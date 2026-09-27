# Accessible ordering: five parallel work packages

**Hackathon goal:** A blind customer orders from one small demo menu by voice or text, hears the exact basket and total, can correct it, and explicitly confirms a **simulated** order. This is an independent prototype for the Yassir everyday-impact award; it is not a Yassir integration.

**Time box:** 11 hours. Build one complete path before polishing. One shop, 6-10 menu items, one language tested well (French is a practical first choice), optional Darija phrases after that. No payments, maps, database, merchant onboarding, or real dispatch.

## Start together: freeze the contract in 20 minutes

The integration lead creates the repository and commits `shared/menu.json`, `shared/contracts.md`, and `shared/fixtures/` **before** everyone branches. Everyone agrees that item IDs and modifier IDs in the menu are authoritative. Changes to shared contracts require a short team review; other work stays in the assigned person's files.

### Proposed repository

```text
accessible-ordering/
├── README.md                       # Person 1
├── shared/
│   ├── menu.json                   # Person 1; frozen after initial agreement
│   ├── contracts.md                # Person 1; frozen after initial agreement
│   └── fixtures/                   # Person 1; example requests and responses
├── web/
│   ├── index.html                  # Person 2: semantic UI
│   ├── style.css                   # Person 2
│   ├── app.js                      # Person 1: integration/state/HTTP adapter
│   ├── speech.js                   # Person 3: STT/TTS adapter
│   └── speech.mock.js              # Person 3: deterministic fallback
├── api/
│   ├── main.py                     # Person 1: POST endpoint, wire modules
│   ├── interpreter.py              # Person 4: model adapter
│   ├── interpreter_mock.py         # Person 4: fixed responses for offline tests
│   ├── logic.py                    # Person 5: validation, basket, price, questions
│   └── privacy.py                  # Person 5: redaction, no transcript logging
├── tests/
│   ├── cases.json                  # Person 5: end-to-end scenarios
│   └── test_api.py                 # Person 5
└── demo/
    ├── script.md                   # Person 2: 90-second flow
    └── evidence.md                 # Person 2: what worked and limitations
```

Plain JS + Vite for the web app, Python FastAPI + Pydantic for the API, JSON for the menu. Use one hosted model that is **already accessible to the team** (Gemini is one option) through a server-side key. Browser `SpeechRecognition` and `speechSynthesis` cover the first voice prototype; verify them in your demo browser. No GPU or Brev is needed.

### Shared JSON contract (freeze names now)

The browser sends text, never raw audio, to `POST /interpret`:

```json
{
  "text": "Un café grand sans sucre",
  "basket": [],
  "state": "REQUEST",
  "pending": null
}
```

The API returns a full next state. It never asks the browser to calculate a price:

```json
{
  "state": "REVIEW",
  "reply_text": "Un grand café sans sucre, 18 dirhams. Confirmer, modifier ou annuler ?",
  "basket": [
    {"product_id": "coffee", "quantity": 1, "modifier_ids": ["large", "no_sugar"], "line_total_mad": 18}
  ],
  "total_mad": 18,
  "question": null,
  "pending": null,
  "error": null
}
```

Allowed states: `REQUEST`, `CLARIFY`, `REVIEW`, `CONFIRMED`, `CANCELLED`. `pending` is `null` or the unconfirmed `{product_id, quantity, modifier_ids, missing_field}` awaiting one answer; echo it on the next request. `question` and `error` are plain strings or `null`. **Only explicit `confirm` while in `REVIEW` may produce `CONFIRMED`.** Unknown products, modifiers or unclear answers yield a clarification, never a guessed order.

A minimal menu entry:

```json
{
  "id": "coffee",
  "name": "Café",
  "base_price_mad": 12,
  "modifiers": [
    {"id": "large", "label": "Grand", "delta_mad": 6},
    {"id": "no_sugar", "label": "Sans sucre", "delta_mad": 0}
  ]
}
```

`line_total_mad = quantity × (base_price_mad + modifier deltas)`, calculated by Person 5. The model may return IDs and intent but **never trusted prices**. Person 1 commits two example request/response pairs and a sample menu before the split.

## Person 1 — Integration lead and API shell

**Own only:** `README.md`, `shared/*`, `web/app.js`, `api/main.py`, dependency files. Also handle merges and submission links.

**Build independently:**

1. Create the fixed menu and fixtures; agree on the contract with everyone.
2. Make `POST /interpret` accept the contract and return a fixture response. Later connect `privacy.py → interpreter.py → logic.py`, passing `pending` through, without changing the browser contract.
3. In `web/app.js`, manage conversation states, call the API, display `reply_text`, basket and total, and call Person 3's `speak(text)` and `listen()` adapters.
4. Provide a `USE_MOCK_AI` environment switch so the whole flow still runs if model quota or keys fail.
5. Own `README.md`: exact install/run steps, required environment variables, demo limits and AI disclosure.

**Can work before other branches:** return fixture responses and import mock speech functions. **Done when:** a typed request traverses browser → API → browser and the page renders a fixture basket. **Integration gate:** all modules export the agreed names; run one real and one mock order.

## Person 2 — Accessible UI and demo experience

**Own only:** `web/index.html`, `web/style.css`, `demo/*`. Coordinate selectors/event names with Person 1; don't edit `app.js`.

**Build independently:**

1. Make one page with `#request-text`, `#send-button`, `#listen-button`, `#repeat-button`, `#response`, `#basket`, `#confirm-button`, `#change-button`, `#cancel-button`, `#status`.
2. Use real `<button>` and `<label>` elements, visible keyboard focus, readable contrast, large tap targets, and `aria-live="polite"` on response/status regions. Confirm/cancel are distinct labeled controls.
3. Show every spoken prompt as visible text. Avoid timed choices. Provide an obvious text fallback and a way to repeat the last response.
4. Write a 90-second demo script with a real ambiguity, a correction, the computed total, and explicit confirmation. Record test outcomes in `demo/evidence.md`.

**Can work before the API:** use static example text and basket markup. **Done when:** keyboard-only users can navigate all controls, and a screen reader announces a changed response. **Handoff:** stable element IDs to Person 1 by hour 2.

## Person 3 — Speech adapter

**Own only:** `web/speech.js`, `web/speech.mock.js`. Do not edit UI or backend files.

**Export exactly:**

```js
export async function listen() { /* returns transcript string; throws clear error */ }
export function speak(text) { /* returns void; cancels older speech first */ }
export function stopSpeaking() { /* returns void */ }
export function speechAvailable() { /* returns { listen: boolean, speak: boolean } */ }
```

**Build independently:** push-to-talk, one utterance at a time using `SpeechRecognition || webkitSpeechRecognition`; set a tested language. Use `speechSynthesis` for playback. Handle denied permission, missing API, silence, and repeated clicks. Mock adapter returns a predefined transcript without microphone access. Do not store recordings or claim browser STT always stays on device.

**Can work before UI:** test adapters in a minimal local HTML page; Person 1 imports the functions. **Done when:** microphone transcript appears as a string, speech can be replayed/stopped, and mock mode works. **Handoff:** export signatures and the browser/language you tested by hour 3.

## Person 4 — AI interpreter

**Own only:** `api/interpreter.py`, `api/interpreter_mock.py`, your prompt examples. No basket pricing or state transitions here.

**Function contract:**

```python
async def interpret(text: str, menu: list, basket: list, state: str, pending: dict | None) -> dict:
    # {"intent": "add|change|confirm|cancel|repeat|unknown",
    #  "product_id": "coffee" or None,
    #  "quantity": 1 or None,
    #  "modifier_ids": ["large"],
    #  "missing_field": "size" or None}
```

**Build independently:** Prompt the model with the bounded menu and current state, request structured JSON, and return only this dict. Test French utterances, an optional Darija phrase, a correction, and an unknown item. Use a server-side key from the environment. Mock interpreter returns predictable dicts for these examples. Never put model text directly into the order or accept invented prices. Let Person 5 validate all IDs and quantities.

**Can work before API:** call `interpret()` from a local script using the shared menu. **Done when:** five fixture utterances return schema-shaped data and failures return `intent="unknown"`. **Handoff:** function signature, dependency and environment variable name by hour 3.

## Person 5 — Deterministic ordering logic, privacy and tests

**Own only:** `api/logic.py`, `api/privacy.py`, `tests/*`. Don't edit interpreter or UI files.

**Function contracts:**

```python
def redact(text: str) -> str: ...
def next_step(parsed: dict, basket: list, state: str, menu: list, pending: dict | None) -> dict: ...
```

`next_step()` returns the exact API response shape shown above. Validate product and modifier IDs; reject invalid quantities; ask at most one missing-choice question; compute totals from menu JSON; support change, cancel, repeat or unclear input. Confirmation requires `state == "REVIEW"` and intent `confirm`. Redact likely phone numbers and sensitive address phrases before the model call; don't log request bodies. Keep local demo data in memory, resettable.

**Can work before model:** feed `next_step()` fixture dictionaries that imitate Person 4's output. **Done when tests cover:** valid item, missing option, unknown product, wrong modifier, quantity correction, confirm, cancel, and model failure. **Handoff:** signatures and passing tests by hour 4.

## Merge and timing checkpoints

| Time | Shared outcome | Integrator action |
|---|---|---|
| 0:00-0:20 | Freeze menu, JSON contract, exports and file ownership. | Commit shared fixtures; create five branches. |
| ~2:00 | UI skeleton + fixture browser/API flow. | Merge Person 2; check typed request end to end. |
| ~3:00 | Speech adapter and model adapter each callable alone. | Merge Person 3 and Person 4 separately, retaining mock modes. |
| ~4:00 | Logic, privacy and tests callable alone. | Merge Person 5; run the five basic scenarios. |
| ~6:00 | One complete live order. | Freeze features, fix interface mismatches. |
| ~8:00 | Keyboard/screen-reader check and failure handling. | Test on actual demo browser and microphone. |
| Final 2 hours | Record 90-second video, slides, code link and submission. | Check links from a signed-out browser and submit by the event deadline. |

**Pull request rule:** Each person changes only owned files after the shared contract freezes. Export a mock implementation even if the real component isn't ready. Every PR says how to run or test its component. The integration lead merges in the order above; nobody waits for all five components to start testing.

## Demo script and safety boundary

Say: “I want a large coffee without sugar.” The app extracts the item from the fixed menu, asks a missing question if needed, reads the itemized basket and exact price, accepts “change”, reads the revised total, then waits for an explicit “confirm”. Show the keyboard/text path too. It is a **simulated order**: no money changes hands and nothing goes to Yassir or a merchant.

Accessibility is the core value proposition. A voice interface alone is insufficient: preserve accessible controls and text equivalents. If possible, invite a blind tester with consent; otherwise clearly state that you tested with screen readers and keyboard, not that you validated the experience with blind users.

## Reference docs

- [MDN Web Speech API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Speech_API) — speech recognition and synthesis; verify browser support.
- [FastAPI request bodies](https://fastapi.tiangolo.com/tutorial/body/) — typed JSON endpoint with Pydantic.
- [Gemini structured output](https://ai.google.dev/gemini-api/docs/structured-output) — one option for a schema-shaped model response.
