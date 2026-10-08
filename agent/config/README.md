# Agent configuration export

A snapshot of the ElevenLabs agent, exported through the API so the configuration can be reviewed without access to the workspace. It is documentation, not the source of truth: the live agent is `agent_6301m3mc0yfne8n9fz45ama739a8`.

| File | Contents |
|---|---|
| `agent.json` | Full agent: prompt, LLM, voices and language presets, built-in tools, knowledge base, evaluation criteria, data collection, initiation webhook, turn-taking |
| `tools/*.json` | The four webhook tools (schemas, descriptions, pre-tool speech, timeouts) |
| `procedures/*.json` | The structured procedure "Confirmar y ejecutar cambio de vuelo" and its closing sub-procedure |
| `tests/*.json` | Simulation tests: golden path, the two procedure tests (tools mocked) and six off-script cases |

Redacted: workspace secret IDs, the human-transfer phone number and account metadata. The `X-Agent-Secret` header on every tool is a reference to a workspace secret, not the value.
