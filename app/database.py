"""Motor, sesion y base declarativa de SQLAlchemy."""

from collections.abc import Generator

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import obtener_configuracion

configuracion = obtener_configuracion()

argumentos_conexion = (
    {"check_same_thread": False}
    if configuracion.url_base_datos.startswith("sqlite")
    else {}
)

motor = create_engine(
    configuracion.url_base_datos,
    connect_args=argumentos_conexion,
    echo=False,
)


# Activa las claves foraneas en SQLite (para el borrado en cascada).
if configuracion.url_base_datos.startswith("sqlite"):

    @event.listens_for(motor, "connect")
    def _activar_foreign_keys(conexion, _registro):  # noqa: ANN001
        cursor = conexion.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


FabricaSesion = sessionmaker(bind=motor, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Clase base declarativa de la que heredan todos los modelos ORM."""


def obtener_sesion() -> Generator[Session, None, None]:
    """Provee una sesion de base de datos y garantiza su cierre posterior."""

    sesion = FabricaSesion()
    try:
        yield sesion
    finally:
        sesion.close()


def _sincronizar_esquema() -> None:
    """Deja la base de datos alineada con los modelos actuales.

    SQLite no altera tablas ya creadas, asi que si el codigo cambio (columnas
    nuevas o quitadas) los INSERT empiezan a fallar. Aqui se compara cada tabla
    con su modelo y, si no coinciden las columnas, la tabla se elimina para que
    `create_all` la vuelva a crear. Las tablas que ya no tienen modelo tambien
    se eliminan. La tabla de usuarios solo se toca si su estructura cambio, de
    modo que las cuentas registradas se conservan entre versiones.
    """

    inspector = inspect(motor)
    tablas_reales = set(inspector.get_table_names())
    tablas_modelo = set(Base.metadata.tables.keys())

    a_eliminar: list[str] = []
    for tabla in tablas_reales - tablas_modelo:
        a_eliminar.append(tabla)
    for tabla in tablas_reales & tablas_modelo:
        columnas_reales = {c["name"] for c in inspector.get_columns(tabla)}
        columnas_modelo = {c.name for c in Base.metadata.tables[tabla].columns}
        if columnas_reales != columnas_modelo:
            a_eliminar.append(tabla)

    if a_eliminar:
        with motor.begin() as conexion:
            conexion.execute(text("PRAGMA foreign_keys=OFF"))
            for tabla in a_eliminar:
                conexion.execute(text(f'DROP TABLE IF EXISTS "{tabla}"'))


def crear_tablas() -> None:
    """Crea las tablas declaradas que aun no existan."""

    from app import modelos  # noqa: F401

    _sincronizar_esquema()
    Base.metadata.create_all(bind=motor)
