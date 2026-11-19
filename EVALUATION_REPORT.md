# GlucoDiary AI — Verification Report

**Tested:** 19 November 2026  
**Scope:** publicly shareable, no-login synthetic-data recruiter website and accompanying Python prototype.  
**Verdict:** Local functional tests passed; **not** a fully verified clinical or hosted multi-agent application.

## Results from actual test runs

| Method | Result | Scope |
| --- | --- | --- |
| Python `pytest -q` | **49 passed** | API, auth, schedules, storage, orchestration, notification logic with mocks |
| Node.js `node --test` | **20 passed** | Public source, schedule, deterministic calculations, duplicate/date validation, recipe exclusions, reset and sample-time consistency |
| Chromium DOM end-to-end interactions | **10 scenarios passed** | Opening and rendering, numerical analysis, save/reject/delete, filtering, sample supplements, food filters, simulated trace, persistence in emulated Web Storage, reset, empty-state handling and responsive sizing |
| JavaScript syntax (`node --check`) | **Passed** | `demo.js`, `demo-core.js` |
| Standalone single-file HTML | **Passed** | Real Chromium rendered inline code, opened interactive forms, saved a sample reading, verified no JavaScript errors and responsive chart at 390px width |
| Real publicly hosted website | **Not tested** | No GitHub deployment access / deployed URL |
| Physical iPhone Safari / emails / push | **Not tested** | No device or connected delivery service available |
| Live LLM-agent calls | **Not tested** | No API key/consent/external provider was configured |
| Clinical correctness and safety | **Not established** | This is an educational fictional-data prototype |

### Verified browser examples

1. Initial fictional dataset: **23 recorded values**, **28 planned tasks**, **23/28** completion, overall mean approximately **7.34 mmol/L** (descriptive only).
2. Clicking **Add example reading** picks a missing before-sleep slot on **7 October 2026 at 22:00**, prefilled as 7.4 mmol/L; saving increases recorded count to **24** and matched planned tasks to **24/28**.
3. Adding that same date and testing occasion again returns a duplicate error without changing the count.
4. Graph filtering uses only its selected measurement occasion.
5. Supplement tracker is off by default; enabling it reveals four fictional dates and reminder **preview only**.
6. Meal ideas are off by default. Milk and peanut selections exclude illustrative paneer and peanut dishes; ingredient exclusion and cuisine selections adjust the list.
7. Four-step simulated agent trace uses the updated **24-reading** count and explicitly states **no live LLM call**.
8. Browser-local state survives reconstruction of the page with the same Web Storage contents; reset restores the original fictional profile.
9. At 390px width the glucose SVG, completion ring and dashboard stay within the viewport.
10. Deleting every reading produces an empty chart and missing average **without a crash**; reset restores all original fictional readings.

**Browser test method:** Chromium was run headlessly. This environment denies navigation to `http://127.0.0.1`, `file://` and `data:` pages (`ERR_BLOCKED_BY_ADMINISTRATOR`), so the exact bundled HTML and assets were loaded into a blank Chromium document through Playwright's `set_content` and script injection, with Web Storage emulated for persistence. Real, separate HTTP deployment and iPhone tests are still required.

## Bugs discovered and fixed

- The sample prefill sometimes used a morning clock time for a bedtime example. Fixed sample times by testing occasion.
- Dates such as 30 February or outside the fictional calendar were accepted by the core date logic despite being invalid or non-persistent. Fixed strict calendar and period validation.
- Resetting the sample dataset left previous chart/reminder UI settings visible. Reset now restores the chart selection and hides reminder preview.
- On a 390px mobile viewport, the SVG graph and completion ring could be clipped by min-content sizing. Fixed mobile grid tracks and fluid SVG sizing; verified the chart bounding box stays within viewport.
- Added regression tests for these issues.

## Limitations / not verified

- GitHub Pages hosts a **static** version. The real Python backend and its orchestration do **not** run on GitHub Pages.
- Public 'agents' are a deterministic **illustrative trace**, not independently running AI agents.
- Email reminders and iPhone push shown in the demo are preview text, not delivered notifications.
- Browser-local demo storage is not authenticated, durable medical data storage; it belongs only to the current visitor's browser.
- Recipe matching is simplified and cannot establish allergen safety; it does not cover all relevant allergens or cross-contact.
- No independent clinician review, real-user study, accessibility audit, full security penetration test, health-data privacy audit, MHRA assessment or device-end-to-end evaluation has been completed.

## Manual hosted-site release checks

After publishing, open the actual GitHub Pages URL in a clean browser, add a fictional reading, refresh it, select a chart filter, toggle food and supplement options, run the simulated trace, reset the demo, and repeat on an iPhone. Record URLs, browser version, screenshots, dates and outcomes. **Do not claim an iPhone/email/live-AI pass until those services are separately tested.**
