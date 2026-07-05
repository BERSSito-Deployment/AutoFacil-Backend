import os
import tempfile
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, obtener_sesion
from app.modelos.enumeraciones import Moneda
from app.modelos.usuario import Usuario
from app.modelos.vehiculo import Vehiculo
from app.rutas import auth, perfil, simulaciones, tipo_cambio, vehiculos
from app.seguridad.hash import hashear_password

_RUTA = os.path.join(tempfile.gettempdir(), "_autofacil_pytest_api.db")
_motor = create_engine(f"sqlite:///{_RUTA}", connect_args={"check_same_thread": False})
SesionPrueba = sessionmaker(bind=_motor, autoflush=False, autocommit=False)
app = FastAPI()
app.include_router(auth.enrutador)
app.include_router(perfil.enrutador)
app.include_router(vehiculos.enrutador)
app.include_router(simulaciones.enrutador)
app.include_router(tipo_cambio.enrutador)


def _sesion_override():
    sesion = SesionPrueba()
    try:
        yield sesion
    finally:
        sesion.close()


app.dependency_overrides[obtener_sesion] = _sesion_override
cliente = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def preparar_datos():
    """Crea el esquema, dos usuarios y el catalogo compartido de vehiculos."""

    Base.metadata.drop_all(_motor)
    Base.metadata.create_all(_motor)
    sesion = SesionPrueba()
    sesion.add_all(
        [
            Usuario(
                nombre="Usuario", apellido="Uno", correo="usuario1@autofacil.local",
                password_hash=hashear_password("Clave123"),
            ),
            Usuario(
                nombre="Usuario", apellido="Dos", correo="usuario2@autofacil.local",
                password_hash=hashear_password("Clave456"),
            ),
            Vehiculo(marca="Toyota", modelo="Yaris", anio=2026,
                     precio=80000, moneda=Moneda.SOLES),
            Vehiculo(marca="Hyundai", modelo="Tucson", anio=2026,
                     precio=35000, moneda=Moneda.DOLARES),
        ]
    )
    sesion.commit()
    sesion.close()
    yield
    app.dependency_overrides.clear()
    _motor.dispose()
    if os.path.exists(_RUTA):
        os.remove(_RUTA)


def _token(correo: str, password: str) -> str:
    return cliente.post(
        "/auth/login-json", json={"correo": correo, "password": password}
    ).json()["access_token"]


def _headers() -> dict:
    return {"Authorization": f"Bearer {_token('usuario1@autofacil.local', 'Clave123')}"}


def _headers2() -> dict:
    return {"Authorization": f"Bearer {_token('usuario2@autofacil.local', 'Clave456')}"}


def _ids():
    h = _headers()
    veh = cliente.get("/vehiculos", headers=h).json()
    return h, veh


def _veh_pen(veh):
    return next(v for v in veh if v["moneda"] == "PEN")


def _solicitud_base(vehiculo_id, moneda="PEN", **extra):
    base = {
        "vehiculo_id": vehiculo_id, "moneda": moneda,
        "plan": "PLAN_36", "tipo_tasa": "EFECTIVA", "valor_tasa": 0.15,
        "porcentaje_cuota_inicial": 0.2, "cok_anual": 0.10,
    }
    base.update(extra)
    return base


def _crear_sim(h, veh, **extra):
    return cliente.post(
        "/simulaciones",
        json=_solicitud_base(_veh_pen(veh)["id"], **extra),
        headers=h,
    )


def test_moneda_distinta_convierte_precio():
    h, veh = _ids()
    veh_usd = next(v for v in veh if v["moneda"] == "USD")
    r = cliente.post(
        "/simulaciones/calcular",
        json=_solicitud_base(veh_usd["id"], moneda="PEN", tipo_cambio_referencial=3.75),
        headers=h,
    )
    assert r.status_code == 200
    assert r.json()["moneda"] == "PEN"
    assert r.json()["precio_vehiculo"] == pytest.approx(veh_usd["precio"] * 3.75, abs=0.01)


def test_moneda_distinta_sin_tipo_cambio_rechazada():
    h, veh = _ids()
    veh_usd = next(v for v in veh if v["moneda"] == "USD")
    r = cliente.post(
        "/simulaciones/calcular",
        json=_solicitud_base(veh_usd["id"], moneda="PEN"),
        headers=h,
    )
    assert r.status_code == 400
    assert "tipo de cambio" in r.json()["detail"].lower()


def test_crear_con_vehiculo_quitado_rechazado():
    h, veh = _ids()
    creado = cliente.post(
        "/vehiculos",
        json={"marca": "Kia", "modelo": "Rio", "anio": 2024, "precio": 60000, "moneda": "PEN"},
        headers=h,
    ).json()
    cliente.delete(f"/vehiculos/{creado['id']}", headers=h)
    r = cliente.post(
        "/simulaciones",
        json=_solicitud_base(creado["id"]),
        headers=h,
    )
    assert r.status_code == 400


def test_cualquier_vehiculo_visible_se_puede_simular():
    h, veh = _ids()
    assert veh, "Deberia haber vehiculos disponibles para simular."
    for objetivo in veh:
        r = cliente.post(
            "/simulaciones/calcular",
            json=_solicitud_base(objetivo["id"], moneda=objetivo["moneda"], tipo_cambio_referencial=3.8),
            headers=h,
        )
        assert r.status_code == 200, r.text


def test_planes_difieren_la_cuota_final_y_cierran_en_cero():
    h, veh = _ids()
    veh_pen = _veh_pen(veh)["id"]

    plan36 = cliente.post(
        "/simulaciones/calcular",
        json=_solicitud_base(veh_pen, plan="PLAN_36"),
        headers=h,
    ).json()
    plan24 = cliente.post(
        "/simulaciones/calcular",
        json=_solicitud_base(veh_pen, plan="PLAN_24"),
        headers=h,
    ).json()

    # la cuota final predeterminada es 40% (Plan 36) y 50% (Plan 24) del precio
    assert plan36["porcentaje_cuota_final"] == 0.40
    assert plan24["porcentaje_cuota_final"] == 0.50
    # el cronograma tiene n filas y la cuota final se paga en la ultima.
    assert len(plan36["cronograma"]) == 37 and len(plan24["cronograma"]) == 25
    for res in (plan36, plan24):
        ultima = res["cronograma"][-1]
        assert ultima["tipo_periodo"] == "CUOTA_FINAL"
        assert ultima["amortizacion_cuota_final"] > 0
        assert abs(ultima["saldo_final_cuota_final"]) < 0.01
        assert abs(ultima["saldo_final"]) < 0.01


def test_simulacion_valida_saldo_cero_e_indicadores():
    h, veh = _ids()
    r = _crear_sim(h, veh)
    assert r.status_code == 201
    sim = r.json()
    assert abs(sim["cronograma"][-1]["saldo_final_cuota_final"]) < 0.01
    assert sim["van"] is not None and sim["tir_mensual"] is not None and sim["tcea"] is not None
    assert "saldo_financiado" in sim


def test_catalogo_compartido_y_simulaciones_aisladas():
    # el catalogo es el mismo para todos pero las simulaciones son para cada usuario"""

    h1, veh = _ids()
    # ambos ven el mismo catalogo
    veh2 = cliente.get("/vehiculos", headers=_headers2()).json()
    assert {v["id"] for v in veh} == {v["id"] for v in veh2}

    # el usuario 1 crea una simulacion
    sim = _crear_sim(h1, veh).json()

    # el usuario 2 no la ve en su historial ni puede abrirla
    h2 = _headers2()
    lista2 = cliente.get("/simulaciones", headers=h2).json()
    assert all(s["id"] != sim["id"] for s in lista2)
    assert cliente.get(f"/simulaciones/{sim['id']}", headers=h2).status_code == 404
    assert cliente.delete(f"/simulaciones/{sim['id']}", headers=h2).status_code == 404
    eliminada = cliente.delete(f"/simulaciones/{sim['id']}", headers=h1)
    assert eliminada.status_code == 200
    assert cliente.get(f"/simulaciones/{sim['id']}", headers=h1).status_code == 404


def test_busqueda_historial_por_vehiculo():
    h, veh = _ids()
    _crear_sim(h, veh)
    por_vehiculo = cliente.get("/simulaciones", params={"busqueda": "Toyota"}, headers=h).json()
    assert len(por_vehiculo) >= 1


def test_listado_muestra_pago_mensual_total():
    h, veh = _ids()
    sim = _crear_sim(
        h,
        veh,
        gps_periodico=20,
        portes_periodico=3.5,
        gastos_adm_periodico=3.5,
        seguro_riesgo_anual=0.003,
    ).json()

    listado = cliente.get("/simulaciones", headers=h).json()
    item = next(fila for fila in listado if fila["id"] == sim["id"])
    esperado = (
        sim["cuota_mensual"]
        + sim["seguro_riesgo_periodico"]
        + sim["gps_periodico"]
        + sim["portes_periodico"]
        + sim["gastos_adm_periodico"]
    )
    assert item["pago_mensual"] == pytest.approx(esperado, abs=0.01)
    assert item["pago_mensual"] > item["cuota_mensual"]


def test_registro_correo_obligatorio_y_normalizado():
    vacio = cliente.post(
        "/auth/registro",
        json={"nombre": "A", "apellido": "B", "correo": "  ", "password": "Clave123"},
    )
    assert vacio.status_code == 422
    ok = cliente.post(
        "/auth/registro",
        json={"nombre": "Carla", "apellido": "Diaz", "correo": "Carla.DIAZ@Mail.com",
              "password": "Clave123"},
    )
    assert ok.status_code == 200
    login = cliente.post(
        "/auth/login-json", json={"correo": "carla.diaz@mail.com", "password": "Clave123"}
    )
    assert login.status_code == 200


def test_password_excede_72_bytes():
    r = cliente.post(
        "/auth/registro",
        json={"nombre": "L", "apellido": "P", "correo": "larga@mail.com",
              "password": "a" * 73},
    )
    assert r.status_code == 422


def test_tipo_cambio_par_invalido():
    h = _headers()
    r = cliente.get("/tipo-cambio", params={"base": "EUR", "destino": "PEN"}, headers=h)
    assert r.status_code == 400


def test_tipo_cambio_en_tiempo_real():
    h = _headers()
    r = cliente.get("/tipo-cambio", params={"base": "USD", "destino": "PEN"}, headers=h)
    assert r.status_code == 200
    assert r.json()["tasa"] > 0
    assert cliente.get("/tipo-cambio").status_code == 401


def test_quitar_vehiculo_lo_oculta_del_catalogo():
    h, veh = _ids()
    creado = cliente.post(
        "/vehiculos",
        json={
            "marca": "Nissan",
            "modelo": "Versa",
            "anio": 2026,
            "precio": 72000,
            "moneda": "PEN",
        },
        headers=h,
    )
    assert creado.status_code == 201
    vehiculo_id = creado.json()["id"]
    quitado = cliente.delete(f"/vehiculos/{vehiculo_id}", headers=h)
    assert quitado.status_code == 200
    catalogo = cliente.get("/vehiculos", headers=h).json()
    assert all(item["id"] != vehiculo_id for item in catalogo)


def test_perfil_password_larga_rechazada():
    h = _headers()
    r = cliente.put("/perfil", json={"password_nueva": "a" * 73}, headers=h)
    assert r.status_code == 422


def test_perfil_cambio_de_contrasena_funciona():
    reg = cliente.post(
        "/auth/registro",
        json={"nombre": "Pa", "apellido": "Pe", "correo": "pa@mail.com", "password": "Clave123"},
    )
    assert reg.status_code == 200
    h = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    mal = cliente.put(
        "/perfil", json={"password_actual": "Incorrecta", "password_nueva": "Nueva1234"}, headers=h
    )
    assert mal.status_code == 400
    ok = cliente.put(
        "/perfil", json={"password_actual": "Clave123", "password_nueva": "Nueva1234"}, headers=h
    )
    assert ok.status_code == 200
    assert cliente.post(
        "/auth/login-json", json={"correo": "pa@mail.com", "password": "Clave123"}
    ).status_code == 401
    assert cliente.post(
        "/auth/login-json", json={"correo": "pa@mail.com", "password": "Nueva1234"}
    ).status_code == 200


def test_primera_simulacion_de_cada_usuario_es_la_numero_uno():
    reg = cliente.post(
        "/auth/registro",
        json={"nombre": "Nu", "apellido": "Evo", "correo": "nuevo@mail.com", "password": "Clave123"},
    )
    h = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    veh = cliente.get("/vehiculos", headers=h).json()
    r = cliente.post(
        "/simulaciones",
        json=_solicitud_base(_veh_pen(veh)["id"]),
        headers=h,
    )
    assert r.status_code == 201
    assert r.json()["codigo"] == "SIM-000001"


def test_recalcular_reproduce_resultado():
    h, veh = _ids()
    sim = _crear_sim(h, veh).json()
    re = cliente.post(f"/simulaciones/{sim['id']}/recalcular", headers=h).json()
    assert abs(re["cuota_mensual"] - sim["cuota_mensual"]) < 0.01
    assert abs(re["monto_prestamo"] - sim["monto_prestamo"]) < 0.01
    if sim["tcea"] is not None and re["tcea"] is not None:
        assert abs(re["tcea"] - sim["tcea"]) < 1e-6


def test_eliminar_simulacion_la_quita_del_historial():
    h, veh = _ids()
    sim = _crear_sim(h, veh).json()
    eliminado = cliente.delete(f"/simulaciones/{sim['id']}", headers=h)
    assert eliminado.status_code == 200
    historial = cliente.get("/simulaciones", headers=h).json()
    assert all(item["id"] != sim["id"] for item in historial)
    assert cliente.get(f"/simulaciones/{sim['id']}", headers=h).status_code == 404


def test_editar_cambiando_moneda_convierte_precio_conservado():
    h, veh = _ids()
    sim = _crear_sim(h, veh).json() 
    precio_pen = sim["precio_vehiculo"]
    editada = cliente.put(
        f"/simulaciones/{sim['id']}",
        json=_solicitud_base(_veh_pen(veh)["id"], moneda="USD", tipo_cambio_referencial=4.0),
        headers=h,
    ).json()
    assert editada["moneda"] == "USD"
    assert abs(editada["precio_vehiculo"] - precio_pen / 4.0) < 0.01


def test_cuota_final_mayor_que_saldo_rechazada():
    h, veh = _ids()
    r = cliente.post(
        "/simulaciones/calcular",
        json=_solicitud_base(_veh_pen(veh)["id"], porcentaje_cuota_inicial=0.99),
        headers=h,
    )
    assert r.status_code == 400
