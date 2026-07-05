from datetime import date
from decimal import Decimal
from app.modelos.enumeraciones import TipoPeriodo
from app.servicios.calculadora_financiera import (
    ParametrosCronograma,
    calcular_cuota_francesa,
    generar_cronograma,
)

TOLERANCIA = Decimal("1e-6")


def _parametros(
    meses_gracia_total: int = 0,
    meses_gracia_parcial: int = 0,
    seguro_desgravamen_mensual: Decimal = Decimal("0"),
    cuota_final: Decimal = Decimal("4000"),
) -> ParametrosCronograma:
    return ParametrosCronograma(
        monto_prestamo=Decimal("10000"),
        cuota_final=cuota_final,
        tem=Decimal("0.01"),
        numero_cuotas=12,
        meses_gracia_total=meses_gracia_total,
        meses_gracia_parcial=meses_gracia_parcial,
        seguro_desgravamen_mensual=seguro_desgravamen_mensual,
        seguro_riesgo_periodico=Decimal("0"),
        gps_periodico=Decimal("0"),
        portes_periodico=Decimal("0"),
        gastos_adm_periodico=Decimal("0"),
        fecha_inicio=date(2026, 1, 1),
    )


def test_cuota_francesa_amortiza_hasta_cero():
    saldo_base = Decimal("10000")
    tasa = Decimal("0.01")
    n = 12
    cuota = calcular_cuota_francesa(saldo_base, tasa, n)

    saldo = saldo_base
    for _ in range(n):
        interes = saldo * tasa
        amortizacion = cuota - interes
        saldo -= amortizacion
    assert abs(saldo) < TOLERANCIA


def test_cuota_francesa_tasa_cero():
    cuota = calcular_cuota_francesa(Decimal("12000"), Decimal("0"), 12)
    assert cuota == Decimal("1000")


def test_cronograma_tiene_un_periodo_extra_para_la_cuota_final():
    resultado = generar_cronograma(_parametros())
    assert len(resultado.filas) == 13  
    assert resultado.filas[-1].numero_periodo == 13
    assert resultado.filas[-1].tipo_periodo == TipoPeriodo.CUOTA_FINAL
    assert abs(resultado.filas[11].saldo_final) < TOLERANCIA
    assert abs(resultado.filas[-1].saldo_final_cuota_final) < TOLERANCIA


def test_cuota_final_se_paga_integro_en_el_periodo_final():
    resultado = generar_cronograma(_parametros(cuota_final=Decimal("4000")))
    ultima = resultado.filas[-1]
    assert abs(ultima.amortizacion_cuota_final - Decimal("4000")) < TOLERANCIA
    assert all(f.amortizacion_cuota_final == Decimal("0") for f in resultado.filas[:-1])


def test_saldo_financiado_excluye_el_valor_presente_de_la_cuota_final():
    resultado = generar_cronograma(_parametros(cuota_final=Decimal("4000")))
    vp = Decimal("4000") / (Decimal("1.01") ** 13)
    assert abs(resultado.saldo_financiado - (Decimal("10000") - vp)) < TOLERANCIA
    assert abs(resultado.filas[0].saldo_inicial - resultado.saldo_financiado) < TOLERANCIA


def test_cronograma_gracia_total_capitaliza_intereses():
    resultado = generar_cronograma(_parametros(meses_gracia_total=3))
    for fila in resultado.filas[:3]:
        assert fila.tipo_periodo == TipoPeriodo.GRACIA_TOTAL
        assert fila.cuota == Decimal("0")
        assert fila.amortizacion == Decimal("0")
        assert fila.saldo_final > fila.saldo_inicial
    assert abs(resultado.filas[11].saldo_final) < TOLERANCIA


def test_cronograma_gracia_parcial_paga_solo_interes():
    resultado = generar_cronograma(_parametros(meses_gracia_parcial=2))
    for fila in resultado.filas[:2]:
        assert fila.tipo_periodo == TipoPeriodo.GRACIA_PARCIAL
        assert fila.amortizacion == Decimal("0")
        assert fila.saldo_final == fila.saldo_inicial
        assert abs(fila.cuota - fila.interes) < TOLERANCIA
    assert abs(resultado.filas[11].saldo_final) < TOLERANCIA
