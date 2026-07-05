from __future__ import annotations
import time
from decimal import Decimal
import httpx

MONEDAS_VALIDAS = {"USD", "PEN"}

_URL_PROVEEDOR = "https://open.er-api.com/v6/latest/{base}"
_FUENTE_LINEA = "open.er-api.com"

_TTL_CACHE = 60 * 60

_TASAS_POR_DEFECTO: dict[str, dict[str, Decimal]] = {
    "USD": {"PEN": Decimal("3.75")},
    "PEN": {"USD": Decimal("0.2667")},
}

_cache: dict[str, tuple[float, dict[str, Decimal]]] = {}


class ParMonedaInvalido(ValueError):
    """datos invalidos"""


def _consultar_proveedor(base: str) -> dict[str, Decimal] | None:
    try:
        respuesta = httpx.get(_URL_PROVEEDOR.format(base=base), timeout=5.0)
        respuesta.raise_for_status()
        cuerpo = respuesta.json()
    except (httpx.HTTPError, ValueError):
        return None
    if cuerpo.get("result") != "success":
        return None
    tasas_crudas = cuerpo.get("rates") or {}
    return {moneda: Decimal(str(valor)) for moneda, valor in tasas_crudas.items()}


def _obtener_tasas(base: str) -> tuple[dict[str, Decimal], str]:

    ahora = time.monotonic()
    en_cache = _cache.get(base)
    if en_cache and ahora - en_cache[0] < _TTL_CACHE:
        return en_cache[1], "linea"

    tasas = _consultar_proveedor(base)
    if tasas:
        _cache[base] = (ahora, tasas)
        return tasas, "linea"

    if en_cache:
        return en_cache[1], "cache"
    return _TASAS_POR_DEFECTO.get(base, {}), "local"


def obtener_tipo_cambio(base: str, destino: str) -> dict:

    base = (base or "").upper().strip()
    destino = (destino or "").upper().strip()
    if base not in MONEDAS_VALIDAS or destino not in MONEDAS_VALIDAS:
        raise ParMonedaInvalido(
            "Solo se admite la conversion entre Soles (PEN) y Dolares (USD)."
        )

    if base == destino:
        return {
            "base": base,
            "destino": destino,
            "tasa": Decimal("1"),
            "fuente": "par identico",
            "en_linea": True,
        }

    tasas, origen = _obtener_tasas(base)
    tasa = tasas.get(destino)
    if tasa is None:
        tasa = _TASAS_POR_DEFECTO.get(base, {}).get(destino)
        origen = "local"
    if tasa is None:
        raise ParMonedaInvalido(
            "No hay tipo de cambio disponible para el par solicitado."
        )

    fuente = {
        "linea": _FUENTE_LINEA,
        "cache": "cache (dato no actualizado)",
        "local": "valor referencial local",
    }[origen]

    return {
        "base": base,
        "destino": destino,
        "tasa": tasa,
        "fuente": fuente,
        "en_linea": origen == "linea",
    }