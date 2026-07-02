"""Conversion entre tasas de interes (TNA, TEA, TEM).

Las conversiones dependen del anio elegido: ordinario (360 dias) o natural
(365 dias). Con anio ordinario y capitalizacion mensual se obtienen los valores
clasicos (12 capitalizaciones al anio, TEM = (1+TEA)^(1/12) - 1).
"""

from decimal import Decimal

from app.modelos.enumeraciones import Capitalizacion, TipoTasa
from app.utilidades.decimales import DIAS_PERIODO, UNO, a_decimal, potencia

# Duracion en dias de cada periodo de capitalizacion. El numero de
# capitalizaciones al anio sale de dividir los dias del anio entre esto
# (ej.: anio de 360 con capitalizacion mensual -> 360/30 = 12 veces al anio).
DIAS_CAPITALIZACION: dict[Capitalizacion, Decimal] = {
    Capitalizacion.DIARIA: Decimal("1"),
    Capitalizacion.QUINCENAL: Decimal("15"),
    Capitalizacion.MENSUAL: Decimal("30"),
    Capitalizacion.BIMESTRAL: Decimal("60"),
    Capitalizacion.TRIMESTRAL: Decimal("90"),
    Capitalizacion.CUATRIMESTRAL: Decimal("120"),
    Capitalizacion.SEMESTRAL: Decimal("180"),
    Capitalizacion.ANUAL: Decimal("360"),
}


def convertir_tna_a_tea(tna: Decimal, capitalizaciones_por_anio: Decimal) -> Decimal:
    """Pasa una tasa nominal anual a efectiva anual: TEA = (1 + TNA/m)^m - 1."""

    tna = a_decimal(tna)
    m = a_decimal(capitalizaciones_por_anio)
    return potencia(UNO + tna / m, m) - UNO


def convertir_tea_a_tem(tea: Decimal, dias_anio: int = 360) -> Decimal:
    """Pasa una tasa efectiva anual a la tasa del periodo de pago (30 dias)."""

    tea = a_decimal(tea)
    exponente = DIAS_PERIODO / Decimal(dias_anio)
    return potencia(UNO + tea, exponente) - UNO


def calcular_tasas_equivalentes(
    tipo_tasa: TipoTasa,
    valor_tasa: Decimal,
    capitalizacion: Capitalizacion | None = None,
    dias_anio: int = 360,
) -> tuple[Decimal, Decimal]:
    """Devuelve (TEA, TEM) equivalentes a la tasa ingresada.

    Si la tasa es nominal, primero se convierte a efectiva anual usando cuantas
    veces capitaliza en el anio; luego la TEA se lleva a la tasa del periodo de
    pago de 30 dias (TEM). Las tasas van en formato decimal (0.18 = 18%).
    """

    valor_tasa = a_decimal(valor_tasa)
    if valor_tasa < 0:
        raise ValueError("La tasa de interes no puede ser negativa.")

    if tipo_tasa == TipoTasa.EFECTIVA:
        tea = valor_tasa
    elif tipo_tasa == TipoTasa.NOMINAL:
        if capitalizacion is None:
            raise ValueError("La capitalizacion es obligatoria cuando la tasa es nominal.")
        m = Decimal(dias_anio) / DIAS_CAPITALIZACION[capitalizacion]
        tea = convertir_tna_a_tea(valor_tasa, m)
    else:
        raise ValueError("El tipo de tasa indicado no es valido.")

    return tea, convertir_tea_a_tem(tea, dias_anio)


def anual_a_periodica(tasa_anual: Decimal, dias_anio: int = 360) -> Decimal:
    """Pasa una tasa efectiva anual (por ejemplo el COK) a la tasa de 30 dias."""

    tasa_anual = a_decimal(tasa_anual)
    exponente = DIAS_PERIODO / Decimal(dias_anio)
    return potencia(UNO + tasa_anual, exponente) - UNO
