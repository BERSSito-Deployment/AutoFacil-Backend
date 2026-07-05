from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import obtener_configuracion
from app.database import FabricaSesion, crear_tablas
from app.rutas import (
    auth,
    perfil,
    simulaciones,
    tipo_cambio,
    vehiculos,
)

configuracion = obtener_configuracion()

ETIQUETAS_OPENAPI = [
    {
        "name": "Autenticacion",
        "description": (
            "Registro e inicio de sesion del usuario"
        ),
    },
    {
        "name": "Perfil",
        "description": (
            "Consulta y actualizacion del perfil del propio usuario"
        ),
    },
    {
        "name": "Vehiculos",
        "description": (
            "Catalogo de vehiculos"
        ),
    },
    {
        "name": "Simulaciones",
        "description": (
            "Simulaciones del credito vehicular, con calculo financiero y cronograma de pagos"
        ),
    },
    {
        "name": "Tipo de cambio",
        "description": (
            "Consulta del tipo de cambio referencial USD/PEN en tiempo real"
        ),
    },
]


@asynccontextmanager
async def ciclo_vida(_: FastAPI):

    crear_tablas()
    from app.datos_semilla import sembrar_datos

    sesion = FabricaSesion()
    try:
        sembrar_datos(sesion)
    finally:
        sesion.close()
    yield


aplicacion = FastAPI(
    title="AutoFacil API",
    version=configuracion.version_aplicacion,
    openapi_tags=ETIQUETAS_OPENAPI,
    swagger_ui_parameters={"persistAuthorization": True},
    lifespan=ciclo_vida,
)

aplicacion.add_middleware(
    CORSMiddleware,
    allow_origins=configuracion.origenes_cors,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

aplicacion.include_router(auth.enrutador)
aplicacion.include_router(perfil.enrutador)
aplicacion.include_router(vehiculos.enrutador)
aplicacion.include_router(simulaciones.enrutador)
aplicacion.include_router(tipo_cambio.enrutador)


@aplicacion.get("/", tags=["Estado"], summary="Estado del servicio")
def estado_servicio() -> dict:

    return {
        "aplicacion": configuracion.nombre_aplicacion,
        "version": configuracion.version_aplicacion,
        "estado": "activo",
    }


app = aplicacion