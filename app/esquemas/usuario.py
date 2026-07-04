"""Esquemas Pydantic para la entidad Usuario."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.esquemas.comunes import validar_correo, validar_password_bcrypt


class UsuarioRespuesta(BaseModel):
    """Representacion publica de un usuario, sin la contrasena."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    apellido: str
    correo: str
    activo: bool
    fecha_creacion: datetime
    fecha_actualizacion: datetime


class PerfilActualizar(BaseModel):
    """Datos para que el usuario actualice su propio perfil."""

    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    apellido: str | None = Field(default=None, min_length=1, max_length=120)
    correo: str | None = Field(default=None, max_length=180)
    password_actual: str | None = Field(default=None, max_length=128)
    password_nueva: str | None = Field(default=None, min_length=6, max_length=128)

    @field_validator("correo")
    @classmethod
    def _validar_correo(cls, valor: str | None) -> str | None:
        return validar_correo(valor)

    @field_validator("password_nueva")
    @classmethod
    def _validar_password(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        return validar_password_bcrypt(valor)

    @field_validator("nombre", "apellido")
    @classmethod
    def _validar_texto(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        if valor.strip() == "":
            raise ValueError("El campo no puede estar vacio.")
        return valor.strip()
