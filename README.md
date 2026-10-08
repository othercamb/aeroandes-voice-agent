# AeroAndes Voice Agent

A voice agent built on **ElevenLabs Agents** for the Solutions Engineer take-home.

**Scenario:** a BPO in Colombia runs the phone line of AeroAndes, a fictitious regional airline, for passengers in Colombia, Mexico, Argentina, Chile and Peru. The agent detects the caller's country from the phone number prefix, answers with a voice in the local accent, and resolves the routine work: booking lookups, flight changes, baggage and pets. Fees are collected through a payment link sent by SMS, never by taking card details over the phone, and complex cases go to a human agent with full context.

The agent speaks Spanish by default (the real customer base) and switches to English when the caller speaks English, so it can be tested by non-Spanish speakers.

**Try it:** call **+1 629 288 9379**, ask for English, and use booking `K7Q2MX`, surname Rojas. **Sample conversation:** `conv_6801m4cqdpn2e459mzctrmghfy25` (English golden path, including a recovered verification failure).

> Code, tool names and the agent prompt are in Spanish on purpose: this is how the solution would be delivered to a LATAM customer whose team maintains it. Everything reviewer-facing is in English.

## Repository layout

| Folder | Contents |
|---|---|
| `api/` | FastAPI service the agent uses as tools: conversation-initiation webhook, bookings, flights, changes, baggage and a simulated payment page |
| `agent/` | Agent configuration: [prompt](agent/prompt.md), IDs, evaluation criteria and the [agent README](agent/README.md) |
| `twilio/` | Twilio Function that routes calls in front of the agent |
| `data/` | Fictitious data: `vuelos.json` (flight inventory), `reservas.json` (12 test bookings) and `generar_datos.py`, which regenerates them |
| `kb/` | Airline policies loaded into the agent's knowledge base |
| `deploy/` | `deploy.sh`: deploys to Cloud Run from Cloud Shell |
| `docs/` | [Business case](docs/business-case.md) |

## Architecture

```
Caller → Twilio number → Twilio Function (router) → ElevenLabs Agent
                                                     ├── Initiation webhook → API: country from prefix → voice, greeting, variables
                                                     ├── Knowledge base (kb/)
                                                     ├── Server tools → API (Cloud Run) → Firestore (transaction on change)
                                                     │                                  → SMS with payment link (simulated in the demo)
                                                     └── System tools: language_detection, transfer_to_number, end_call
```

Key design decisions:

- **Business rules as pure functions** (`api/app/reglas.py`): the LLM handles the conversation, but fees and eligibility are decided by deterministic, tested code. The agent cannot "invent" a policy exception.
- **Verification on every tool call:** each tool re-validates booking code and surname. There is no session to hijack, and a failure never reveals whether the booking exists.
- **Built for phone audio:** codes are dictated with support words ("K as in kilo"), read back and confirmed; the API tolerates surname noise ("Rojas." / "surname Rojas") and a single misheard code character, but only when the surname matches exactly one booking.
- **Explicit confirmation:** `cambiar-vuelo` requires `confirmacion_cliente: true`. Without it, nothing executes.
- **Consistent inventory:** the change runs inside a Firestore transaction, so two simultaneous calls cannot sell the same seat.
- **Payment outside the voice channel:** the agent never receives card data; payment happens through an SMS link.
- **Frozen "today"** (`DEMO_NOW`): the demo world lives on October 13, 2026, so the golden path behaves the same whenever someone tests it.
- **Safe SMS in the demo** (`DEMO_SMS_TO`): every SMS goes to the presenter's number, never to the fictitious phones in the bookings.
- **Measurable quality:** every call is scored by 5 evaluation criteria and 6 extracted data fields (see the [agent README](agent/README.md)).

## API

| Route | Purpose |
|---|---|
| `POST /webhooks/inicio-conversacion` | Called by ElevenLabs when a call starts. Returns voice, greeting and variables for the country of the `caller_id` |
| `POST /herramientas/consultar-reserva` | Verifies code and surname; returns the booking and whether it can be changed |
| `POST /herramientas/buscar-vuelos` | Options for a date with the total already computed by policy; if the date is full, searches ±2 days |
| `POST /herramientas/cambiar-vuelo` | Executes the confirmed change and sends the SMS with the payment link |
| `POST /herramientas/estado-equipaje` | Status of a baggage claim (reference + surname) |
| `GET/POST /pagar/{token}` | Simulated payment page (the SMS link) |
| `POST /admin/reiniciar` | Resets the data between rehearsals |
| `GET /salud` | Health check |

All tool and admin routes require the `X-Agent-Secret` header.

### Run locally

```bash
cd api
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest              # 36 tests: rules, security, golden path, off-script cases, voice-capture tolerance
DEMO_NOW=2026-10-13T10:00:00-05:00 uvicorn app.main:app --port 8080
```

Locally it uses in-memory storage and simulated SMS (written to the log).

### Deploy to GCP

From Cloud Shell, at the repo root:

```bash
bash deploy/deploy.sh
```

The script enables the APIs, creates the `aeroandes` Firestore database, a least-privilege service account and the tools secret in Secret Manager; deploys to Cloud Run (`us-east1`, one always-on instance) and seeds the data. For real SMS, export `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER` and `DEMO_SMS_TO` first.

## Test data

- **Golden path:** booking `K7Q2MX` (surname Rojas). BOG–MEX flight on October 20, Classic fare. The 21st is full; on the 22nd there are two options: morning (USD 80) or afternoon (USD 60).
- The other cases (Basic fare, airline-cancelled flight, already checked in, delayed bag, pets, multiple passengers) are described in the `nota_demo` field of each booking.

To regenerate the data:

```bash
python3 data/generar_datos.py
```

## Security

No secrets in the repository. The cloud deployment uses Secret Manager; for local development, copy `.env.example` to `.env`.
