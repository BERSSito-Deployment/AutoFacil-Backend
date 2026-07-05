from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.database import obtener_sesion
from app.esquemas.vehiculo import VehiculoActualizar, VehiculoCrear, VehiculoRespuesta
from app.modelos.usuario import Usuario
from app.modelos.vehiculo import Vehiculo
from app.seguridad.dependencias import obtener_usuario_actual
from app.utilidades.respuestas import error_no_encontrado

enrutador = APIRouter(prefix="/vehiculos", tags=["Vehiculos"])


def _obtener(sesion: Session, vehiculo_id: int) -> Vehiculo:
    vehiculo = sesion.get(Vehiculo, vehiculo_id)
    if vehiculo is None or not vehiculo.activo:
        raise error_no_encontrado("El vehiculo indicado no existe.")
    return vehiculo


@enrutador.get("", response_model=list[VehiculoRespuesta], summary="Listar y buscar vehiculos")
def listar_vehiculos(
    busqueda: str | None = Query(default=None),
    sesion: Session = Depends(obtener_sesion),
    _: Usuario = Depends(obtener_usuario_actual),
) -> list[Vehiculo]:
    consulta = sesion.query(Vehiculo).filter(Vehiculo.activo.is_(True))
    if busqueda:
        patron = f"%{busqueda}%"
        consulta = consulta.filter(
            or_(
                Vehiculo.marca.ilike(patron),
                Vehiculo.modelo.ilike(patron),
                Vehiculo.version.ilike(patron),
            )
        )
    return consulta.order_by(Vehiculo.marca, Vehiculo.modelo).all()


@enrutador.get("/{vehiculo_id}", response_model=VehiculoRespuesta, summary="Obtener un vehiculo")
def obtener_vehiculo(
    vehiculo_id: int,
    sesion: Session = Depends(obtener_sesion),
    _: Usuario = Depends(obtener_usuario_actual),
) -> Vehiculo:

    return _obtener(sesion, vehiculo_id)


@enrutador.post(
    "",
    response_model=VehiculoRespuesta,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un vehiculo",
)
def crear_vehiculo(
    datos: VehiculoCrear,
    sesion: Session = Depends(obtener_sesion),
    _: Usuario = Depends(obtener_usuario_actual),
) -> Vehiculo:

    vehiculo = Vehiculo(**datos.model_dump())
    sesion.add(vehiculo)
    sesion.commit()
    sesion.refresh(vehiculo)
    return vehiculo


@enrutador.put("/{vehiculo_id}", response_model=VehiculoRespuesta, summary="Actualizar un vehiculo")
def actualizar_vehiculo(
    vehiculo_id: int,
    datos: VehiculoActualizar,
    sesion: Session = Depends(obtener_sesion),
    _: Usuario = Depends(obtener_usuario_actual),
) -> Vehiculo:
    vehiculo = _obtener(sesion, vehiculo_id)
    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(vehiculo, campo, valor)
    sesion.commit()
    sesion.refresh(vehiculo)
    return vehiculo


@enrutador.delete(
    "/{vehiculo_id}",
    response_model=VehiculoRespuesta,
    summary="Quitar un vehiculo",
)
def quitar_vehiculo(
    vehiculo_id: int,
    sesion: Session = Depends(obtener_sesion),
    _: Usuario = Depends(obtener_usuario_actual),
) -> Vehiculo:
    vehiculo = _obtener(sesion, vehiculo_id)
    vehiculo.activo = False
    sesion.commit()
    sesion.refresh(vehiculo)
    return vehiculo
