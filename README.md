# Accessible Ordering

Hackathon prototype for an accessible, voice-or-text ordering flow. A customer chooses from one fixed demo menu, reviews the exact basket and total, can correct it, and must explicitly confirm a **simulated** order.

This is an independent prototype. It does not connect to Yassir, a merchant, payments, delivery, or dispatch.

## What works in the integration baseline

- `POST /interpret` accepts the frozen request contract.
- Mock mode returns deterministic responses without an AI key.
- The browser integration manages the conversation state and renders the API's basket and total.
- Speech and ordering modules can be merged later without changing the public contract.

## Project structure

```text
shared/       Frozen menu, contract, and integration fixtures
web/          Browser UI and integration code
api/          FastAPI shell and later interpreter/logic modules
tests/        Ordering tests owned by the logic contributor
demo/         Demo script and evidence owned by the UI contributor
```

File ownership and the team plan are documented in `accessible_ordering_team_plan.md`. Changes to `shared/` require a short team review after the initial contract commit.

## Run the API

Prerequisites: Python 3.11 or newer.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:USE_MOCK_AI = "true"
python -m uvicorn api.main:app --reload --port 8000
```

The API is available at `http://localhost:8000`; its interactive documentation is at `http://localhost:8000/docs`.

## Run the web app

In another terminal, with Node.js 20 or newer:

```powershell
npm install
npm run dev
```

Open the local address printed by Vite. Vite forwards `/interpret` and `/health` to the API on port 8000.

Until the UI contributor adds `web/index.html`, the API can be checked at `/docs` or with the examples in `shared/fixtures/`.

## Environment variables

| Name | Default | Purpose |
|---|---|---|
| `USE_MOCK_AI` | `true` | Uses deterministic offline behavior. Set to `false` only after the real interpreter and logic modules are integrated. |
| `MODEL_API_KEY` | unset | Placeholder name; the interpreter contributor must document the final server-side key name before integration. Never expose it to browser code. |

## Integration checks

```powershell
python -m pytest
```

Before the demo, run one full order with `USE_MOCK_AI=true` and one with the real model. Also verify the text-only path, keyboard navigation, screen-reader announcements, denied microphone permission, and explicit confirmation.

## Privacy, AI, and demo limits

- The browser sends transcript text, not raw audio, to the API.
- Do not log request bodies or retain transcripts.
- Model output is treated as untrusted: deterministic code validates IDs and quantities and calculates every price from `shared/menu.json`.
- Browser speech recognition may use a browser/vendor service; do not claim it always runs locally.
- The demo supports one shop and a small fixed English menu. English is the only supported interaction language for the hackathon build.
- Every order is simulated. No payment is taken and no real order is placed.

