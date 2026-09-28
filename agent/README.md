# Agente en ElevenLabs

| Recurso | ID |
|---|---|
| Agente "AeroAndes – Sofía (BPO LATAM)" | `agent_6301m3mc0yfne8n9fz45ama739a8` |
| Herramienta `consultar_reserva` | `tool_1201m3mb0kybee99deg2v8egcma3` |
| Herramienta `buscar_vuelos` | `tool_1601m3mb0pxkfxr89ssdhe53jmb9` |
| Herramienta `cambiar_vuelo` | `tool_2301m3mb0t2me01sts5mh2b525th` |
| Herramienta `estado_equipaje` | `tool_1601m3mb0wyzf818f8b12c0z9mq2` |
| Test de simulación "Golden path - cambio de vuelo K7Q2MX" | `test_4101m3mc6rzrfzmav8yqp4tj47jb` |

El secreto `X-Agent-Secret` vive como secreto del workspace de ElevenLabs (solo se referencia su ID) y en Secret Manager de GCP (`agent-tools-secret`).

## Configuración

- **Idioma:** español. **TTS:** `eleven_flash_v2_5` (los agentes que no están en inglés deben usar Flash o Turbo v2.5).
- **Prompt:** [`prompt.md`](prompt.md), organizado en personalidad, entorno, tono, flujo, herramientas y guardrails.
- **Variables dinámicas:** `pais`, `pais_codigo`, `trato_regional`, `telefono_cliente`. Tienen Colombia por defecto; en llamadas reales las llena el webhook de inicio.
- **Base de conocimiento:** los 6 documentos de `kb/`, en modo `auto` con RAG apagado. Son unos 12 KB y caben completos en el contexto: sin búsqueda previa y sin riesgo de que se escape un detalle.
- **Herramientas de sistema:** `end_call`. `transfer_to_number` se agrega junto con Twilio.

## Pendiente

- Webhook de inicio por país (habilitar los overrides de voz y primer mensaje).
- Voces por país agregadas a "My Voices".
- Número de Twilio y transferencia a humano.
- Criterios de evaluación y data collection.
- Tests de casos fuera del guion.
