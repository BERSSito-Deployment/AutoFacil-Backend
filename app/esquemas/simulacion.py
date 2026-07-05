from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.esquemas.cronograma import CronogramaFilaRespuesta
from app.modelos.enumeraciones import (
    Capitalizacion,
    Moneda,
    Plan,
    TipoTasa,
)


class ParametrosFinancieros(BaseModel):

    moneda: Moneda = Moneda.SOLES
    tipo_cambio_referencial: Decimal | None = Field(default=None, ge=0)
    # el plan 24 y 36 sirven como un ajuste predeterminado, personalizado las agarra de numero_cuotas
    plan: Plan = Plan.PLAN_36
    # si se elige personalizado se saca de aquí:
    numero_cuotas: int | None = Field(default=None, ge=1, le=120)
    # año para las conversiones de tasas: 360 dias (ordinario) o 365 (natural)
    dias_anio: int = 360
    porcentaje_cuota_inicial: Decimal = Field(default=Decimal("0.20"), ge=0, le=1)
    # cuota final, si el usuario no pone una personalizada se usa la predeterminada por el plan (40% en Plan 36, 50% en Plan 24)
    porcentaje_cuota_final: Decimal | None = Field(default=None, ge=0, lt=1)
    tipo_tasa: TipoTasa = TipoTasa.NOMINAL
    valor_tasa: Decimal = Field(..., ge=0, description="Tasa en formato decimal (0.15 = 15%)")
    # solo si la tasa es nominal
    capitalizacion: Capitalizacion | None = None
    # periodos de gracia, primero va la gracia total y luego la parcial, en la q solo se paga intereses y seguros
    meses_gracia_total: int = Field(default=0, ge=0)
    meses_gracia_parcial: int = Field(default=0, ge=0)
    # costos y gastos iniciales, se elige si entra al prestamo o si el usuario lo pagará al contado
    costo_notarial: Decimal = Field(default=Decimal("0"), ge=0)
    costo_notarial_financiado: bool = True
    costo_registral: Decimal = Field(default=Decimal("0"), ge=0)
    costo_registral_financiado: bool = True
    costo_tasacion: Decimal = Field(default=Decimal("0"), ge=0)
    costo_tasacion_financiado: bool = True
    comision_estudio: Decimal = Field(default=Decimal("0"), ge=0)
    comision_estudio_financiado: bool = True
    comision_activacion: Decimal = Field(default=Decimal("0"), ge=0)
    comision_activacion_financiado: bool = True
    # costos periodicos por cuota
    gps_periodico: Decimal = Field(default=Decimal("0"), ge=0)
    portes_periodico: Decimal = Field(default=Decimal("0"), ge=0)
    gastos_adm_periodico: Decimal = Field(default=Decimal("0"), ge=0)
    # seguros
    seguro_desgravamen_mensual: Decimal = Field(default=Decimal("0"), ge=0)
    seguro_riesgo_anual: Decimal = Field(default=Decimal("0"), ge=0)
    # coki
    cok_anual: Decimal = Field(default=Decimal("0"), ge=0)
    fecha_inicio: date | None = None

    @model_validator(mode="after")
    def validar_reglas(self) -> "ParametrosFinancieros":

        if self.tipo_tasa == TipoTasa.NOMINAL and self.capitalizacion is None:
            raise ValueError("La capitalizacion es obligatoria cuando la tasa es nominal.")
        if self.dias_anio not in (360, 365):
            raise ValueError("Los dias por anio deben ser 360 (ordinario) o 365 (natural).")
        if self.plan == Plan.PERSONALIZADO and self.numero_cuotas is None:
            raise ValueError("Indique el numero de meses del plan personalizado.")
        cuotas = self.plan.cuotas(self.numero_cuotas)
        if self.meses_gracia_total + self.meses_gracia_parcial >= cuotas:
            raise ValueError("Los meses de gracia deben ser menores que el numero de cuotas.")
        return self


class SimulacionCalcularRequest(ParametrosFinancieros):
    vehiculo_id: int
    nombre: str | None = Field(default=None, max_length=150)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "vehiculo_id": 1,
                    "nombre": "Compra Inteligente - Plan 36",
                    "moneda": "PEN",
                    "plan": "PLAN_36",
                    "porcentaje_cuota_inicial": 0.20,
                    "tipo_tasa": "NOMINAL",
                    "valor_tasa": 0.15,
                    "capitalizacion": "DIARIA",
                    "meses_gracia_total": 3,
                    "meses_gracia_parcial": 3,
                    "costo_notarial": 100,
                    "costo_notarial_financiado": True,
                    "costo_registral": 75,
                    "costo_registral_financiado": True,
                    "gps_periodico": 20,
                    "portes_periodico": 3.5,
                    "gastos_adm_periodico": 3.5,
                    "seguro_desgravamen_mensual": 0.00049,
                    "seguro_riesgo_anual": 0.003,
                    "cok_anual": 0.50,
                    "fecha_inicio": "2026-01-01",
                }
            ]
        }
    }


class SimulacionGuardarRequest(SimulacionCalcularRequest):
    # se puede actualizar el precio del vehiculo al momento de editar, claro si es que este cambió en primer lugar
    actualizar_precio: bool = False


class IndicadoresSimulacion(BaseModel):
    moneda: Moneda
    precio_vehiculo: float
    plan: Plan
    numero_cuotas: int
    dias_anio: int
    porcentaje_cuota_inicial: float
    cuota_inicial: float
    porcentaje_cuota_final: float
    cuota_final: float
    monto_prestamo: float
    saldo_financiado: float
    tipo_tasa: TipoTasa
    tasa_ingresada: float
    capitalizacion: Capitalizacion | None
    tea_equivalente: float
    tem: float
    meses_gracia_total: int
    meses_gracia_parcial: int
    seguro_desgravamen_mensual: float
    seguro_riesgo_anual: float
    seguro_riesgo_periodico: float
    gps_periodico: float
    portes_periodico: float
    gastos_adm_periodico: float
    total_costos_financiados: float
    total_costos_efectivo: float
    cuota_mensual: float
    cok_anual: float
    cok_mensual: float
    van: float
    tir_mensual: float | None
    tcea: float | None
    total_intereses: float
    total_amortizado: float
    total_seguro_desgravamen: float
    total_seguro_riesgo: float
    total_gps: float
    total_portes: float
    total_gastos_adm: float
    monto_total_pagado: float


class ResultadoCalculo(IndicadoresSimulacion):
    cronograma: list[CronogramaFilaRespuesta]


class SimulacionRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    nombre: str | None
    vehiculo_id: int
    usuario_id: int
    moneda: Moneda
    tipo_cambio_referencial: float | None
    fecha_inicio: date
    # Parametros de entrada.
    precio_vehiculo: float
    plan: Plan
    porcentaje_cuota_inicial: float
    tipo_tasa: TipoTasa
    tasa_ingresada: float
    capitalizacion: Capitalizacion | None
    meses_gracia_total: int
    meses_gracia_parcial: int
    costo_notarial: float
    costo_notarial_financiado: bool
    costo_registral: float
    costo_registral_financiado: bool
    costo_tasacion: float
    costo_tasacion_financiado: bool
    comision_estudio: float
    comision_estudio_financiado: bool
    comision_activacion: float
    comision_activacion_financiado: bool
    gps_periodico: float
    portes_periodico: float
    gastos_adm_periodico: float
    seguro_desgravamen_mensual: float
    seguro_riesgo_anual: float
    cok_anual: float
    # resultados
    numero_cuotas: int
    dias_anio: int
    porcentaje_cuota_final: float
    cuota_inicial: float
    cuota_final: float
    monto_prestamo: float
    saldo_financiado: float
    tea_equivalente: float
    tem: float
    seguro_riesgo_periodico: float
    total_costos_financiados: float
    total_costos_efectivo: float
    cuota_mensual: float
    cok_mensual: float
    van: float
    tir_mensual: float | None
    tcea: float | None
    total_intereses: float
    total_amortizado: float
    total_seguro_desgravamen: float
    total_seguro_riesgo: float
    total_gps: float
    total_portes: float
    total_gastos_adm: float
    monto_total_pagado: float
    fecha_creacion: datetime
    fecha_actualizacion: datetime


class SimulacionDetalle(SimulacionRespuesta):
    vehiculo_descripcion: str | None = None
    usuario_nombre: str | None = None
    cronograma: list[CronogramaFilaRespuesta] = []


class SimulacionListado(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    nombre: str | None = None
    moneda: Moneda
    plan: Plan
    vehiculo_id: int
    vehiculo_descripcion: str | None = None
    monto_prestamo: float
    numero_cuotas: int
    cuota_mensual: float
    pago_mensual: float # pago total, cuota del propio auto + costos adicionales
    tcea: float | None
    fecha_creacion: datetime
