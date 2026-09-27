# Current Integration Handoff

## Running The App

Use the setup and environment steps in the root `README.md`. `start.ps1` installs dependencies, builds the Vite frontend, and runs FastAPI at `http://127.0.0.1:8000`, which serves the built app. For development, run FastAPI on port 8000 and `npm.cmd run dev` in separate terminals; Vite proxies API and voice routes to FastAPI.

## Implemented Flow

- The browser loads `/catalog` and `/health`. A fresh order goes to `POST /recommend`, which sends the full catalog and request to local Ollama and returns a validated, server-priced review basket. Later turns send `state`, `basket`, `pending`, and `restaurant_id` to `POST /interpret`.
- Ollama extracts ordering intent locally. IDs and quantities are checked against the selected menu; `api/logic.py` owns all state transitions and pricing. The deterministic matcher is the bounded recommendation fallback if Ollama is unavailable.
- Only explicit confirmation while the basket is in review can produce `CONFIRMED`. Confirmation is checked server-side; all prices are recalculated from the selected menu.
- Restaurant changes clear the browser basket. A new request after a confirmed or cancelled order starts a fresh server-side conversation.
- Restaurant ranking maximizes requested-item coverage, then minimizes listed food subtotal. It does not have live availability, location, or delivery data. The browser can persist an explicit auto-listen preference; microphone access remains controlled by browser permission.
- A voice session captures the full request, reads the proposed list and total, and continues listening for confirmation or refusal. Browser speech is the default; cloud speech routes are disabled unless explicitly enabled with `USE_CLOUD_VOICE=true`.

## Verification

The Python test suite, production frontend build, local Ollama full-menu recommendation, and browser order/review flow are recorded in `demo/evidence.md`. That record also lists presentation-time checks that still require a person, including microphone permission, keyboard operation, and screen-reader behavior. Do not treat automated checks as a human accessibility audit.

## Boundaries

Orders are simulations only. The additional restaurant data is a sampled public snapshot, not a live menu; delivery estimates and fees are not authoritative. Displayed totals exclude delivery and other fees. English is the supported interaction language.
