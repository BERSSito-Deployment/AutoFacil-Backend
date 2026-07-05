from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database import obtener_sesion
from app.esquemas.auth import (
    CredencialesLogin,
    RegistroRequest,
    TokenRespuesta,
)
from app.esquemas.usuario import UsuarioRespuesta
from app.modelos.usuario import Usuario
from app.seguridad.dependencias import obtener_usuario_actual
from app.seguridad.hash import hashear_password, verificar_password
from app.seguridad.jwt import crear_token_acceso
from app.utilidades.respuestas import error_autenticacion, error_conflicto

enrutador = APIRouter(prefix="/auth", tags=["Autenticacion"])


def _autenticar(sesion: Session, correo: str, password: str) -> Usuario:
    correo = (correo or "").strip().lower()
    usuario = sesion.query(Usuario).filter(Usuario.correo == correo).first()
    if usuario is None or not verificar_password(password, usuario.password_hash):
        raise error_autenticacion("Correo o contrasena incorrectos.")
    if not usuario.activo:
        raise error_autenticacion("El usuario se encuentra inactivo.")
    return usuario


@enrutador.post(
    "/login",
    response_model=TokenRespuesta,
    summary="Iniciar sesion",
)
def login(
    datos: OAuth2PasswordRequestForm = Depends(),
    sesion: Session = Depends(obtener_sesion),
) -> TokenRespuesta:
    
    usuario = _autenticar(sesion, datos.username, datos.password)
    token = crear_token_acceso(str(usuario.id))
    return TokenRespuesta(access_token=token)


@enrutador.post(
    "/login-json",
    response_model=TokenRespuesta,
    summary="Iniciar sesion",
)
def login_json(
    credenciales: CredencialesLogin,
    sesion: Session = Depends(obtener_sesion),
) -> TokenRespuesta:

    usuario = _autenticar(sesion, credenciales.correo, credenciales.password)
    token = crear_token_acceso(str(usuario.id))
    return TokenRespuesta(access_token=token)


@enrutador.post(
    "/registro",
    response_model=TokenRespuesta,
    summary="Registrar un nuevo usuario e iniciar sesion",
)
def registro(
    datos: RegistroRequest,
    sesion: Session = Depends(obtener_sesion),
) -> TokenRespuesta:
    duplicado = sesion.query(Usuario).filter(Usuario.correo == datos.correo).first()
    if duplicado is not None:
        raise error_conflicto("El correo ya esta registrado.")

    usuario = Usuario(
        nombre=datos.nombre,
        apellido=datos.apellido,
        correo=datos.correo,
        password_hash=hashear_password(datos.password),
        activo=True,
    )
    sesion.add(usuario)
    sesion.commit()
    sesion.refresh(usuario)
    token = crear_token_acceso(str(usuario.id))
    return TokenRespuesta(access_token=token)


@enrutador.get("/me", response_model=UsuarioRespuesta, summary="Perfil del usuario autenticado")
def perfil_actual(usuario_actual: Usuario = Depends(obtener_usuario_actual)) -> Usuario:

    return usuario_actual
