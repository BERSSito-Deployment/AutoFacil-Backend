from datetime import date
from pydantic import BaseModel, ConfigDict
from app.modelos.enumeraciones import TipoPeriodo


class CronogramaFilaRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    numero_periodo: int
    fecha_pago: date
    tipo_periodo: TipoPeriodo
    # para cuota final
    saldo_inicial_cuota_final: float
    interes_cuota_final: float
    amortizacion_cuota_final: float
    desgravamen_cuota_final: float
    saldo_final_cuota_final: float
    # el tramo regular
    saldo_inicial: float
    interes: float
    cuota: float
    amortizacion: float
    seguro_desgravamen: float
    seguro_riesgo: float
    gps: float
    portes: float
    gastos_adm: float
    saldo_final: float
    flujo: float