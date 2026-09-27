# 90-Second English Demo

## Before You Start

Start Ollama and confirm the configured model is installed with `ollama list`. Run `start.ps1` and open <http://127.0.0.1:8000>. Run `scripts/check_services.py` once before presenting. Use Chrome or Edge on localhost and allow microphone access. Browser speech recognition may use the browser's speech service. Keep the text field available as a fallback.

## Run Of Show

| Time | Presenter and user action | Expected result |
| --- | --- | --- |
| 0-10 s | Introduce ClearOrder as a listening-first English ordering demo. | Show the restaurant menu selector and simulated-order notice. |
| 10-25 s | Press Start listening and say: “I want two big coffees with no sugar, and a croissant.” | Ollama receives the full catalog; the app stages the best matching menu and prices every item from that menu. |
| 25-40 s | Listen to the proposed restaurant, item list, and total. | The same list and total appear on screen. The assistant explicitly says the order is not confirmed. |
| 40-55 s | Say “No, cancel.” | The proposal is discarded and the voice session ends; no order is placed. |
| 55-72 s | Start listening again and repeat the order. Say “Confirm order” after hearing the read-back. | Only the explicit confirmation produces `CONFIRMED`; the assistant repeats that this is simulated. |
| 72-90 s | Show the text fallback and the basket. | Leave the final state visible. |

The local model receives every sample restaurant menu and proposes item IDs. The API checks those IDs and computes the total; no model-provided price is trusted. Live opening status, availability, and delivery charges are not part of the recommendation. For typed orders, use Ctrl+Enter or Send message.

## Fallbacks And Claims

- If microphone permission or recognition fails, continue with text and explain the issue plainly.
- If speech synthesis fails, use the visible assistant response.
- If Ollama is unavailable, set `USE_MOCK_AI=true` and identify the demo as using offline rules.
- Disable automatic speech when testing with a screen reader to avoid overlapping audio.
- Describe only the accessibility checks recorded in `evidence.md`. No blind-user validation is claimed.
