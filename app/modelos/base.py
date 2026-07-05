from datetime import datetime, timezone
from sqlalchemy import DateTime, Numeric
from sqlalchemy.orm import Mapped, mapped_column

TipoMonto = Numeric(18, 2)
TipoTasaColumna = Numeric(18, 10)


def _ahora_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class MarcasTiempoMixin:
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime, default=_ahora_utc, nullable=False
    )
    fecha_actualizacion: Mapped[datetime] = mapped_column(
        DateTime, default=_ahora_utc, onupdate=_ahora_utc, nullable=False
    )
