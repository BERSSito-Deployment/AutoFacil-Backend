# AutoFacil - Backend (FastAPI)

API para simular el credito de un auto con el producto Compra Inteligente:
cuotas mensuales fijas (metodo frances) mas una cuota final que se paga al
terminar el credito.

## Puesta en marcha

```cmd
cd AutoFacil-Backend-main
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
docker compose up -d postgres
uvicorn app.main:app --reload
```

- API: http://localhost:8000 - Documentacion: http://localhost:8000/docs
- La configuracion de ejemplo usa PostgreSQL local en `localhost:5432`.
- Las tablas y los datos de ejemplo se crean al iniciar el servicio.
- Para usar SQLite local en lugar de PostgreSQL, cambie
  `AUTOFACIL_URL_BASE_DATOS` en `.env` por `sqlite:///./autofacil.db`.

## PostgreSQL

El archivo `docker-compose.yml` levanta una base PostgreSQL de desarrollo con:

| Campo | Valor |
|-------|-------|
| Host | localhost |
| Puerto | 5432 |
| Base de datos | autofacil |
| Usuario | autofacil |
| Contrasena | autofacil_dev |

La cadena usada por la aplicacion es:

```env
AUTOFACIL_URL_BASE_DATOS=postgresql+psycopg://autofacil:autofacil_dev@localhost:5432/autofacil
```

No suba su archivo `.env` real a un repositorio publico. Use `.env.example`
solo como plantilla.

## Deploy con PostgreSQL externa

Para desplegar, configure estas variables en la plataforma de hosting:

```env
AUTOFACIL_CLAVE_SECRETA=una-clave-larga-y-aleatoria
AUTOFACIL_URL_BASE_DATOS=postgresql+psycopg://USUARIO:CONTRASENA@HOST:5432/NOMBRE_DB
AUTOFACIL_SEMBRAR_DATOS_INICIO=false
AUTOFACIL_ORIGENES_CORS=["https://url-del-frontend.com"]
```

Si la plataforma entrega `DATABASE_URL`, tambien sirve. La app acepta URLs como
`postgres://...` o `postgresql://...` y las adapta al driver instalado.

Comando de inicio sugerido:

```cmd
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

En produccion mantenga:

```env
AUTOFACIL_SEMBRAR_DATOS_INICIO=false
```

asi no se crean usuarios demo en la base publica. No suba archivos `.env`
reales al repositorio.

## Cuentas de prueba

| Usuario | Contrasena |
|---------|------------|
| demo    | Demo1234   |
| maria   | Maria1234  |

## Como funciona

- Cada persona crea su cuenta (JWT + contrasena cifrada) y solo ve sus propios
  vehiculos y simulaciones.
- Planes: Plan 24 (24 cuotas, cuota final sugerida 50% del precio), Plan 36
  (36 cuotas, sugerida 40%) o personalizado (meses a eleccion). La cuota final
  siempre se puede editar.
- Tasa fija: efectiva (TEA) o nominal (TNA) con capitalizacion diaria,
  quincenal, mensual, bimestral, trimestral, cuatrimestral, semestral o anual.
- Anio de 360 dias (ordinario) o 365 (natural) para las conversiones de tasas.
- Meses de gracia al inicio: total (no se paga y el interes se acumula) o
  parcial (se paga solo el interes).
- Costos iniciales financiados o al contado; costos por cuota (GPS, portes,
  gastos administrativos); seguros de desgravamen y todo riesgo.
- Resultados: cronograma completo, cuota mensual, TEA/TEM, VAN, TIR y TCEA
  (el costo real anual del credito). Todo se calcula con precision decimal y
  solo se redondea al mostrar.

## Pruebas

```cmd
venv\Scripts\activate
pytest
```

Incluye un caso maestro que reproduce al centimo el modelo Excel del producto.
