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


if configuracion.url_base_datos.startswith("sqlite"):

    @event.listens_for(motor, "connect")
    def _activar_foreign_keys(conexion, _registro):  
        cursor = conexion.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


FabricaSesion = sessionmaker(bind=motor, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Clase base"""


def obtener_sesion() -> Generator[Session, None, None]:
    sesion = FabricaSesion()
    try:
        yield sesion
    finally:
        sesion.close()


def _sincronizar_esquema() -> None:

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
    from app import modelos  

    _sincronizar_esquema()
    Base.metadata.create_all(bind=motor)
