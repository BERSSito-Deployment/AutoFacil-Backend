from decimal import Decimal
from app.utilidades.decimales import UNO, a_decimal, potencia

_TOLERANCIA = Decimal("1e-12")
_MAX_ITERACIONES = 200
_TASA_MINIMA = Decimal("-0.999999")
_TASA_MAXIMA = Decimal("10")
_PASO_BUSQUEDA = Decimal("0.005")


def calcular_van(flujos: list[Decimal], tasa_periodica: Decimal) -> Decimal:
    tasa_periodica = a_decimal(tasa_periodica)
    base = UNO + tasa_periodica
    if base <= 0:
        raise ValueError("La tasa de descuento produce un factor no positivo.")

    acumulado = Decimal("0")
    for k, flujo in enumerate(flujos):
        acumulado += a_decimal(flujo) / potencia(base, Decimal(k))
    return acumulado


def _derivada_van(flujos: list[Decimal], tasa_periodica: Decimal) -> Decimal:
    base = UNO + tasa_periodica
    acumulado = Decimal("0")
    for k, flujo in enumerate(flujos):
        if k == 0:
            continue
        acumulado += -a_decimal(flujo) * Decimal(k) / potencia(base, Decimal(k + 1))
    return acumulado


def _acotar_cambio_signo(
    flujos: list[Decimal],
) -> tuple[Decimal, Decimal] | None:
    # busca donde la van cambia de signo

    tasa_anterior = _TASA_MINIMA
    van_anterior = calcular_van(flujos, tasa_anterior)
    if van_anterior == 0:
        return tasa_anterior, tasa_anterior

    tasa_actual = tasa_anterior + _PASO_BUSQUEDA
    while tasa_actual <= _TASA_MAXIMA:
        van_actual = calcular_van(flujos, tasa_actual)
        if van_actual == 0:
            return tasa_actual, tasa_actual
        if (van_anterior > 0) != (van_actual > 0):
            return tasa_anterior, tasa_actual
        tasa_anterior = tasa_actual
        van_anterior = van_actual
        tasa_actual += _PASO_BUSQUEDA

    return None


def _biseccion(flujos: list[Decimal], izquierda: Decimal, derecha: Decimal) -> Decimal:

    van_izquierda = calcular_van(flujos, izquierda)
    for _ in range(_MAX_ITERACIONES):
        medio = (izquierda + derecha) / 2
        van_medio = calcular_van(flujos, medio)
        if abs(van_medio) < _TOLERANCIA or (derecha - izquierda) < _TOLERANCIA:
            return medio
        if (van_izquierda > 0) != (van_medio > 0):
            derecha = medio
        else:
            izquierda = medio
            van_izquierda = van_medio
    return (izquierda + derecha) / 2


def calcular_tir(flujos: list[Decimal]) -> Decimal | None:

    if not flujos or all(a_decimal(flujo) == 0 for flujo in flujos):
        return None

    intervalo = _acotar_cambio_signo(flujos)
    if intervalo is None:
        return None

    izquierda, derecha = intervalo
    if izquierda == derecha:
        return izquierda

    aproximacion = _biseccion(flujos, izquierda, derecha)

    tasa = aproximacion
    for _ in range(_MAX_ITERACIONES):
        valor = calcular_van(flujos, tasa)
        if abs(valor) < _TOLERANCIA:
            return tasa
        derivada = _derivada_van(flujos, tasa)
        if derivada == 0:
            break
        siguiente = tasa - valor / derivada
        if siguiente <= _TASA_MINIMA or siguiente >= _TASA_MAXIMA:
            break
        if abs(siguiente - tasa) < _TOLERANCIA:
            return siguiente
        tasa = siguiente

    return aproximacion
