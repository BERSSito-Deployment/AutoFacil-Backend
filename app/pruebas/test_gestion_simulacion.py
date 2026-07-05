from decimal import Decimal
from app.esquemas.simulacion import SimulacionCalcularRequest
from app.modelos.enumeraciones import Moneda
from app.modelos.vehiculo import Vehiculo
from app.servicios.servicio_gestion_simulacion import construir_entrada, convertir_precio


def _solicitud() -> SimulacionCalcularRequest:
    return SimulacionCalcularRequest(
        vehiculo_id=1,
        moneda="PEN",
        plan="PLAN_36",
        tipo_tasa="EFECTIVA",
        valor_tasa=Decimal("0.15"),
        porcentaje_cuota_inicial=Decimal("0.20"),
    )


def test_entrada_usa_precio_actual_del_vehiculo():
    vehiculo = Vehiculo(
        marca="Toyota", modelo="Yaris", anio=2026, precio=Decimal("95000"), moneda=Moneda.SOLES
    )
    entrada = construir_entrada(_solicitud(), vehiculo)
    assert Decimal(entrada.precio_vehiculo) == Decimal("95000")


def test_entrada_conserva_precio_operacion_en_recalculo():
    vehiculo = Vehiculo(
        marca="Toyota", modelo="Yaris", anio=2026, precio=Decimal("95000"), moneda=Moneda.SOLES
    )
    entrada = construir_entrada(
        _solicitud(), vehiculo, precio_operacion=Decimal("90000")
    )
    assert Decimal(entrada.precio_vehiculo) == Decimal("90000")


def test_convertir_precio_entre_monedas():
    assert convertir_precio(Decimal("100"), Moneda.SOLES, Moneda.SOLES, None) == Decimal("100")
    assert convertir_precio(
        Decimal("3750"), Moneda.SOLES, Moneda.DOLARES, Decimal("3.75")
    ) == Decimal("1000")
    assert convertir_precio(
        Decimal("1000"), Moneda.DOLARES, Moneda.SOLES, Decimal("3.75")
    ) == Decimal("3750")


def test_simular_mismo_vehiculo_en_otra_moneda():
    vehiculo = Vehiculo(
        marca="Toyota", modelo="Yaris", anio=2026, precio=Decimal("75000"), moneda=Moneda.SOLES
    )
    solicitud = SimulacionCalcularRequest(
        vehiculo_id=1,
        moneda="USD",
        tipo_cambio_referencial=Decimal("3.75"),
        plan="PLAN_36",
        tipo_tasa="EFECTIVA",
        valor_tasa=Decimal("0.12"),
        porcentaje_cuota_inicial=Decimal("0.20"),
    )
    entrada = construir_entrada(solicitud, vehiculo)
    assert entrada.moneda == Moneda.DOLARES
    assert Decimal(entrada.precio_vehiculo) == Decimal("20000")  
