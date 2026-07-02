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
uvicorn app.main:app --reload
```

- API: http://localhost:8000 - Documentacion: http://localhost:8000/docs
- La base SQLite (`autofacil.db`) y los datos de ejemplo se crean al iniciar.
  Si el codigo cambia de version, las tablas desactualizadas se recrean solas
  (las cuentas de usuario se conservan).

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
