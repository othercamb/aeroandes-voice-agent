# Business case: a voice agent for the AeroAndes BPO

*Demo estimate. All figures are reasonable assumptions based on public 2026 ranges, not data from a real customer. The AI cost per call is checked against a measured demo call.*

## The customer's problem

A BPO in Colombia runs the AeroAndes phone line for passengers in five countries: Colombia, Mexico, Argentina, Chile and Peru. It faces three problems:

1. **Cost:** every change or lookup call is handled by a human, even though most are repetitive (look up a booking, change a date, ask about baggage).
2. **Peaks it cannot staff:** during disruptions (weather, airport closures), volume multiplies within hours. There is no way to hire and train agents that fast.
3. **Local experience:** a Mexican passenger served in a Colombian accent, or in robotic "neutral" Spanish, doesn't feel like their airline is taking care of them.

## Assumptions

| Assumption | Value | Basis |
|---|---|---|
| Monthly volume (5 countries) | 100,000 calls | Mid-size regional airline |
| Loaded cost of a nearshore agent (Colombia) | USD 15/hour (range 12–20) | Public nearshore BPO rates, 2026 |
| Average handle time, human (AHT) | 6 minutes | Flight-change calls with verification and hold time |
| Agent occupancy | 80% | Typical contact-center benchmark |
| AI cost per call (planning figure) | USD 0.60 | Conservative; see the measured call below |
| Containment (calls resolved without a human) | 60% | Conservative assumption for changes, lookups and baggage |

**Measured:** the golden-path demo call (`conv_1801m3sm21vsf569gwgeym933xd2`, 3 min 40 s, full verification + flight change) used 2,129 credits, **≈ USD 0.39** on the Creator plan, including voice and LLM. Adding telephony, a real call lands around USD 0.45, so the USD 0.60 planning figure leaves margin for longer calls and failed verification attempts. At enterprise volume pricing, the per-minute cost would be lower still.

## Result

| | Value |
|---|---|
| Cost per human call | **USD 1.88** (range 1.50–2.50) |
| Cost per AI call | **USD 0.60** planning (≈ 0.39–0.45 measured) |
| Current monthly cost (100% human) | USD 187,500 |
| Monthly cost with AI (60% AI, 40% human) | USD 111,000 |
| **Savings** | **USD 76,500 per month (≈ USD 918,000 per year), −41%** |

With the measured cost (≈ USD 0.45 per call including telephony), savings rise to about USD 85,500 per month (−46%).

## The strongest argument: peaks

- On a normal day about 3,300 calls come in, requiring roughly **35 agents** at once.
- On a disruption day (5× volume) about 16,700 calls would come in. That needs roughly **175 agents** simultaneously: impossible to staff within hours.
- The AI agent scales with concurrency. It serves the passengers affected by the cancellation first and keeps humans free for complex cases (refunds, compensation, complaints).

## Beyond cost

- **Local accent per country:** the agent detects the country from the phone prefix and answers with a local voice. Five "native agents" from a single agent, plus English for international travelers.
- **24/7 coverage** without night shifts.
- **Measurable quality:** every call has a transcript, automatic evaluation and extracted data (reason, outcome, amount due, transfer).
- **Compliance:** the agent never receives card data (payment by SMS link) and applies the verification policy on 100% of calls.

## How to say it in the video (about 30 seconds)

> "A Colombian BPO runs AeroAndes' phone line for five countries. Every call costs them about two dollars with a human agent, and when weather cancels flights, call volume jumps five times in a few hours, and they simply can't staff for it. This agent resolves the routine 60% — lookups, flight changes, baggage — for under 60 cents a call (we measured 39 cents on the demo call), answers in the caller's local accent, and hands the complex cases to humans with full context."

## Sensitivity (for Q&A)

- With agents at USD 12/h and 40% containment, savings drop to about USD 36,000 per month: the case still holds.
- With agents at USD 20/h and 70% containment, they rise to about USD 133,000 per month.
- The variable that matters most is **containment**, which is why every call is evaluated automatically.

## Sources for the ranges

- Nearshore BPO rates in Colombia (USD 12–20 per agent hour, loaded cost): Fusion CX, Centris, Call Force Global, 2026.
- ElevenLabs Agents pricing: public 2026 pricing pages; validated against the credits consumed by the demo call.
