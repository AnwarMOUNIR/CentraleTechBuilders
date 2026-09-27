# Judge rehearsal — 27 September 2026

The regression suite covers menu/browsing variants, mixed-restaurant baskets, offer acceptance and rejection, ambiguous confirmation, cancellation, repeat, removal, dietary uncertainty, unavailable services, invalid quantities, missing products, unrequested modifiers, negations, quantity/price combinations, redacted logging and session isolation.

Run offline regression checks:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Run 27 conversation scenarios with the real configured local Qwen model (no cloud speech calls, no real orders):

```powershell
.\.venv\Scripts\python.exe scripts/judge_rehearsal.py
```

The live rehearsal uses temporary isolated conversation storage. It follows the browser's initial recommendation plus interpretation fallback. Menu browsing and safety-critical actions are deterministic; open-ended interpretation still uses Qwen. A passing rehearsal does not mean every utterance is routed through the model.

Fixed during rehearsal: empty catalog claims for natural menu questions; repeated yes loops; single-restaurant omission of requested items; invented size/spice; unsupported dish qualifiers silently substituted; ignored unknown clauses; duplicate internal search messages in memory; quantity reset during option changes; lost receipt on repeat; SQLite connection leak.

Restaurant selection uses lowest listed food prices for recognized items; delivery fees and live availability are not known. Mixed requests can span multiple restaurants and are read back by restaurant. Unknown or ambiguous requests may deliberately ask for clarification rather than modify the basket.

Before judging, test with the actual microphone and speaker arrangement, including background noise, accents, permission denial, silence, and Escape/stop. Automated text rehearsals do not validate speech recognition accuracy, audio playback, screen-reader behavior, or every possible natural-language request. All orders remain simulated.

Category recovery regression: “one hot drink, one cold drink, and something with fish” now produces a three-item proposal requiring acceptance before adding. Hot/cold suggestions currently use coffee/orange juice; these are explicit demo defaults, not unrestricted semantic category understanding. Repeat and unclear replies preserve the whole proposal. Decline before selecting alternatives. Contextual “heart rate”/“heartbreak” asks for clearer speech rather than silently changing the transcript. No raw model inquiry prose is read aloud; the application renders a clarification template. Added speech vocabulary hints do not guarantee transcription accuracy. The suite passed 202 tests after these changes.
