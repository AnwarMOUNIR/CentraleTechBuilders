# Frozen integration contract

Version: `1.0` — changes require review by the integration lead and affected file owner.

## HTTP endpoint

`POST /interpret` accepts JSON:

```json
{
  "text": "Un café grand sans sucre",
  "basket": [],
  "state": "REQUEST",
  "pending": null
}
```

- `text`: non-empty string containing typed text or a browser-generated transcript.
- `basket`: zero or more basket lines in the response shape below.
- `state`: one of `REQUEST`, `CLARIFY`, `REVIEW`, `CONFIRMED`, `CANCELLED`.
- `pending`: `null` or an unconfirmed object with `product_id`, `quantity`, `modifier_ids`, and `missing_field`.

The response is always a complete next state:

```json
{
  "state": "REVIEW",
  "reply_text": "Un grand café sans sucre, 18 dirhams. Confirmer, modifier ou annuler ?",
  "basket": [
    {
      "product_id": "coffee",
      "quantity": 1,
      "modifier_ids": ["large", "no_sugar"],
      "line_total_mad": 18
    }
  ],
  "total_mad": 18,
  "question": null,
  "pending": null,
  "error": null
}
```

`question` and `error` are strings or `null`. Money fields are integer Moroccan dirhams for this menu. The API, never the browser or model, calculates prices.

## Safety invariants

1. Only an explicit `confirm` intent received while the current state is `REVIEW` can produce `CONFIRMED`.
2. Unknown products, modifiers, invalid quantities, or unclear answers produce `CLARIFY`; they are never guessed into the basket.
3. `product_id` and `modifier_ids` must exist in `shared/menu.json`.
4. `line_total_mad = quantity × (base_price_mad + modifier deltas)`.
5. Raw audio is never sent to this endpoint. Request bodies and transcript text must not be logged.

## Python module boundaries

```python
async def interpret(text: str, menu: list, basket: list, state: str, pending: dict | None) -> dict: ...
def redact(text: str) -> str: ...
def next_step(parsed: dict, basket: list, state: str, menu: list, pending: dict | None) -> dict: ...
```

The interpreter returns only `intent`, `product_id`, `quantity`, `modifier_ids`, and `missing_field`. Allowed intents are `add`, `change`, `confirm`, `cancel`, `repeat`, and `unknown`.

## Browser speech exports

```js
export async function listen() {}
export function speak(text) {}
export function stopSpeaking() {}
export function speechAvailable() {}
```

`speechAvailable()` returns `{ listen: boolean, speak: boolean }`. The stable UI element IDs are listed in the team plan and consumed by `web/app.js`.

