"""Datos semilla para ejecucion local (idempotente)."""

from decimal import Decimal

from sqlalchemy.orm import Session

from app.database import FabricaSesion, crear_tablas
from app.modelos.enumeraciones import Moneda
from app.modelos.usuario import Usuario
from app.modelos.vehiculo import Vehiculo
from app.seguridad.hash import hashear_password


# Catalogo de vehiculos de ejemplo, compartido por todos los usuarios.
_VEHICULOS = [
    {
        "marca": "Toyota", "modelo": "Corolla Cross", "version": "XLI", "anio": 2026,
        "tipo": "SUV", "precio": Decimal("90000.00"), "moneda": Moneda.SOLES,
        "descripcion": "SUV compacto, ideal para la ciudad y el uso diario.",
        "url_imagen": (
            "https://northperurentacar.com.pe/wp-content/uploads/2023/05/"
            "alquiler-de-autos-toyota-corolla-cross-talara-piura-peru.jpg"
        ),
    },
    {
        "marca": "Hyundai", "modelo": "Tucson", "version": "GLS 2.0", "anio": 2025,
        "tipo": "SUV", "precio": Decimal("35000.00"), "moneda": Moneda.DOLARES,
        "descripcion": "SUV familiar con buen equipamiento.",
        "url_imagen": (
            "https://encrypted-tbn0.gstatic.com/images?q=tbn:"
            "ANd9GcSBVablpp4RF9SzGTgASPyBx5tgn7CiAo_58w&s"
        ),
    },
    {
        "marca": "Kia", "modelo": "Rio", "version": "LX", "anio": 2025,
        "tipo": "Sedan", "precio": Decimal("62000.00"), "moneda": Moneda.SOLES,
        "descripcion": "Sedan economico de bajo consumo de combustible.",
        "url_imagen": "https://www.diariomotor.com/imagenes/2020/05/kia-rio-2020-4.jpg?class=M",
    },
    {
        "marca": "Volkswagen", "modelo": "Virtus", "version": "Comfortline", "anio": 2026,
        "tipo": "Sedan", "precio": Decimal("85000.00"), "moneda": Moneda.SOLES,
        "descripcion": "Sedan con tecnologia de seguridad avanzada.",
        "url_imagen": (
            "https://fotos.perfil.com/2018/03/01/trim/1280/720/"
            "5e7d61736d1c41d2c0bb03737267bad2-low.jpg"
        ),
    },
    {
        "marca": "Mazda", "modelo": "CX-5", "version": "Grand Touring", "anio": 2026,
        "tipo": "SUV", "precio": Decimal("42000.00"), "moneda": Moneda.DOLARES,
        "descripcion": "SUV premium con acabados de alta gama.",
        "url_imagen": (
            "https://acnews.blob.core.windows.net/imgnews/medium/"
            "NAZ_de411291377343648e73fbe7dcd94da4.webp"
        ),
    },
]


def _crear_usuarios(sesion: Session) -> None:
    """Crea las cuentas de prueba (se inicia sesion con el correo)."""

    sesion.add_all(
        [
            Usuario(
                nombre="Usuario",
                apellido="Demo",
                correo="demo@gmail.com",
                password_hash=hashear_password("Demo1234"),
                activo=True,
            ),
            Usuario(
                nombre="Maria",
                apellido="Perez",
                correo="maria@gmail.com",
                password_hash=hashear_password("Maria1234"),
                activo=True,
            ),
        ]
    )


def sembrar_datos(sesion: Session) -> bool:
    """Inserta los datos semilla que falten. Devuelve True si inserto algo."""

    creado = False

    if sesion.query(Usuario).first() is None:
        _crear_usuarios(sesion)
        creado = True

    if sesion.query(Vehiculo).first() is None:
        sesion.add_all([Vehiculo(**fila) for fila in _VEHICULOS])
        creado = True

    if creado:
        sesion.commit()
    return creado


def ejecutar_semilla() -> None:
    """Punto de entrada para sembrar datos desde la linea de comandos."""

    crear_tablas()
    sesion = FabricaSesion()
    try:
        if sembrar_datos(sesion):
            print("Datos semilla creados correctamente.")
        else:
            print("La base de datos ya contiene datos; no se realizaron cambios.")
    finally:
        sesion.close()


if __name__ == "__main__":
    ejecutar_semilla()
