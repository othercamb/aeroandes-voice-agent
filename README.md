# AeroAndes Voice Agent

Demo de un agente de voz construido en **ElevenLabs Agents** para el take-home de Solutions Engineer.

**Escenario:** un BPO en Colombia atiende la línea telefónica de AeroAndes, una aerolínea regional ficticia, para pasajeros de Colombia, México, Argentina, Chile y Perú. El agente detecta el país por el prefijo del número que llama, responde con una voz de acento local y resuelve lo rutinario: consultar reservas, cambiar vuelos, equipaje y mascotas. Los cargos se cobran con un enlace de pago enviado por SMS, sin pedir datos de tarjeta, y los casos complejos pasan a un asesor humano con el contexto completo.

## Estructura

| Carpeta | Contenido |
|---|---|
| `api/` | API en FastAPI que el agente usa como herramientas: webhook de inicio, reservas, vuelos, cambios, equipaje y pago simulado |
| `data/` | Datos ficticios: `vuelos.json` (inventario), `reservas.json` (12 reservas de prueba) y `generar_datos.py`, que los regenera |
| `kb/` | Políticas de la aerolínea que se cargan en la base de conocimiento del agente |
| `deploy/` | `deploy.sh`: despliegue a Cloud Run desde Cloud Shell |
| `docs/` | Caso comercial y, más adelante, el diagrama de arquitectura |

Próxima carpeta: `agent/`, con la configuración del agente, las herramientas y los tests versionados.

## Arquitectura

```
Llamada → Twilio → ElevenLabs Agent
                     ├── Webhook de inicio → API: país por prefijo → voz, saludo y variables
                     ├── Base de conocimiento (kb/)
                     └── Herramientas → API (Cloud Run) → Firestore (transacción en el cambio)
                                                       → Twilio SMS → página de pago simulado
```

Decisiones principales:

- **Reglas de negocio como funciones puras** (`api/app/reglas.py`): el LLM conversa, pero el cálculo de cargos y la elegibilidad los decide código determinístico y probado. El agente no puede "inventar" una excepción a la política.
- **Verificación en cada herramienta:** cada llamada vuelve a validar código de reserva y apellido. No hay sesión que se pueda secuestrar, y un fallo nunca revela si la reserva existe.
- **Confirmación explícita:** `cambiar-vuelo` exige `confirmacion_cliente: true`. Si no llega, no ejecuta.
- **Cupos consistentes:** el cambio corre en una transacción de Firestore, para que dos llamadas simultáneas no vendan el mismo asiento.
- **Pago fuera de la voz:** el agente nunca recibe datos de tarjeta; el cobro llega por un enlace en un SMS.
- **"Hoy" congelado** (`DEMO_NOW`): el mundo de la demo vive el 13 de octubre de 2026, así el golden path funciona igual cuando alguien lo pruebe después.
- **SMS seguros en la demo** (`DEMO_SMS_TO`): todos los SMS van al número de quien presenta; nunca se escribe a los teléfonos ficticios de las reservas.

## API

| Ruta | Uso |
|---|---|
| `POST /webhooks/inicio-conversacion` | ElevenLabs la llama al iniciar la conversación. Devuelve voz, saludo y variables según el país del `caller_id` |
| `POST /herramientas/consultar-reserva` | Verifica código y apellido; devuelve la reserva y si se puede cambiar |
| `POST /herramientas/buscar-vuelos` | Opciones para una fecha, con el total calculado según la política; si no hay, busca ±2 días |
| `POST /herramientas/cambiar-vuelo` | Ejecuta el cambio confirmado y envía el SMS con el enlace de pago |
| `POST /herramientas/estado-equipaje` | Estado de un reclamo de maleta (referencia + apellido) |
| `GET/POST /pagar/{token}` | Página de pago simulado (el enlace del SMS) |
| `POST /admin/reiniciar` | Vuelve los datos al estado inicial entre ensayos |
| `GET /salud` | Prueba de vida |

Todas las rutas de herramientas y administración exigen el header `X-Agent-Secret`.

### Correr en local

```bash
cd api
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest              # 23 tests: reglas, seguridad, golden path y casos fuera del guion
DEMO_NOW=2026-10-13T10:00:00-05:00 uvicorn app.main:app --port 8080
```

En local usa almacenamiento en memoria y SMS simulados (se escriben en el log).

### Desplegar en GCP

Desde Cloud Shell, en la raíz del repo:

```bash
bash deploy/deploy.sh
```

El script habilita las APIs, crea la base Firestore `aeroandes`, una cuenta de servicio con permisos mínimos y el secreto de las herramientas en Secret Manager; despliega en Cloud Run (`us-east1`, una instancia siempre activa) y siembra los datos. Para SMS reales, exporta antes `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER` y `DEMO_SMS_TO`.

## Datos de prueba

- **Golden path:** reserva `K7Q2MX` (apellido Rojas). Vuelo BOG–MEX del 20 de octubre, tarifa Clásica. El 21 está lleno; el 22 hay dos opciones: mañana (USD 80) o tarde (USD 60).
- Los demás casos (tarifa Básica, vuelo cancelado, check-in hecho, maleta demorada, mascotas, varios pasajeros) están descritos en el campo `nota_demo` de cada reserva.

Para regenerar los datos:

```bash
python3 data/generar_datos.py
```

## Seguridad

Ningún secreto va al repositorio. En la nube se usa Secret Manager; para desarrollo local, copia `.env.example` a `.env`.
