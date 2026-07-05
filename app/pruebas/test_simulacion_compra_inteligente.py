from datetime import date
from decimal import Decimal
from app.modelos.enumeraciones import Capitalizacion, Moneda, Plan, TipoPeriodo, TipoTasa
from app.servicios import servicio_van_tir
from app.servicios.servicio_simulacion import (
    CostoInicial,
    EntradaSimulacion,
    calcular_simulacion,
    redondear_resultado,
)
from app.servicios.servicio_tcea import calcular_tcea


def _entrada_base(**cambios) -> EntradaSimulacion:
    parametros = dict(
        moneda=Moneda.SOLES,
        precio_vehiculo=Decimal("80000"),
        plan=Plan.PLAN_36,
        porcentaje_cuota_inicial=Decimal("0.20"),
        tipo_tasa=TipoTasa.EFECTIVA,
        valor_tasa=Decimal("0.145"),
        capitalizacion=None,
        meses_gracia_total=0,
        meses_gracia_parcial=0,
        gps_periodico=Decimal("20"),
        portes_periodico=Decimal("5"),
        gastos_adm_periodico=Decimal("5"),
        seguro_desgravamen_mensual=Decimal("0.0005"),
        seguro_riesgo_anual=Decimal("0.003"),
        cok_anual=Decimal("0.12"),
        fecha_inicio=date(2026, 1, 1),
    )
    parametros.update(cambios)
    return EntradaSimulacion(**parametros)


def test_van_flujos_conocidos():
    flujos = [Decimal("-1000"), Decimal("600"), Decimal("600")]
    van = servicio_van_tir.calcular_van(flujos, Decimal("0.10"))
    assert abs(van - Decimal("41.32231405")) < Decimal("1e-6")


def test_tir_flujos_conocidos():
    flujos = [Decimal("-1000"), Decimal("600"), Decimal("600")]
    tir = servicio_van_tir.calcular_tir(flujos)
    assert tir is not None
    assert abs(tir - Decimal("0.130662386")) < Decimal("1e-6")
    assert abs(servicio_van_tir.calcular_van(flujos, tir)) < Decimal("1e-6")


def test_tcea_anualiza_la_tasa_mensual():
    flujos = [Decimal("2647.13")] + [Decimal("-900")] * 3
    tasa_mensual, tcea = calcular_tcea(flujos, Decimal("12"))
    assert tasa_mensual is not None and tcea is not None
    esperado = (Decimal("1") + tasa_mensual) ** 12 - Decimal("1")
    assert abs(tcea - esperado) < Decimal("1e-9")


def test_simulacion_completa_cierra_en_cero():
    resultado = calcular_simulacion(_entrada_base())
    assert len(resultado.filas) == 37  
    assert resultado.cuota_final == Decimal("80000") * Decimal("0.40")
    assert resultado.monto_prestamo == Decimal("64000")  # 80000 - 20%
    assert abs(resultado.filas[35].saldo_final) < Decimal("1e-6")
    assert abs(resultado.filas[-1].saldo_final_cuota_final) < Decimal("1e-6")
    ordinarias = {
        round(float(f.cuota), 2)
        for f in resultado.filas
        if f.tipo_periodo == TipoPeriodo.CUOTA_ORDINARIA
    }
    assert len(ordinarias) == 1


def test_simulacion_indicadores_presentes():
    resultado = calcular_simulacion(_entrada_base())
    assert resultado.van is not None
    assert resultado.tir_mensual is not None
    assert resultado.tcea is not None
    esperado = (Decimal("1") + resultado.tir_mensual) ** 12 - Decimal("1")
    assert abs(resultado.tcea - esperado) < Decimal("1e-9")
    assert resultado.tcea > resultado.tea_equivalente


def test_simulacion_gracia_total_cierra_en_cero():
    resultado = calcular_simulacion(_entrada_base(meses_gracia_total=3))
    assert resultado.meses_gracia_total == 3
    assert [f.tipo_periodo for f in resultado.filas[:3]] == [TipoPeriodo.GRACIA_TOTAL] * 3
    assert abs(resultado.filas[35].saldo_final) < Decimal("1e-6")
    assert abs(resultado.filas[-1].saldo_final_cuota_final) < Decimal("1e-6")


def test_simulacion_tasa_nominal():
    resultado = calcular_simulacion(
        _entrada_base(
            tipo_tasa=TipoTasa.NOMINAL,
            valor_tasa=Decimal("0.12"),
            capitalizacion=Capitalizacion.MENSUAL,
        )
    )
    assert abs(resultado.tem - Decimal("0.01")) < Decimal("1e-10")


def test_plan_24_usa_cuota_final_del_50_por_ciento():
    resultado = calcular_simulacion(_entrada_base(plan=Plan.PLAN_24))
    assert resultado.numero_cuotas == 24
    assert resultado.cuota_final == Decimal("80000") * Decimal("0.50")
    assert len(resultado.filas) == 25


def test_plan_personalizado_usa_los_meses_indicados():
    resultado = calcular_simulacion(
        _entrada_base(
            plan=Plan.PERSONALIZADO,
            numero_cuotas=18,
            porcentaje_cuota_final=Decimal("0.30"),
        )
    )
    assert resultado.numero_cuotas == 18
    assert len(resultado.filas) == 19  # 18 cuotas + la cuota final
    assert resultado.cuota_final == Decimal("80000") * Decimal("0.30")
    assert abs(resultado.filas[17].saldo_final) < Decimal("1e-6")
    assert abs(resultado.filas[-1].saldo_final_cuota_final) < Decimal("1e-6")


def test_anio_natural_cambia_las_conversiones():
    ordinario = calcular_simulacion(_entrada_base(dias_anio=360))
    natural = calcular_simulacion(_entrada_base(dias_anio=365))
    assert natural.tem < ordinario.tem
    assert natural.tcea != ordinario.tcea
    assert abs(natural.filas[35].saldo_final) < Decimal("1e-6")


def test_capitalizacion_trimestral():
    resultado = calcular_simulacion(
        _entrada_base(
            tipo_tasa=TipoTasa.NOMINAL,
            valor_tasa=Decimal("0.12"),
            capitalizacion=Capitalizacion.TRIMESTRAL,
        )
    )
    esperado = (Decimal("1.03") ** 4) - Decimal("1")
    assert abs(resultado.tea_equivalente - esperado) < Decimal("1e-12")


def test_costos_financiados_elevan_el_prestamo_y_la_cuota():
    base = calcular_simulacion(_entrada_base())
    con_costos = calcular_simulacion(
        _entrada_base(costo_notarial=CostoInicial(Decimal("1000"), True))
    )
    assert con_costos.total_costos_financiados == Decimal("1000")
    assert con_costos.monto_prestamo == base.monto_prestamo + Decimal("1000")
    assert con_costos.cuota_mensual > base.cuota_mensual


def test_costo_efectivo_no_eleva_el_prestamo():
    base = calcular_simulacion(_entrada_base())
    con_efectivo = calcular_simulacion(
        _entrada_base(costo_notarial=CostoInicial(Decimal("1000"), False))
    )
    assert con_efectivo.total_costos_efectivo == Decimal("1000")
    assert con_efectivo.monto_prestamo == base.monto_prestamo


def test_redondeo_cronograma_devuelve_todas_las_filas():
    crono = redondear_resultado(calcular_simulacion(_entrada_base()))["cronograma"]
    assert len(crono) == 37
    assert crono[-1]["saldo_final_cuota_final"] == Decimal("0.00")
    assert crono[-1]["amortizacion_cuota_final"] > Decimal("0")
