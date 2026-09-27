# ClearOrder

## Current integration status

The live path now defaults to a model-led search → structured draft → separate Qwen verification flow (`api/order_agent.py`). This integration is **work in progress**: the first verified proposal has been exercised, but full multi-turn acceptance of the new architecture is not yet complete. Verification by the same model is a second check, not an independent guarantee. Server-side price, item-ID, and explicit-confirmation checks still apply.

`USE_MOCK_AI=true` selects offline behavior. With live AI, `USE_VERIFIED_AI=false` temporarily selects the older interpreter. Existing offline regression tests explicitly select that older path; passing them does not certify the new live agent. `tests/test_verified_agent.py` checks the new pipeline's server safety boundaries. Earlier rehearsal results below and in `demo/` describe the previous engine unless stated otherwise. Local credentials and conversation databases are excluded from Git.

An accessible English voice-and-text ordering demo. Start listening, describe your full order, and the local Ollama model selects items from all sample restaurant menus. ClearOrder validates and reprices the proposed basket, reads it back, and waits for explicit confirmation or refusal. Orders are **simulated**; the app is not connected to a merchant, payment, delivery, or dispatch service.

## Run on Windows

Requirements: Python 3.11 or newer, Node.js 20 or newer, and Ollama running locally with the configured model installed. From the project folder, run:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
.\start.ps1
```

The sample configuration uses `qwen3:4b`. If needed, run `ollama pull qwen3:4b` first. The startup script installs dependencies, builds the frontend, and warms the model with `OLLAMA_KEEP_ALIVE=-1` so it remains loaded. Open <http://127.0.0.1:8000> in Chrome or Edge. If PowerShell blocks the script, run `powershell -ExecutionPolicy Bypass -File .\start.ps1`. For offline rule-based ordering, set `USE_MOCK_AI=true` in `.env`. To release GPU memory after the demo, run `ollama stop qwen3:4b`.

The API docs are at <http://127.0.0.1:8000/docs>. Stop the server with Ctrl+C.

## AI And Voice

The local Ollama model handles interpretation and restaurant selection. With `USE_CLOUD_VOICE=true` and keys configured, Deepgram transcribes audio and ElevenLabs speaks replies. Faster-Whisper (CPU, `base.en`, downloaded on first use) and browser speech provide fallbacks. The microphone loop is half-duplex: it listens after each spoken response finishes, not while the assistant is speaking.

Press **Start listening**, say your full request, then review the spoken and visible items and total. Say “confirm order” to confirm the simulated order, or “no, cancel” to discard it. To avoid pressing Start listening on later visits, opt in to **Start listening automatically on future visits** once. The browser still controls microphone permission and may require a user gesture. Say “stop listening” or press Escape to stop.

| Variable | Default | Purpose |
|---|---|---|
| `USE_MOCK_AI` | `false` | Use offline deterministic interpretation instead of Ollama. |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Local Ollama server URL. |
| `OLLAMA_MODEL` | `qwen3:4b` | Installed local chat model for interpretation and menu selection. |
| `OLLAMA_KEEP_ALIVE` | `-1` | Keep the model loaded until Ollama stops or unloads it. |
| `WHISPER_MODEL` | `base.en` | Local English speech-recognition model; downloaded from Hugging Face on first use. |
| `USE_CLOUD_VOICE` | `true` | Enable cloud speech when credentials exist. Set false for local-only speech. |
| `DEEPGRAM_API_KEY` | unset | Optional recognition credential, used only when cloud voice is enabled. |
| `ELEVENLABS_API_KEY` | unset | Optional synthesis credential, used only when cloud voice is enabled. |
| `ELEVENLABS_VOICE_ID` | `JBFqnCBsd6RMkjVDRZzb` | Optional ElevenLabs voice selection. |

## Development And Checks

For a Vite development server with API hot reload, install dependencies once, then run the API and web app in separate PowerShell terminals:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
npm.cmd ci
.\.venv\Scripts\python.exe -m uvicorn api.main:app --reload --port 8000
```

In the second terminal:

```powershell
npm.cmd run dev
```

Open the Vite URL it prints. Run the checks with:

```powershell
.\.venv\Scripts\python.exe -m pytest
npm.cmd run build
.\.venv\Scripts\python.exe scripts/check_services.py
```

The service diagnostic checks the configured local Ollama model. `demo/script.md` has a short demo flow; `demo/evidence.md` records completed checks and remaining manual acceptance work.

## Data And Limits

- Every order is simulated. No order, payment, or delivery is sent anywhere.
- The default demo menu uses fixed MAD prices. Other menus and delivery details are sample snapshots; totals exclude delivery and other fees.
- SQLite FTS5 and parameterized LIKE fallback retrieve at most 24 catalog candidates, plus current basket items. Qwen receives that subset, current basket/pending state, and the last six logged events. Qwen never supplies executable SQL. Catalog tables are seeded from the JSON source on first search in each process; edit the source and restart to update them. This is bounded retrieval, not a production-scale database benchmark.
- Recommendations use sample prices only; live availability, distance, delivery fees, and service quality are not ranked.
- Debug transcripts, generated replies, playback requests and basket snapshots are stored locally in ignored `data/catalog.db`. Phone/address patterns are redacted, but this is not comprehensive anonymization: avoid sensitive input. Old events are pruned after seven days when a new event is written. Audio is not saved by this app; configured cloud/browser providers may process it under their own policies.
- The supported interaction language is English. Automated checks do not replace testing with a microphone and screen reader in the presentation setup.

## Debugging conversations

Open <http://127.0.0.1:8000/conversations> to find recent conversation IDs, then `/conversations/ID` for up to 500 events with timestamps. Each page load starts a fresh ID. Playback events indicate requested speech, not proof the user heard it. SQLite and logs are excluded from Git. `ORDER_DB_PATH` can override the local database path. These unauthenticated debugging endpoints are for localhost only; do not expose this demo publicly.

Quick acceptance test: say “one fish pastilla”, then “make that two”, then “I like it but I am still deciding”. The basket should remain two pastillas at 110 MAD, unconfirmed. Only “confirm order” should confirm it. Also test switching restaurants with an existing basket and saying “repeat”.

