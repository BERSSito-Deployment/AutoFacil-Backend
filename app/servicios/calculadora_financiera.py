"""Arma el cronograma de pagos del credito vehicular.

Idea general (producto "Compra Inteligente"):
El monto del prestamo se paga de dos formas a la vez:
  1) Cuotas mensuales normales (interes + parte del capital + seguros + cargos).
  2) La cuota final: un pago grande (un porcentaje del precio del auto) que se
     deja para el final y se paga de una sola vez justo despues de la ultima cuota.

Como una parte de la deuda se deja para el final, lo que se reparte en las
cuotas mensuales es menor y por eso salen mas baratas. Para saber cuanto
reparte cada mes, calculamos cuanto "vale hoy" esa cuota final y se lo restamos
al prestamo: el resto (saldo_financiado) es lo unico que amortizan las cuotas
mensuales. La cuota final, mientras tanto, va acumulando su interes mes a mes
hasta que se paga completa al final.

Al inicio puede haber meses de gracia: "total" = ese mes no se paga nada y el
interes se suma a la deuda; "parcial" = ese mes solo se paga el interes.

Todo se calcula con numeros de alta precision (Decimal) y solo se redondea al
mostrar el resultado. Cada mes equivale a 30 dias (mes comercial).
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from app.modelos.enumeraciones import TipoPeriodo
from app.utilidades.decimales import CERO, UNO, a_decimal, potencia
from app.utilidades.fechas import avanzar_periodos_comerciales


@dataclass
class ParametrosCronograma:
    """Parametros de entrada para construir un cronograma de pagos."""

    monto_prestamo: Decimal           # lo que se presta (precio - cuota inicial + costos financiados)
    cuota_final: Decimal              # el pago grande que se deja para el final
    tem: Decimal                      # tasa de interes mensual
    numero_cuotas: int                # cuantas cuotas mensuales (la cuota final se paga una despues)
    meses_gracia_total: int           # meses al inicio sin pagar nada
    meses_gracia_parcial: int         # meses al inicio pagando solo el interes
    seguro_desgravamen_mensual: Decimal  # % mensual del seguro de desgravamen
    seguro_riesgo_periodico: Decimal     # monto del seguro de riesgo por cuota
    gps_periodico: Decimal               # monto del GPS por cuota
    portes_periodico: Decimal            # monto de portes por cuota
    gastos_adm_periodico: Decimal        # monto de gastos administrativos por cuota
    fecha_inicio: date


@dataclass
class FilaCronograma:
    """Detalle calculado de un periodo del cronograma (valores sin redondear).

    Los importes se expresan como magnitudes positivas; `flujo` es lo que sale
    del bolsillo ese mes (negativo).
    """

    numero_periodo: int
    fecha_pago: date
    tipo_periodo: TipoPeriodo
    # Tramo de la cuota final (el pago que se difiere al final).
    saldo_inicial_cuota_final: Decimal
    interes_cuota_final: Decimal
    amortizacion_cuota_final: Decimal
    desgravamen_cuota_final: Decimal
    saldo_final_cuota_final: Decimal
    # Tramo de la cuota mensual normal.
    saldo_inicial: Decimal
    interes: Decimal
    cuota: Decimal
    amortizacion: Decimal
    seguro_desgravamen: Decimal
    seguro_riesgo: Decimal
    gps: Decimal
    portes: Decimal
    gastos_adm: Decimal
    saldo_final: Decimal
    flujo: Decimal


@dataclass
class ResultadoCronograma:
    """Cronograma generado junto con los totales acumulados sin redondear."""

    filas: list[FilaCronograma] = field(default_factory=list)
    saldo_financiado: Decimal = CERO   # lo que pagan las cuotas (prestamo - valor de hoy de la cuota final)
    cuota_ordinaria: Decimal = CERO    # la cuota mensual normal
    total_intereses: Decimal = CERO
    total_amortizado: Decimal = CERO
    total_seguro_desgravamen: Decimal = CERO
    total_seguro_riesgo: Decimal = CERO
    total_gps: Decimal = CERO
    total_portes: Decimal = CERO
    total_gastos_adm: Decimal = CERO
    monto_total_pagado: Decimal = CERO   # total que paga la persona (sin la cuota inicial)


def calcular_cuota_francesa(
    saldo_base: Decimal, tasa_periodica: Decimal, numero_periodos: int
) -> Decimal:
    """Calcula la cuota fija (misma cantidad cada mes) que, pagada n veces, deja el saldo en cero.

    Es el "metodo frances": todas las cuotas mensuales valen lo mismo; al inicio
    la cuota es casi todo interes y con el tiempo pasa a ser casi todo capital.
    """

    saldo_base = a_decimal(saldo_base)
    tasa_periodica = a_decimal(tasa_periodica)
    n = numero_periodos
    if n <= 0:
        raise ValueError("El numero de periodos ordinarios debe ser mayor que cero.")
    if tasa_periodica == CERO:
        return saldo_base / Decimal(n)
    factor = potencia(UNO + tasa_periodica, Decimal(n))
    return saldo_base * tasa_periodica * factor / (factor - UNO)


def generar_cronograma(parametros: ParametrosCronograma) -> ResultadoCronograma:
    """Construye el cronograma completo: N cuotas mensuales y la cuota final en el mes N+1."""

    prestamo = a_decimal(parametros.monto_prestamo)
    cuota_final = a_decimal(parametros.cuota_final)
    tem = a_decimal(parametros.tem)
    desgravamen = a_decimal(parametros.seguro_desgravamen_mensual)
    seguro_riesgo = a_decimal(parametros.seguro_riesgo_periodico)
    gps = a_decimal(parametros.gps_periodico)
    portes = a_decimal(parametros.portes_periodico)
    gastos_adm = a_decimal(parametros.gastos_adm_periodico)

    n = parametros.numero_cuotas
    meses_total = parametros.meses_gracia_total
    meses_parcial = parametros.meses_gracia_parcial

    if n <= 0:
        raise ValueError("El numero de cuotas debe ser mayor que cero.")
    if meses_total + meses_parcial >= n:
        raise ValueError("Los meses de gracia deben ser menores que el numero de cuotas.")

    # La cuota mensual carga el interes y el seguro de desgravamen juntos.
    tasa_con_desgravamen = tem + desgravamen

    # Cuanto "vale hoy" la cuota final (su valor presente): se trae al presente el
    # pago del mes N+1 usando la tasa mensual. Ese monto se le resta al prestamo;
    # lo que queda (saldo_financiado) es lo que pagan las cuotas mensuales.
    valor_presente_final = cuota_final / potencia(UNO + tasa_con_desgravamen, Decimal(n + 1))
    saldo_financiado = prestamo - valor_presente_final
    if saldo_financiado <= CERO:
        raise ValueError(
            "La cuota final es demasiado alta: no queda saldo para las cuotas mensuales."
        )

    resultado = ResultadoCronograma(saldo_financiado=saldo_financiado)

    saldo = saldo_financiado          # lo que falta pagar con cuotas mensuales
    saldo_cf = valor_presente_final   # lo que va acumulando la cuota final

    # Recorremos mes por mes, desde la cuota 1 hasta el pago final (N+1).
    for nc in range(1, n + 2):
        fecha = avanzar_periodos_comerciales(parametros.fecha_inicio, nc)

        # --- La cuota final (el pago grande que espera al final) ---
        # Cada mes acumula su interes y desgravamen (crece sin pagarse).
        interes_cf = saldo_cf * tem
        desgravamen_cf = saldo_cf * desgravamen
        if nc == n + 1:
            # Mes final: se paga completa (saldo acumulado + lo del mes).
            amortizacion_cf = saldo_cf + interes_cf + desgravamen_cf
            saldo_final_cf = CERO
        else:
            amortizacion_cf = CERO
            saldo_final_cf = saldo_cf + interes_cf + desgravamen_cf

        # --- La cuota mensual normal ---
        if nc > n:
            # En el mes N+1 ya no hay cuota mensual, solo el pago final.
            saldo_inicial = CERO
            interes = cuota = amortizacion = seguro_desgravamen = CERO
            saldo_final = CERO
            tipo_periodo = TipoPeriodo.CUOTA_FINAL
        else:
            saldo_inicial = saldo
            interes = saldo * tem                 # interes del mes sobre lo que falta
            seguro_desgravamen = saldo * desgravamen
            if nc <= meses_total:
                # Gracia total: no se paga nada; el interes se suma a la deuda.
                cuota = amortizacion = CERO
                saldo_final = saldo + interes
                tipo_periodo = TipoPeriodo.GRACIA_TOTAL
            elif nc <= meses_total + meses_parcial:
                # Gracia parcial: solo se paga el interes; la deuda queda igual.
                cuota = interes
                amortizacion = CERO
                saldo_final = saldo
                tipo_periodo = TipoPeriodo.GRACIA_PARCIAL
            else:
                # Cuota fija: la misma cantidad cada mes hasta el final, calculada
                # para que, pagandola en los meses que faltan, el saldo llegue a cero.
                periodos_restantes = n - nc + 1
                cuota = calcular_cuota_francesa(
                    saldo, tasa_con_desgravamen, periodos_restantes
                )
                # Amortizacion: la parte de la cuota que baja la deuda (lo que queda
                # despues de cubrir el interes y el seguro de ese mes).
                amortizacion = cuota - interes - seguro_desgravamen
                saldo_final = saldo - amortizacion
                tipo_periodo = TipoPeriodo.CUOTA_ORDINARIA
                if resultado.cuota_ordinaria == CERO:
                    resultado.cuota_ordinaria = cuota

        # --- Lo que efectivamente paga la persona este mes (el "flujo") ---
        # Cuota + seguro de riesgo + GPS + portes + gastos administrativos.
        egreso = cuota + seguro_riesgo + gps + portes + gastos_adm
        if tipo_periodo in (TipoPeriodo.GRACIA_TOTAL, TipoPeriodo.GRACIA_PARCIAL):
            # En los meses de gracia el desgravamen no va dentro de la cuota:
            # se cobra aparte, asi que aqui lo sumamos.
            egreso += seguro_desgravamen
        if nc == n + 1:
            egreso += amortizacion_cf            # el ultimo mes tambien paga la cuota final
        flujo = -egreso                          # negativo: es dinero que sale

        resultado.filas.append(
            FilaCronograma(
                numero_periodo=nc,
                fecha_pago=fecha,
                tipo_periodo=tipo_periodo,
                saldo_inicial_cuota_final=saldo_cf,
                interes_cuota_final=interes_cf,
                amortizacion_cuota_final=amortizacion_cf,
                desgravamen_cuota_final=desgravamen_cf,
                saldo_final_cuota_final=saldo_final_cf,
                saldo_inicial=saldo_inicial,
                interes=interes,
                cuota=cuota,
                amortizacion=amortizacion,
                seguro_desgravamen=seguro_desgravamen,
                seguro_riesgo=seguro_riesgo,
                gps=gps,
                portes=portes,
                gastos_adm=gastos_adm,
                saldo_final=saldo_final,
                flujo=flujo,
            )
        )

        # --- Vamos sumando los totales para el resumen final ---
        if nc <= n:
            # El interes del mes es lo que queda de la cuota tras quitar capital y seguro.
            resultado.total_intereses += cuota - amortizacion - seguro_desgravamen
            resultado.total_amortizado += amortizacion
            resultado.total_seguro_desgravamen += seguro_desgravamen
        resultado.total_amortizado += amortizacion_cf
        resultado.total_seguro_riesgo += seguro_riesgo
        resultado.total_gps += gps
        resultado.total_portes += portes
        resultado.total_gastos_adm += gastos_adm
        resultado.monto_total_pagado += egreso

        saldo = saldo_final
        saldo_cf = saldo_final_cf

    return resultado
