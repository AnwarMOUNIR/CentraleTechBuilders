# Person 2 verification record

## Scope

English UI in `web/index.html` and `web/style.css`. The integration baseline has now been aligned to English. Full ordering and assistive-technology behavior are **not yet verified**. Known controller/backend gaps are recorded in `demo/integration.md`; in particular, review buttons remain disabled until the controller updates their state.

## Checks performed

| Check | Result | Evidence / limits |
| --- | --- | --- |
| Original plan's ten required IDs | Passed in browser | Each occurs exactly once. No duplicate IDs or broken label/ARIA references. |
| English document, labels, visible speech equivalents | Implemented | `lang="en"`, explicit textarea label, English button names, persistent response and status regions. |
| Keyboard and target-size support | Basic browser check passed | Activating Skip to ordering focuses the textarea. Tab then reaches Send, Speak, and Repeat in order; disabled actions are skipped. Focus outline is solid. Every button measured 48 px high. Full integrated keyboard test remains pending. |
| Responsive layout | Browser check passed at 1280 and 320 CSS px | Two columns at 1280; one at 320. No horizontal page overflow at either tested width. 200% browser zoom remains a manual check. |
| Palette contrast | Calculated | Body text 11.26:1; muted text on paper 5.92:1; muted text on response background 5.30:1; primary button text 9.51:1; status text 7.28:1; input border against white 3.55:1. This is a palette check, not a full accessibility audit. |
| Screen-reader announcements | Not tested | Must use an actual screen reader with dynamic updates after integration. Markup alone does not prove announcements. |
| English speech input/output | Not tested | Requires Person 3's adapter and actual microphone/browser. |
| API ordering and confirmation guard | Not tested | Requires Persons 1, 4, and 5. Confirm starts disabled in HTML. |
| Testing with blind users | Not conducted | Do not claim validation with blind users. |
| Repository production build | Passed | Vite 7.3.6 built the combined repository successfully. Installed the existing dependency range without changing the committed package files. This checks bundling, not completed ordering behavior. |
| Speech placeholder contract | Passed | Both adapter modules expose all four required functions, report both capabilities unavailable, and reject listening with an English text-fallback message. |

## Manual acceptance checks after integration

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
- [ ] Repeat response reads the visible text; Stop reading interrupts it.
- [ ] Microphone denied/unavailable/silent: clear status and usable text fallback.
- [ ] Model/network failure: no invented basket, no silent confirmation, text retained for retry.
- [ ] Repeated clicks while busy cannot submit duplicate requests.
- [ ] New order after confirmation/cancellation starts a fresh conversation.
- [ ] Simulated-order disclosure stays visible and is associated with the confirm control.

## Test session notes

Date: 2026-09-27
Tester: Automated UI/source inspection by Codex; no human accessibility session yet.
Browser / OS: Codex in-app browser on Windows; exact browser version not captured.
Screen reader:
Real or mock AI:
Menu fixture / expected totals:
Observed passes:
Observed failures and follow-up:
