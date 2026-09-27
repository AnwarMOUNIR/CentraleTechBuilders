# Person 2 handoff — English accessible UI

## Files and preview

Merge `web/index.html`, `web/style.css`, and `demo/`. There are no external fonts, images, UI libraries, or new package dependencies. Person 1 still owns `web/app.js`; this HTML loads it with `<script type="module" src="./app.js"></script>`. Serve `web/` as the Vite root, or open `/web/` if the existing Vite root is the repository root. Do not add a second app script or duplicate listeners.

Opening `web/index.html` directly is a **layout preview only**. Run the repository's Vite and API commands for integration. Existing `web/app.js`, `api/main.py`, menu, fixtures, and contracts have been preserved. Missing interpreter, privacy, logic, and test modules are empty placeholders; `tests/cases.json` is an empty array. Missing speech adapters export the four agreed names and report speech unavailable so importing them cannot break the controller. They do not implement real speech or a mock transcript.

## Observed integration gaps in baseline `23db49e`

These are open integration tasks for Person 1, not behavior provided by the HTML/CSS:

- `app.js` never enables Confirm/Change/Cancel; apply the state table below. The HTML starts them disabled deliberately, so a complete order cannot yet be confirmed through this page.
- `app.js` appends a total row inside `basket` instead of updating `total`; update the dedicated total element and remove the duplicate total row.
- `app.js` uses French status/command strings and `api/main.py` recognizes French coffee phrases and returns French replies. English orders are not yet supported end to end. Translate the controller and coordinate English fixtures/backend responses with Persons 4 and 5.
- The baseline submits on every Enter inside the textarea, auto-submits microphone transcripts, and does not guard concurrent requests. Align it with the event and request guidance below.
- Stop reading is not bound, speech availability does not disable Repeat, and basket labels are raw IDs. Wire the extra controls and resolve labels from the shared menu.
- Clarification, change, cancellation, and quantity-correction behavior still require the ordering implementation. The 90-second script is a target acceptance flow, not a verified capability of the current baseline.

The user selected **English**. The original planning document still contains French examples. Persons 1, 3, 4, and 5 should use English menu labels, recognition, synthesis, interpretation fixtures, questions, and replies. Product/modifier IDs and MAD currency do not change. Person 3 should set an English locale (for example `en-US`) in both speech recognition and synthesis.

## DOM contract for Person 1

All ten IDs required by the original plan are present exactly once. All buttons use `type="button"`; there is no form submission or inline event handler. Attach one `click` listener per action in `app.js`. Enter inside the textarea inserts a newline; users Tab to Send message and press Enter or Space to send.

| ID | Element | Integration behavior |
| --- | --- | --- |
| `request-text` | `textarea` | Read/write `.value`. Used for new requests, clarification answers, and corrections. Reject empty/whitespace-only text locally. |
| `send-button` | `button` | Send the current text with the latest `basket`, `state`, and `pending`. |
| `listen-button` | `button` | Call `stopSpeaking()` before `listen()`. Put the resulting transcript in the textarea. Announce “Transcript ready. Review it, then choose Send message.” Let the user review before submitting. |
| `repeat-button` | `button` | Call `speak()` with the current visible response text; do not submit another order. |
| `response` | `p`, polite live region | Replace `.textContent` with the API's English `reply_text`. It must contain every prompt that is spoken. Keep the element itself mounted. |
| `basket` | `ul` | Replace its children with `li` elements representing the returned basket. Remove the initial `.empty-basket` item when rendering an order. Restore an empty message for an empty basket. |
| `confirm-button` | `button`, initially disabled | Send text `confirm` through the same API flow only in `REVIEW`. Never confirm locally or automatically. |
| `change-button` | `button`, initially disabled | Send text `change`, apply the API response, then focus `request-text` so the user can specify the correction. |
| `cancel-button` | `button`, initially disabled | Send text `cancel`; apply the API response. |
| `status` | `p`, polite status region | Short operational messages: loading, listening, microphone denied, retry, order confirmed/cancelled. Avoid repeating the assistant's full reply here. |

Additional hooks:

| ID | Purpose |
| --- | --- |
| `total` | Set `.textContent` from **API `total_mad`**, formatted in MAD. Initial text: `0.00 MAD`. |
| `stop-speaking-button` | Initially disabled. Bind `stopSpeaking()` from Person 3. Enable when speech synthesis is available. It is an extra UI hook, not a change to the speech/API contracts. |
| `confirmation-hint` | Optional state-specific explanation of why confirmation is disabled or available. |
| `ordering-app` | Optional `.dataset.state` mirror of the returned state. No CSS or business logic relies on it. |

Names/modifiers must resolve through `shared/menu.json`; render strings using `textContent`, not unsanitized HTML. Do not show raw model markup, invent menu entries, trust model prices, or calculate totals in the browser. The page deliberately does not hardcode a menu that could drift from the shared file.

Optional basket classes supported by the stylesheet:

```html
<li class="basket-item">
  <span class="item-name">1 × Coffee</span>
  <span class="item-details">Large · No sugar</span>
  <span class="item-price">18.00 MAD</span>
</li>
```

This is a display example only. Plain `li` elements also work. Use `Intl.NumberFormat("en-US", { style: "currency", currency: "MAD" })` for formatting server amounts.

## State, requests, and focus

Initialize local state to `REQUEST`, `basket` to `[]`, and `pending` to `null`. For every successful response, apply the full returned state, basket, pending, total, and reply together. Echo `pending` unchanged in the next request. Treat `question`/`error` as visible English text if the backend does not already include them in `reply_text`; any spoken question must also appear in `response`.

| State | Confirm | Change | Cancel |
| --- | --- | --- | --- |
| `REQUEST` | Disabled | Disabled unless a basket exists | Enabled if a basket or pending item exists |
| `CLARIFY` | Disabled | Enabled if a basket exists | Enabled |
| `REVIEW` | Enabled only for a nonempty basket and no pending clarification/error | Enabled | Enabled |
| `CONFIRMED` | Disabled | Disabled | Disabled |
| `CANCELLED` | Disabled | Disabled | Disabled |

The API must enforce confirmation too. While an order request is in flight, prevent a second submission, disable Send/Listen/Confirm/Change/Cancel, and announce progress in `status`. Restore controls from the latest state afterward; do not blindly enable everything in a `finally` block. On a failed request, preserve the last basket and the user's text, show a retry message, and keep confirmation disabled until the user obtains a fresh successful review.

After `CONFIRMED` or `CANCELLED`, keep the final response visible. The next new typed/spoken order should begin a fresh `REQUEST` with an empty basket and `pending: null`; reset this explicitly in Person 1's controller, or agree on a backend restart convention with Person 5. Do not reuse a confirmed basket accidentally.

Use `speechAvailable()` to disable unavailable speech controls and explain that typing remains available. Denied microphone permission, silence, or a rejected `listen()` promise must leave typing usable. Guard repeated microphone clicks. Keep Stop reading usable during playback; Repeat response should use the speech adapter's cancel-before-speak behavior.

Preserve keyboard focus during ordinary updates. For a clarification or Change action, focus the textarea after updating the visible question. If a focused action becomes disabled after confirmation/cancellation, move focus to the textarea. Update existing live-region text rather than replacing the regions. Basket/total are not extra live regions: include the exact itemized summary and total in `reply_text` to avoid duplicate screen-reader announcements.

For screen-reader tests, disable automatic speech playback so browser speech and the screen reader do not talk over one another; keep explicit Repeat response available. Automatic speech is optional for other demos. Validate this behavior with the actual demo browser and screen reader.

## Merge gate

1. Connect the required selectors, plus `total` and `stop-speaking-button`.
2. Verify a typed order against the shared fixture, including API-supplied prices.
3. Run clarification → correction → review → explicit confirmation in English.
4. Run cancel, network failure, unsupported speech, and denied-microphone cases.
5. Complete and record the manual checks in `demo/evidence.md` before claiming end-to-end accessibility.
