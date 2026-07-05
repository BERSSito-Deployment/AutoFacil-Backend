"""Rutas de calculo y gestion de simulaciones (cada usuario ve solo las suyas)."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import obtener_sesion
from app.esquemas.cronograma import CronogramaFilaRespuesta
from app.esquemas.simulacion import (
    ResultadoCalculo,
    SimulacionCalcularRequest,
    SimulacionDetalle,
    SimulacionGuardarRequest,
    SimulacionListado,
    SimulacionRespuesta,
)
from app.modelos.enumeraciones import EstadoSimulacion
from app.modelos.simulacion import Simulacion
from app.modelos.usuario import Usuario
from app.modelos.vehiculo import Vehiculo
from app.seguridad.dependencias import obtener_usuario_actual
from app.servicios.servicio_gestion_simulacion import (
    aplicar_resultado_a_modelo,
    calcular_desde_solicitud,
    construir_filas_cronograma,
    convertir_precio,
)
from app.servicios.servicio_simulacion import redondear_resultado
from app.utilidades.respuestas import error_no_encontrado, error_validacion

enrutador = APIRouter(prefix="/simulaciones", tags=["Simulaciones"])


def _validar_para_crear(
    sesion: Session, solicitud: SimulacionCalcularRequest
) -> Vehiculo:
    """Valida una nueva simulacion: el vehiculo del catalogo existe y esta activo."""

    vehiculo = sesion.get(Vehiculo, solicitud.vehiculo_id)
    if vehiculo is None or not vehiculo.activo:
        raise error_validacion("El vehiculo seleccionado no existe o esta inactivo.")
    return vehiculo


def _vehiculo_de_simulacion(
    sesion: Session, solicitud: SimulacionCalcularRequest
) -> Vehiculo:
    """Obtiene el vehiculo para previsualizar, editar o recalcular (no exige que siga activo)."""

    vehiculo = sesion.get(Vehiculo, solicitud.vehiculo_id)
    if vehiculo is None:
        raise error_validacion("El vehiculo de la simulacion ya no existe.")
    return vehiculo


def _codigo_siguiente(sesion: Session, usuario: Usuario) -> str:
    """Correlativo por usuario: la primera simulacion de cada cuenta es la 1."""

    existentes = (
        sesion.query(Simulacion).filter(Simulacion.usuario_id == usuario.id).count()
    )
    return f"SIM-{existentes + 1:06d}"


def _obtener_simulacion(sesion: Session, simulacion_id: int, usuario: Usuario) -> Simulacion:
    """Obtiene una simulacion propia o lanza 404 si no existe o no es del usuario."""

    simulacion = sesion.get(Simulacion, simulacion_id)
    if simulacion is None or simulacion.usuario_id != usuario.id:
        raise error_no_encontrado("La simulacion indicada no existe.")
    return simulacion


def _a_detalle(simulacion: Simulacion) -> SimulacionDetalle:
    """Construye la representacion detallada de una simulacion."""

    base = SimulacionRespuesta.model_validate(simulacion).model_dump()
    return SimulacionDetalle(
        **base,
        vehiculo_descripcion=(
            f"{simulacion.vehiculo.marca} {simulacion.vehiculo.modelo}"
            if simulacion.vehiculo
            else None
        ),
        usuario_nombre=(
            f"{simulacion.usuario.nombre} {simulacion.usuario.apellido}"
            if simulacion.usuario
            else None
        ),
        cronograma=[
            CronogramaFilaRespuesta.model_validate(fila)
            for fila in simulacion.cronograma
        ],
    )


def _a_listado(simulacion: Simulacion) -> SimulacionListado:
    """Construye el resumen de una simulacion para listados."""

    return SimulacionListado(
        id=simulacion.id,
        codigo=simulacion.codigo,
        nombre=simulacion.nombre,
        estado=simulacion.estado,
        moneda=simulacion.moneda,
        plan=simulacion.plan,
        vehiculo_id=simulacion.vehiculo_id,
        vehiculo_descripcion=(
            f"{simulacion.vehiculo.marca} {simulacion.vehiculo.modelo}"
            if simulacion.vehiculo
            else None
        ),
        monto_prestamo=float(simulacion.monto_prestamo),
        numero_cuotas=simulacion.numero_cuotas,
        cuota_mensual=float(simulacion.cuota_mensual),
        # Pago real del mes: la cuota mas el seguro de riesgo, GPS, portes y
        # gastos administrativos de cada periodo.
        pago_mensual=float(
            simulacion.cuota_mensual
            + simulacion.seguro_riesgo_periodico
            + simulacion.gps_periodico
            + simulacion.portes_periodico
            + simulacion.gastos_adm_periodico
        ),
        tcea=float(simulacion.tcea) if simulacion.tcea is not None else None,
        fecha_creacion=simulacion.fecha_creacion,
    )


def _solicitud_desde_modelo(simulacion: Simulacion) -> SimulacionCalcularRequest:
    """Reconstruye la solicitud de calculo a partir de una simulacion guardada."""

    return SimulacionCalcularRequest(
        vehiculo_id=simulacion.vehiculo_id,
        nombre=simulacion.nombre,
        moneda=simulacion.moneda,
        tipo_cambio_referencial=simulacion.tipo_cambio_referencial,
        plan=simulacion.plan,
        numero_cuotas=simulacion.numero_cuotas,
        dias_anio=simulacion.dias_anio,
        porcentaje_cuota_inicial=simulacion.porcentaje_cuota_inicial,
        porcentaje_cuota_final=simulacion.porcentaje_cuota_final,
        tipo_tasa=simulacion.tipo_tasa,
        valor_tasa=simulacion.tasa_ingresada,
        capitalizacion=simulacion.capitalizacion,
        meses_gracia_total=simulacion.meses_gracia_total,
        meses_gracia_parcial=simulacion.meses_gracia_parcial,
        costo_notarial=simulacion.costo_notarial,
        costo_notarial_financiado=simulacion.costo_notarial_financiado,
        costo_registral=simulacion.costo_registral,
        costo_registral_financiado=simulacion.costo_registral_financiado,
        costo_tasacion=simulacion.costo_tasacion,
        costo_tasacion_financiado=simulacion.costo_tasacion_financiado,
        comision_estudio=simulacion.comision_estudio,
        comision_estudio_financiado=simulacion.comision_estudio_financiado,
        comision_activacion=simulacion.comision_activacion,
        comision_activacion_financiado=simulacion.comision_activacion_financiado,
        gps_periodico=simulacion.gps_periodico,
        portes_periodico=simulacion.portes_periodico,
        gastos_adm_periodico=simulacion.gastos_adm_periodico,
        seguro_desgravamen_mensual=simulacion.seguro_desgravamen_mensual,
        seguro_riesgo_anual=simulacion.seguro_riesgo_anual,
        cok_anual=simulacion.cok_anual,
        fecha_inicio=simulacion.fecha_inicio,
    )


@enrutador.get("", response_model=list[SimulacionListado], summary="Listar simulaciones")
def listar_simulaciones(
    busqueda: str | None = Query(default=None),
    vehiculo_id: int | None = Query(default=None),
    estado: EstadoSimulacion | None = Query(default=None),
    sesion: Session = Depends(obtener_sesion),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
) -> list[SimulacionListado]:
    """Lista las simulaciones del usuario, con busqueda y filtros opcionales.

    La busqueda libre encuentra por nombre, codigo o datos del vehiculo.
    """

    consulta = (
        sesion.query(Simulacion)
        .filter(Simulacion.usuario_id == usuario_actual.id)
        .outerjoin(Vehiculo, Simulacion.vehiculo_id == Vehiculo.id)
    )
    if vehiculo_id is not None:
        consulta = consulta.filter(Simulacion.vehiculo_id == vehiculo_id)
    if estado is not None:
        consulta = consulta.filter(Simulacion.estado == estado)
    if busqueda:
        patron = f"%{busqueda}%"
        consulta = consulta.filter(
            or_(
                Simulacion.nombre.ilike(patron),
                Simulacion.codigo.ilike(patron),
                Vehiculo.marca.ilike(patron),
                Vehiculo.modelo.ilike(patron),
            )
        )

    simulaciones = consulta.order_by(Simulacion.fecha_creacion.desc()).all()
    return [_a_listado(simulacion) for simulacion in simulaciones]


@enrutador.post(
    "/calcular",
    response_model=ResultadoCalculo,
    summary="Calcular simulacion sin guardar (previsualizacion)",
)
def calcular_simulacion_preview(
    solicitud: SimulacionCalcularRequest,
    sesion: Session = Depends(obtener_sesion),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
) -> dict:
    """Calcula una simulacion sin persistirla (previsualizacion)."""

    vehiculo = _vehiculo_de_simulacion(sesion, solicitud)
    try:
        resultado = calcular_desde_solicitud(solicitud, vehiculo)
    except ValueError as exc:
        raise error_validacion(str(exc)) from exc
    return redondear_resultado(resultado)


@enrutador.post(
    "",
    response_model=SimulacionDetalle,
    status_code=status.HTTP_201_CREATED,
    summary="Calcular y guardar una simulacion",
)
def crear_simulacion(
    solicitud: SimulacionGuardarRequest,
    sesion: Session = Depends(obtener_sesion),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
) -> SimulacionDetalle:
    """Calcula y guarda una nueva simulacion junto con su cronograma."""

    vehiculo = _validar_para_crear(sesion, solicitud)
    try:
        resultado = calcular_desde_solicitud(solicitud, vehiculo)
    except ValueError as exc:
        raise error_validacion(str(exc)) from exc

    simulacion = Simulacion(
        codigo=_codigo_siguiente(sesion, usuario_actual),
        vehiculo_id=solicitud.vehiculo_id,
        usuario_id=usuario_actual.id,
        estado=solicitud.estado,
    )
    aplicar_resultado_a_modelo(simulacion, solicitud, resultado)
    sesion.add(simulacion)
    sesion.flush()
    simulacion.cronograma = construir_filas_cronograma(resultado)
    sesion.commit()
    sesion.refresh(simulacion)
    return _a_detalle(simulacion)


@enrutador.get(
    "/{simulacion_id}",
    response_model=SimulacionDetalle,
    summary="Obtener detalle de una simulacion",
)
def obtener_simulacion(
    simulacion_id: int,
    sesion: Session = Depends(obtener_sesion),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
) -> SimulacionDetalle:
    """Obtiene el detalle completo de una simulacion propia, incluido el cronograma."""

    return _a_detalle(_obtener_simulacion(sesion, simulacion_id, usuario_actual))


@enrutador.put(
    "/{simulacion_id}",
    response_model=SimulacionDetalle,
    summary="Editar parametros y recalcular una simulacion",
)
def actualizar_simulacion(
    simulacion_id: int,
    solicitud: SimulacionGuardarRequest,
    sesion: Session = Depends(obtener_sesion),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
) -> SimulacionDetalle:
    """Edita los parametros de una simulacion propia y recalcula su cronograma."""

    simulacion = _obtener_simulacion(sesion, simulacion_id, usuario_actual)
    vehiculo = _vehiculo_de_simulacion(sesion, solicitud)
    # Conserva el precio original (convertido si cambia la moneda) salvo que se pida actualizarlo.
    if solicitud.actualizar_precio:
        precio_operacion = None
    else:
        precio_operacion = convertir_precio(
            simulacion.precio_vehiculo,
            simulacion.moneda,
            solicitud.moneda,
            solicitud.tipo_cambio_referencial,
        )
    try:
        resultado = calcular_desde_solicitud(solicitud, vehiculo, precio_operacion=precio_operacion)
    except ValueError as exc:
        raise error_validacion(str(exc)) from exc

    simulacion.vehiculo_id = solicitud.vehiculo_id
    # Editar no cambia el estado.
    aplicar_resultado_a_modelo(simulacion, solicitud, resultado)
    simulacion.cronograma = construir_filas_cronograma(resultado)
    sesion.commit()
    sesion.refresh(simulacion)
    return _a_detalle(simulacion)


@enrutador.post(
    "/{simulacion_id}/recalcular",
    response_model=SimulacionDetalle,
    summary="Recalcular una simulacion con sus parametros guardados",
)
def recalcular_simulacion(
    simulacion_id: int,
    sesion: Session = Depends(obtener_sesion),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
) -> SimulacionDetalle:
    """Recalcula una simulacion propia usando sus parametros almacenados."""

    simulacion = _obtener_simulacion(sesion, simulacion_id, usuario_actual)
    solicitud = _solicitud_desde_modelo(simulacion)
    vehiculo = _vehiculo_de_simulacion(sesion, solicitud)
    try:
        # Conserva el precio original de la operacion.
        resultado = calcular_desde_solicitud(
            solicitud, vehiculo, precio_operacion=simulacion.precio_vehiculo
        )
    except ValueError as exc:
        raise error_validacion(str(exc)) from exc

    aplicar_resultado_a_modelo(simulacion, solicitud, resultado)
    simulacion.cronograma = construir_filas_cronograma(resultado)
    sesion.commit()
    sesion.refresh(simulacion)
    return _a_detalle(simulacion)


@enrutador.delete(
    "/{simulacion_id}",
    response_model=SimulacionDetalle,
    summary="Archivar una simulacion (baja logica)",
)
def archivar_simulacion(
    simulacion_id: int,
    sesion: Session = Depends(obtener_sesion),
    usuario_actual: Usuario = Depends(obtener_usuario_actual),
) -> SimulacionDetalle:
    """Archiva una simulacion propia (baja logica): la marca como ARCHIVADA."""

    simulacion = _obtener_simulacion(sesion, simulacion_id, usuario_actual)
    simulacion.estado = EstadoSimulacion.ARCHIVADA
    sesion.commit()
    sesion.refresh(simulacion)
    return _a_detalle(simulacion)
