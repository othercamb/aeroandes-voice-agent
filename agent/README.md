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
- **Reconocimiento de voz:** turno `patient` y *keywords* de ASR con los apellidos del CRM de la demo y "AeroAndes". En producción, el webhook de inicio podría enviar como keywords los apellidos asociados al teléfono de quien llama.
- **Voz por defecto:** Luna (CO). Las 5 voces por país son de la Voice Library (plan Creator) y están en My Voices.
- **Webhook de inicio:** `POST /webhooks/inicio-conversacion` con el header `X-Agent-Secret` (mismo secreto de las herramientas). Con cada llamada entrante de Twilio, ElevenLabs envía `caller_id`; la API responde la voz, el saludo y las variables del país. Overrides habilitados en el agente: `tts.voice_id`, `agent.first_message` y `agent.language`; cualquier otro override se ignora.

> El webhook de inicio solo se dispara en llamadas telefónicas (Twilio o SIP). En el widget o en las pruebas de texto se usan los valores por defecto de Colombia.

## Número de teléfono (Twilio)

- Número de la demo: **+1 629 288 9379** (local, Nashville). Importado en ElevenLabs y asignado al agente.
- SMS deshabilitados en Twilio (falta registro A2P 10DLC): la API envía el enlace de pago en modo simulado.

### Enrutador delante del agente

El número apunta a la Twilio Function [`/router`](../twilio/router.js) (servicio `forward-call`). Las llamadas de la
plataforma de notificaciones (<notification platform number>) se desvían al celular; el resto va a ElevenLabs
(`https://api.us.elevenlabs.io/twilio/inbound_call`). El *status callback* de ElevenLabs
(`https://api.us.elevenlabs.io/twilio/status-callback`) se deja igual. Si el número se reimporta en ElevenLabs,
hay que volver a apuntar "A call comes in" a `/router`.

### Restaurar el número después del proceso

Antes de la demo, el número redirigía las llamadas a un celular con una Twilio Function. Para volver a ese estado:
eliminar el número en ElevenLabs (Phone Numbers) y, en Twilio → número → Voice Configuration → "A call comes in",
elegir **Function** → servicio `forward-call` (SID `<service SID>`), path `/forward-call`
(`<forward-call Function URL>`).

## Conversación de referencia (golden path por teléfono)

`conv_1801m3sm21vsf569gwgeym933xd2` (30-sep-2026): llamada real desde Colombia por Twilio → enrutador → ElevenLabs.
Verificación (código dictado con palabras de apoyo + apellido confirmado) → 21-oct lleno → alternativas del 22 →
AN103 por USD 60 → confirmación explícita → cambio + enlace de pago → cierre con `end_call`.
3 min 40 s, 2.129 créditos (≈ USD 0,39). Herramientas: 0,4–0,5 s. Respuesta del agente: 0,8–2,5 s.

## Pendiente

- Número de Twilio y transferencia a humano.
- Criterios de evaluación y data collection.
- Tests de casos fuera del guion.
