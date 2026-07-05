from pydantic import BaseModel
from app.esquemas.comunes import DecimalNumero


class TipoCambioRespuesta(BaseModel):
    base: str
    destino: str
    tasa: DecimalNumero
    fuente: str
    en_linea: bool
