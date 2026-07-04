"""Esquemas Pydantic para autenticacion y registro de usuarios."""

from pydantic import BaseModel, Field, field_validator

from app.esquemas.comunes import validar_correo_obligatorio, validar_password_bcrypt


class TokenRespuesta(BaseModel):
    """Respuesta entregada tras un inicio de sesion exitoso."""

    access_token: str
    token_type: str = "bearer"


class CredencialesLogin(BaseModel):
    """Credenciales del inicio de sesion: correo y contrasena."""

    correo: str = Field(..., max_length=180)
    password: str

    model_config = {
        "json_schema_extra": {
            "examples": [{"correo": "demo@gmail.com", "password": "Demo1234"}]
        }
    }


class RegistroRequest(BaseModel):
    """Datos para el registro publico de un nuevo usuario."""

    nombre: str = Field(..., min_length=1, max_length=120)
    apellido: str = Field(..., min_length=1, max_length=120)
    correo: str = Field(..., max_length=180)
    password: str = Field(..., min_length=6, max_length=128)

    @field_validator("correo")
    @classmethod
    def _validar_correo(cls, valor: str) -> str:
        return validar_correo_obligatorio(valor)

    @field_validator("password")
    @classmethod
    def _validar_password(cls, valor: str) -> str:
        return validar_password_bcrypt(valor)

    @field_validator("nombre", "apellido")
    @classmethod
    def _validar_texto(cls, valor: str) -> str:
        if valor.strip() == "":
            raise ValueError("El campo no puede estar vacio.")
        return valor.strip()

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "nombre": "Lucia",
                    "apellido": "Garcia",
                    "correo": "lucia.garcia@gmail.com",
                    "password": "Clave123",
                }
            ]
        }
    }
