# AeroAndes Voice Agent

Demo de un agente de voz construido en **ElevenLabs Agents** para el take-home de Solutions Engineer.

**Escenario:** un BPO en Colombia atiende la línea telefónica de AeroAndes, una aerolínea regional ficticia, para pasajeros de Colombia, México, Argentina, Chile y Perú. El agente detecta el país por el prefijo del número que llama, responde con una voz de acento local y resuelve lo rutinario: consultar reservas, cambiar vuelos, equipaje y mascotas. Los cargos se cobran con un enlace de pago enviado por SMS, sin pedir datos de tarjeta, y los casos complejos pasan a un asesor humano con el contexto completo.

## Estructura

| Carpeta | Contenido |
|---|---|
| `data/` | Datos ficticios: `vuelos.json` (inventario), `reservas.json` (12 reservas de prueba) y `generar_datos.py`, que los regenera |
| `kb/` | Políticas de la aerolínea que se cargan en la base de conocimiento del agente |
| `docs/` | Caso comercial y, más adelante, el diagrama de arquitectura |

Próximas carpetas: `api/` (FastAPI en Cloud Run con Firestore) y `agent/` (configuración del agente, herramientas y tests versionados).

## Arquitectura prevista

```
Llamada → Twilio → ElevenLabs Agent
                     ├── Webhook de inicio → API (Cloud Run): país → voz y saludo
                     ├── Base de conocimiento (kb/)
                     └── Herramientas → API (Cloud Run) → Firestore
                                                       → Twilio SMS (enlace de pago)
```

## Datos de prueba

- **Golden path:** reserva `K7Q2MX` (apellido Rojas). Vuelo BOG–MEX del 20 de octubre, tarifa Clásica, cambio al 22 de octubre.
- Los demás casos (tarifa Básica, vuelo cancelado, check-in hecho, maleta demorada, mascotas, varios pasajeros) están descritos en el campo `nota_demo` de cada reserva.

Para regenerar los datos:

```bash
python3 data/generar_datos.py
```

## Seguridad

Ningún secreto va al repositorio. En la nube se usa Secret Manager; para desarrollo local, copia `.env.example` a `.env`.
