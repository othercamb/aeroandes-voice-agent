# ElevenLabs agent

| Resource | ID |
|---|---|
| Agent "AeroAndes – Sofía (BPO LATAM)" | `agent_6301m3mc0yfne8n9fz45ama739a8` |
| Tool `consultar_reserva` (booking lookup + verification) | `tool_1201m3mb0kybee99deg2v8egcma3` |
| Tool `buscar_vuelos` (flight search with priced options) | `tool_1601m3mb0pxkfxr89ssdhe53jmb9` |
| Tool `cambiar_vuelo` (execute confirmed change) | `tool_2301m3mb0t2me01sts5mh2b525th` |
| Tool `estado_equipaje` (baggage claim status) | `tool_1601m3mb0wyzf818f8b12c0z9mq2` |
| Simulation test "Golden path - cambio de vuelo K7Q2MX" (real API) | `test_4101m3mc6rzrfzmav8yqp4tj47jb` |
| Simulation test "Procedure - confirma y ejecuta" (tools mocked) | `test_0901m4cv1ej6ech88xz02avm6err` |
| Simulation test "Procedure - pasajera no confirma" (tools mocked) | `test_2001m4cv1td7fzx909n7m9jd9rzb` |
| Structured procedure "Confirmar y ejecutar cambio de vuelo" | `agtprc_2501m4crph1aet08x852eb4dhqjp` |

The `X-Agent-Secret` secret lives as an ElevenLabs workspace secret (referenced only by ID) and in GCP Secret Manager (`agent-tools-secret`).

## Configuration

- **Language:** Spanish by default, English via the `language_detection` system tool. The `en` language preset switches the voice to Jessica and uses an English greeting. **TTS:** `eleven_flash_v2_5` (multilingual, lowest latency).
- **LLM:** `qwen35-397b-a17b`, temperature 0.
- **Prompt:** [`prompt.md`](prompt.md), structured as personality, environment, tone, language, call flow, tools and guardrails.
- **Dynamic variables:** `pais`, `pais_codigo`, `trato_regional`, `telefono_cliente`. They default to Colombia; on real calls the initiation webhook fills them in.
- **Knowledge base:** the 6 documents in `kb/`, in `auto` mode with RAG off. They are about 12 KB and fit entirely in context: no retrieval step and no risk of missing a detail.
- **System tools:** `end_call`, `language_detection` and `transfer_to_number` (conference transfer to the BPO's human agent; in the demo, a Colombian mobile). The agent transfers only after the passenger accepts.
- **Speech recognition:** `patient` turn eagerness and ASR keywords with the demo CRM surnames and "AeroAndes". In production, the initiation webhook could send the surnames linked to the caller's phone as keywords.
- **Voices:** one per country, all from the Voice Library (Creator plan, added to My Voices): Luna (CO, default), Regina (MX), Melisa (AR, with *voseo*), Catalina (CL), Lily (PE). English: Jessica.
- **Initiation webhook:** `POST /webhooks/inicio-conversacion` with the `X-Agent-Secret` header. On every inbound Twilio call, ElevenLabs sends the `caller_id`; the API returns the country's voice, greeting and variables. Overrides enabled on the agent: `tts.voice_id`, `agent.first_message` and `agent.language`; any other override is ignored.

## Structured procedure: confirm and execute the change

The one irreversible step, charging the passenger and moving the seat, runs as a **structured procedure** instead of free prompt text. It starts once the passenger picks one of the options from `buscar_vuelos`:

1. **Ask** — read back flight, day, time and total, and ask for confirmation (the only step that waits for the caller).
2. **Branch** — *explicit yes* → `cambiar_vuelo` with `confirmacion_cliente` forced to `true` as a **constant** (the LLM cannot set it), then confirm and mention the payment link; on tool failure, apologise and offer a human. *Anything else* → no change, say so.

Three layers protect the write: the step order (the tool only exists inside the "yes" branch), the constant parameter, and the API's own check. The prompt delegates this step to the procedure and forbids calling `cambiar_vuelo` directly.

What we learned building it:
- While the prompt also described "read back, confirm, call the tool", the LLM never started the procedure: it had no reason to. Switching the LLM to Gemini did not help (and was ~3× slower on first token), so we kept `qwen35`; the fix was removing that responsibility from the prompt.
- The first working version said "processing" twice and produced garbled output after the procedure ended. Both were found by reading transcripts of runs that the test marked as passed; fixed by dropping the redundant "tell" step and ending the procedure without a question.
- Webhook-tool overrides in procedures need the `request_body.` prefix; ElevenLabs validation reports the exact step path on publish.
- The two procedure tests mock the three booking tools, so they are repeatable without resetting data; the original golden-path test still hits the real API.
- A phone test of the merged procedure (`conv_2901m4e1h27ke74tzbdf6xy491dr`, 3 min 2 s, all 5 criteria passed) confirmed it fires by voice, but showed ~6 s of silence after `consultar_reserva`: the LLM did not always say the "one moment" line before the tool. `pre_tool_speech` is now set to `force` on that tool, so the platform always speaks before the lookup.

> The initiation webhook only fires on phone calls (Twilio or SIP). The widget and text tests use the Colombian defaults.

## Phone number (Twilio)

- Demo number: **+1 629 288 9379** (US local). Imported into ElevenLabs and assigned to the agent.
- SMS is disabled on the Twilio account (A2P 10DLC registration pending), so the API sends the payment link in simulated mode and the payment page is shown directly in the demo.

### Router in front of the agent

The number points to the Twilio Function [`/router`](../twilio/router.js) (service `forward-call`). Calls from the presenter's notification platform (<notification platform number>) are forwarded to a mobile; everything else goes to ElevenLabs (`https://api.us.elevenlabs.io/twilio/inbound_call`). A `<Redirect>` keeps `From`, `To` and `CallSid`, so country detection still works. The ElevenLabs status callback (`https://api.us.elevenlabs.io/twilio/status-callback`) is unchanged. If the number is re-imported into ElevenLabs, "A call comes in" must be pointed back to `/router`.

### Restoring the number after the process

Before the demo, the number forwarded calls to a mobile through a Twilio Function. To go back: delete the number in ElevenLabs (Phone Numbers) and, in Twilio → number → Voice Configuration → "A call comes in", choose **Function** → service `forward-call` (SID `<service SID>`), path `/forward-call` (`<forward-call Function URL>`).

## Automatic evaluation of every call

When each conversation ends, ElevenLabs analyzes it with an LLM and scores it. This lets the BPO measure quality on 100% of calls instead of a sample.

| Criterion | What it checks |
|---|---|
| `verified_before_disclosure` | No booking data before `verificado=true`, and never confirms a booking exists when verification fails |
| `explicit_confirmation` | Reads back flight, day, time and total, and waits for an explicit yes before `cambiar_vuelo` |
| `no_invented_information` | Prices, schedules and rules come from tools or policy; no exceptions |
| `resolved_or_escalated` | Resolves the need, or offers a transfer when the case belongs to a human |
| `voice_style` | Short turns, one question at a time, no lists or technical identifiers |

Data extracted per call (filterable in the call history): `call_reason`, `booking_code`, `verification_passed`, `outcome`, `amount_due_usd`, `transferred_to_human`. The country comes from the `pais_codigo` dynamic variable.

## Reference conversation (golden path by phone)

`conv_1801m3sm21vsf569gwgeym933xd2` (Sep 30, 2026, in Spanish): a real call from Colombia through Twilio → router → ElevenLabs. Verification (code dictated with support words + confirmed surname) → the 21st is full → alternatives on the 22nd → AN103 for USD 60 → explicit confirmation → change + payment link → close with `end_call`. 3 min 40 s, 2,129 credits (≈ USD 0.39). Tool latency: 0.4–0.5 s. Agent response time: 0.8–2.5 s.

`conv_8701m3t4vdgse5cv6e14bjh1aq5b` (Sep 30, 2026, in English): the caller asks for English right after the Spanish greeting → `language_detection` switches language and voice → same golden path, morning option AN101 for USD 80 → explicit confirmation → change + payment link. 4 min 24 s, 2,547 credits. All 5 evaluation criteria passed, but a transcript review found a numbered list, Spanish spelling words in English ("M as in mama") and a flight date called "today". The prompt and the `voice_style` criterion were tightened afterwards: the automatic evaluation is only as good as its criteria, so they are reviewed against real transcripts.

### Sample conversation for reviewers (English)

**`conv_6801m4cqdpn2e459mzctrmghfy25`** (Oct 7, 2026), after the prompt fixes. Spanish greeting → caller asks for English → `language_detection` → code dictated and read back in the NATO alphabet → the surname is first captured as "Soto", verification fails without revealing whether the booking exists, and the agent keeps the confirmed code and asks only for the surname spelled out ("Romeo, Oscar, Juliet, Alpha, Sierra") → verified → the 21st is full → two options on the 22nd in a single sentence → AN101 for USD 80 → explicit confirmation → change + payment link (with the 2-hour auto-reversal from the policy KB) → `end_call`. 4 min 11 s, 2,452 credits. All 5 criteria passed under the stricter `voice_style`; tool latency 0.3–0.5 s.

## Next steps

- Off-script tests (Basic fare, airline cancellation, already checked in, caller asks for a human).
