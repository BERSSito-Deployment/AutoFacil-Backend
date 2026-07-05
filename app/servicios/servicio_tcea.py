from decimal import Decimal
from app.servicios.servicio_van_tir import calcular_tir
from app.utilidades.decimales import UNO, potencia

# la tcea es la tasa que dice cuanto cuesta el credito al año contando todo lo que se paga, se usa la tasa mensual que iguala la tir y llevandola a un año

def calcular_tcea(
    flujos_costo_deudor: list[Decimal], periodos_por_anio: Decimal
) -> tuple[Decimal | None, Decimal | None]:

    tasa_mensual = calcular_tir(flujos_costo_deudor)
    if tasa_mensual is None:
        return None, None

    return tasa_mensual, potencia(UNO + tasa_mensual, periodos_por_anio) - UNO
