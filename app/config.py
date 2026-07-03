"""Configuracion de la aplicacion leida del entorno."""

from functools import lru_cache
from os import getenv
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Ruta absoluta de la base SQLite (anclada al directorio del backend).
DIRECTORIO_BACKEND = Path(__file__).resolve().parent.parent
RUTA_BASE_DATOS = (DIRECTORIO_BACKEND / "autofacil.db").as_posix()


def _url_base_datos_predeterminada() -> str:
    """Usa DATABASE_URL si existe; si no, conserva SQLite local."""

    return getenv("DATABASE_URL", f"sqlite:///{RUTA_BASE_DATOS}")


def normalizar_url_base_datos(url: str) -> str:
    """Adapta URLs PostgreSQL comunes al driver psycopg instalado."""

    url_limpia = url.strip()
    if url_limpia.startswith("postgres://"):
        return f"postgresql+psycopg://{url_limpia.removeprefix('postgres://')}"
    if url_limpia.startswith("postgresql://"):
        return f"postgresql+psycopg://{url_limpia.removeprefix('postgresql://')}"
    return url_limpia


class Configuracion(BaseSettings):
    """Parametros de configuracion."""

    nombre_aplicacion: str = "AutoFacil"
    descripcion_aplicacion: str = (
        "Sistema de simulacion y gestion de credito vehicular para una entidad "
        "financiera en Peru."
    )
    version_aplicacion: str = "1.0.0"

    url_base_datos: str = Field(default_factory=_url_base_datos_predeterminada)

    # En produccion definir AUTOFACIL_CLAVE_SECRETA en el entorno.
    clave_secreta: str = "autofacil-clave-secreta-solo-desarrollo-local-cambiar"
    algoritmo_jwt: str = "HS256"
    minutos_expiracion_token: int = 60 * 8

    origenes_cors: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

    precision_decimal: int = 50
    sembrar_datos_inicio: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_prefix="AUTOFACIL_")

    @field_validator("url_base_datos")
    @classmethod
    def _validar_url_base_datos(cls, url: str) -> str:
        return normalizar_url_base_datos(url)


@lru_cache
def obtener_configuracion() -> Configuracion:
    """Devuelve una instancia unica y cacheada de la configuracion."""

    return Configuracion()
