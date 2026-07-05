import re
from decimal import Decimal
from typing import Annotated
from pydantic import PlainSerializer

DecimalNumero = Annotated[
    Decimal,
    PlainSerializer(
        lambda valor: float(valor) if valor is not None else None,
        return_type=float,
        when_used="json",
    ),
]

_PATRON_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validar_correo(valor: str | None) -> str | None:

    if valor is None:
        return None
    valor = valor.strip().lower()
    if valor == "":
        return None
    if not _PATRON_CORREO.match(valor):
        raise ValueError("El correo electronico no tiene un formato valido.")
    return valor


def validar_correo_obligatorio(valor: str | None) -> str:

    if valor is None or valor.strip() == "":
        raise ValueError("El correo electronico es obligatorio.")
    valor = valor.strip().lower()
    if not _PATRON_CORREO.match(valor):
        raise ValueError("El correo electronico no tiene un formato valido.")
    return valor


def validar_password_bcrypt(valor: str) -> str:

    if valor is None or valor == "":
        raise ValueError("La contraseña es obligatoria.")
    if len(valor.encode("utf-8")) > 72:
        raise ValueError(
            "La contraseña es demasiado larga."
        )
    return valor


def texto_obligatorio(valor: str, campo: str) -> str:

    if valor is None or valor.strip() == "":
        raise ValueError(f"El campo {campo} no puede estar vacio.")
    return valor.strip()