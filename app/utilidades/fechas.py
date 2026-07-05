from datetime import date, timedelta

DIAS_MES_COMERCIAL = 30


def avanzar_periodos_comerciales(fecha_base: date, periodos: int) -> date:

    return fecha_base + timedelta(days=DIAS_MES_COMERCIAL * periodos)