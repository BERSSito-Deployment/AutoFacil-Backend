"""Enumeraciones de dominio."""

from enum import Enum


class Moneda(str, Enum):
    """Monedas admitidas para precios y simulaciones."""

    SOLES = "PEN"
    DOLARES = "USD"


class TipoTasa(str, Enum):
    """Tipo de tasa de interes ingresada (TNA = nominal, TEA = efectiva)."""

    NOMINAL = "NOMINAL"
    EFECTIVA = "EFECTIVA"


class Capitalizacion(str, Enum):
    """Frecuencias con las que capitaliza una tasa nominal (TNA)."""

    DIARIA = "DIARIA"
    QUINCENAL = "QUINCENAL"
    MENSUAL = "MENSUAL"
    BIMESTRAL = "BIMESTRAL"
    TRIMESTRAL = "TRIMESTRAL"
    CUATRIMESTRAL = "CUATRIMESTRAL"
    SEMESTRAL = "SEMESTRAL"
    ANUAL = "ANUAL"


class Plan(str, Enum):
    """Plan de pagos del credito.

    Los planes 24 y 36 son los del producto Compra Inteligente (con su numero
    de cuotas y cuota final sugerida). El plan personalizado deja elegir los
    meses a mano.
    """

    PLAN_24 = "PLAN_24"
    PLAN_36 = "PLAN_36"
    PERSONALIZADO = "PERSONALIZADO"

    def cuotas(self, numero_cuotas_manual: int | None = None) -> int:
        """Numero de cuotas del plan; el personalizado usa el valor manual."""

        if self is Plan.PLAN_24:
            return 24
        if self is Plan.PLAN_36:
            return 36
        if numero_cuotas_manual is None or numero_cuotas_manual <= 0:
            raise ValueError("Indique el numero de meses del plan personalizado.")
        return numero_cuotas_manual

    @property
    def cuota_final_sugerida(self) -> str:
        """Porcentaje de cuota final por defecto (decimal, como texto)."""

        if self is Plan.PLAN_24:
            return "0.50"
        return "0.40"


class TipoPeriodo(str, Enum):
    """Clasificacion de cada fila del cronograma de pagos."""

    GRACIA_TOTAL = "GRACIA_TOTAL"
    GRACIA_PARCIAL = "GRACIA_PARCIAL"
    CUOTA_ORDINARIA = "CUOTA_ORDINARIA"
    CUOTA_FINAL = "CUOTA_FINAL"


class EstadoSimulacion(str, Enum):
    """Estado de una simulacion: vigente (CALCULADA) o archivada (ARCHIVADA)."""

    CALCULADA = "CALCULADA"
    ARCHIVADA = "ARCHIVADA"
