"""Pruebas de configuracion de entorno."""

from app.config import Configuracion, normalizar_url_base_datos


def test_normaliza_urls_postgresql_para_psycopg():
    assert (
        normalizar_url_base_datos("postgres://u:p@host:5432/db")
        == "postgresql+psycopg://u:p@host:5432/db"
    )
    assert (
        normalizar_url_base_datos("postgresql://u:p@host:5432/db")
        == "postgresql+psycopg://u:p@host:5432/db"
    )
    assert (
        normalizar_url_base_datos("postgresql+psycopg://u:p@host:5432/db")
        == "postgresql+psycopg://u:p@host:5432/db"
    )


def test_usa_database_url_si_no_hay_variable_prefijada(monkeypatch):
    monkeypatch.delenv("AUTOFACIL_URL_BASE_DATOS", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgres://u:p@host:5432/db")

    configuracion = Configuracion(_env_file=None)

    assert configuracion.url_base_datos == "postgresql+psycopg://u:p@host:5432/db"
