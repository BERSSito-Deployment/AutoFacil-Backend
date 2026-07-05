from decimal import Decimal
import pytest
from app.modelos.enumeraciones import Capitalizacion, TipoTasa
from app.servicios import servicio_tasas


def _aprox(valor: Decimal, esperado: str, tolerancia: str = "1e-9") -> bool:
    return abs(valor - Decimal(esperado)) < Decimal(tolerancia)


def test_tea_a_tem():
    tem = servicio_tasas.convertir_tea_a_tem(Decimal("0.10"))
    # (1.10)^(1/12) - 1
    assert _aprox(tem, "0.0079741404", "1e-8")


def test_tna_a_tea_y_tem_capitalizacion_mensual():
    tea, tem = servicio_tasas.calcular_tasas_equivalentes(
        TipoTasa.NOMINAL, Decimal("0.12"), Capitalizacion.MENSUAL
    )
    # TEA = (1 + 0.12/12)^12 - 1
    assert _aprox(tea, "0.1268250301", "1e-9")
    # TEM = (1 + TEA)^(1/12) - 1 = 0.01 exacto
    assert _aprox(tem, "0.01", "1e-12")


def test_tea_directa_devuelve_misma_tea():
    # tasa efectiva anual ingresada se conserva como TEA

    tea, tem = servicio_tasas.calcular_tasas_equivalentes(
        TipoTasa.EFECTIVA, Decimal("0.145"), None
    )
    assert tea == Decimal("0.145")
    assert _aprox(tem, "0.0113476210", "1e-9")


def test_nominal_sin_capitalizacion_lanza_error():
    # tasa nominal sin capitalizacion debe producir un error de validacion

    with pytest.raises(ValueError):
        servicio_tasas.calcular_tasas_equivalentes(
            TipoTasa.NOMINAL, Decimal("0.18"), None
        )


def test_tasa_negativa_lanza_error():
    # tasa negativa no debe aceptarse

    with pytest.raises(ValueError):
        servicio_tasas.calcular_tasas_equivalentes(
            TipoTasa.EFECTIVA, Decimal("-0.01"), None
        )
