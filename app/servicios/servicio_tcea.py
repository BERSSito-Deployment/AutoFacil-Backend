"""Calculo de la TCEA a partir del flujo de pagos del usuario.

La TCEA es la tasa que resume cuanto cuesta el credito al anio contando todo lo
que se paga: intereses, seguros y cargos. Se obtiene buscando la tasa mensual
que iguala lo recibido con lo pagado (la TIR) y llevandola a un anio.
"""

from decimal import Decimal

from app.servicios.servicio_van_tir import calcular_tir
from app.utilidades.decimales import UNO, potencia


def calcular_tcea(
    flujos_costo_deudor: list[Decimal], periodos_por_anio: Decimal
) -> tuple[Decimal | None, Decimal | None]:
    """Devuelve (tasa mensual de costo, TCEA anual) o (None, None).

    `periodos_por_anio` son las cuotas que entran en un anio: 12 con anio
    ordinario de 360 dias, 365/30 con anio natural.
    """

    tasa_mensual = calcular_tir(flujos_costo_deudor)
    if tasa_mensual is None:
        return None, None

    return tasa_mensual, potencia(UNO + tasa_mensual, periodos_por_anio) - UNO
