# Integration verification record

## Scope

English UI and integrated ordering flow. Automated tests and provider checks pass; keyboard, microphone, and assistive-technology acceptance still needs a person using the presentation setup.

## Checks performed

| Check | Result | Evidence / limits |
| --- | --- | --- |
| Python regression suite | Passed: 50 tests | Ran with the project's `.venv`; one upstream Starlette deprecation warning was reported. |
| Restaurant recommendation | Passed | Coffee plus croissant selected one venue covering both for 22 MAD; orange juice selected the lowest listed price (13 MAD); unsupported large/no-sugar options did not match a menu that lacks them. |
| Ollama full-catalog order | Passed in browser | Installed local Qwen model received all restaurant menus and returned two large coffees without sugar plus a croissant, priced by the API at 46 MAD. The response explicitly stayed in `REVIEW` and said it was not confirmed. |
| Ollama service diagnostic | Passed | Local runtime 0.32.15; full-catalog request returned two validated items and 46 MAD. |
| Listening-session review | Passed with mock speech input | One session captured a full multi-item order, read back the visible summary, and stayed in review until the next utterance. “No, cancel” discarded it; a second run followed by “Confirm order” produced `CONFIRMED`. Mock mode bypasses physical microphone and audible-speech testing. |
| Browser read-aloud control | Passed in browser | Typed menu response started browser speech; Stop reading became enabled, stopped playback, and returned to disabled. Actual audio output still needs a person to verify on presentation hardware. |
| Order refusal | Passed | “No, cancel” and other negative-confirmation variants clear a review basket and produce `CANCELLED`; nothing is placed. |
| Automatic listen preference | Passed in mock speech | Opt-in started a session, persisted in browser storage, and auto-started again after reload. Mock mode avoided microphone capture; real permission and browser gesture behavior remain manual checks. |
| Integrated browser order | Passed | In the built app with offline rules: one large coffee without sugar was 18 MAD; “make that two coffees” preserved both modifiers and returned 36 MAD; explicit confirmation produced `CONFIRMED` and the simulated-order disclosure. |
| Stop-reading control | Passed in browser | Stop became available during audio playback, cancelled the in-flight speech request, returned to disabled, and left the reviewed basket unchanged. A live microphone session still needs manual verification. |
| Local interpreter failure | Passed | An unavailable Ollama endpoint returns a safe unknown intent; menu recommendation falls back to bounded local matching. |
| Original plan's ten required IDs | Passed in browser | Each occurs exactly once. No duplicate IDs or broken label/ARIA references. |
| English document, labels, visible speech equivalents | Implemented | `lang="en"`, explicit textarea label, English button names, persistent response and status regions. |
| Keyboard and target-size support | Basic browser check passed | Activating Skip to ordering focuses the textarea. Tab then reaches Send, Speak, and Repeat in order; disabled actions are skipped. Focus outline is solid. Every button measured 48 px high. Full integrated keyboard test remains pending. |
| Responsive layout | Browser check passed at 1280 and 320 CSS px | Two columns at 1280; one at 320. No horizontal page overflow at either tested width. 200% browser zoom remains a manual check. |
| Palette contrast | Calculated | Body text 11.26:1; muted text on paper 5.92:1; muted text on response background 5.30:1; primary button text 9.51:1; status text 7.28:1; input border against white 3.55:1. This is a palette check, not a full accessibility audit. |
| Screen-reader announcements | Not tested | Requires an actual screen reader. Markup alone does not prove announcements. |
| Real microphone and audible speech | Not tested with a person | Mock recognition exercised the full loop. Permission and browser recognition quality still need testing on the presentation device; automated playback-state checks do not prove a human heard speech. |
| API ordering and confirmation guard | Passed | Covered by the regression suite and local-model browser review flow. |
| Testing with blind users | Not conducted | Do not claim validation with blind users. |
| Repository production build | Passed | `npm.cmd run build`; Vite 7.3.6 produced the current frontend bundle. |

## Manual Acceptance Checks

Record browser/version, OS, screen reader/version, date, tester, and pass/fail details. A pass requires observing the behavior, not just inspecting markup.

- [ ] Keyboard: first Tab exposes Skip to ordering; activate it and verify textarea focus.
- [ ] Keyboard: all available buttons are reachable with Tab/Shift+Tab and activate with Enter/Space. No traps or unexpected submissions.
- [ ] Focus remains visible at desktop and narrow widths and after server responses.
- [ ] At 200% zoom and a 320 CSS px viewport, controls and text remain usable without horizontal page scrolling.
- [ ] Screen reader announces the textarea label/help and meaningful button names.
- [ ] Updated assistant replies and operational status are announced once without focus being stolen.
- [ ] Basket names/modifiers/quantities and total are readable in the correct order.
- [ ] Clarification asks one question; the answer preserves API `pending` state.
- [ ] Correction updates quantity and API-calculated total before confirmation.
- [ ] Confirm works only after review and never from a mic click, Repeat response, or an ambiguous reply.
- [ ] Cancel clears or preserves the basket exactly as the API specifies and announces cancellation.
- [ ] Repeat response reads the visible text; Stop reading interrupts it without ending the voice session.
- [ ] Microphone denied/unavailable/silent: clear status and usable text fallback.
- [ ] Model/network failure: no invented basket, no silent confirmation, text retained for retry.
- [ ] Repeated clicks while busy cannot submit duplicate requests.
- [ ] New order after confirmation/cancellation starts a fresh conversation.
- [ ] Simulated-order disclosure stays visible and is associated with the confirm control.

## Test session notes

Date: 2026-09-27
Tester: Automated workspace/browser checks; no human accessibility session yet.
Browser / OS: Integrated browser on Windows; exact browser version not captured.
Screen reader: Not tested.
Real or mock AI: Local Ollama model for menu selection; deterministic pricing and offline fallback.
Menu fixture / expected totals: Two large no-sugar coffees plus croissant, 46 MAD.
Observed passes: 50 tests; production build; live local-model full-catalog basket at 46 MAD; listening-loop cancel and confirm; saved mock auto-start check.
Remaining: Manual acceptance checks above.
