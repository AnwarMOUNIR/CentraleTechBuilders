# 90-second English demonstration

## Before presenting

Run the integrated app in the team's chosen browser. Verify English speech and microphone permission. Use the authoritative shared menu and real API-computed prices. Keep the typed fallback ready. Clearly disclose mock mode if using it.

The original plan gives an illustrative coffee price: 12 MAD base + 6 MAD large = 18 MAD each. Use 18 / 36 MAD below **only if that is the committed menu**. Otherwise use the returned totals. Confirm with Person 5 which ambiguous phrase reliably triggers `CLARIFY`; do not claim coffee size is required unless the committed menu/logic makes it required. “I’d like a drink” is a candidate if the demo menu contains multiple drinks.

## Run of show

| Time | Presenter and user action | Expected visible/spoken result |
| --- | --- | --- |
| 0–10 s | “ClearOrder helps someone order using English speech or text. This is a simulated café order.” | Show the text input, speech control, and simulation label. |
| 10–25 s | Choose Speak your order. Say the team's tested ambiguous phrase, such as “I’d like a drink.” Review the transcript and choose Send message. | The assistant asks one relevant clarification. It does not guess an item or confirm anything. |
| 25–40 s | Reply: “One large coffee without sugar.” Send the reply. | Basket shows the resolved item and modifiers; the assistant reads the exact server total. For the illustrative menu: 18 MAD. |
| 40–55 s | Use Tab to reach Change order and activate it. Type “Make that two large coffees without sugar.” Send. | Quantity updates to two; the exact revised total appears and is read. For the illustrative menu: 36 MAD. |
| 55–68 s | Activate Repeat response, then Stop reading if needed. | Same visible summary is read again; playback can be stopped. No order is submitted by these controls. |
| 68–83 s | Tab to Confirm simulated order and press Enter. | Only this explicit action produces `CONFIRMED`. The assistant says the simulated order is confirmed. |
| 83–90 s | “Every spoken prompt is also text. You can correct your order and take your time. There is no payment or delivery.” | Leave the final itemized basket and confirmation visible. |

## Fallbacks

- If the microphone fails, type the same phrases and explain that the text path remains available.
- If synthesis is unavailable, show the visible responses and disclose the limitation.
- If the hosted model is unavailable, use Person 1's configured mock mode and label the demonstration accordingly.
- If screen-reader speech overlaps with synthesis, turn off automatic synthesis and use the screen reader; test explicit playback separately.
- Only describe accessibility tests actually recorded in `evidence.md`. Do not claim testing with blind users unless it happened with consent.
