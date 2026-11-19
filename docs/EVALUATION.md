# GlucoDiary AI — Test evidence and remaining evaluation

## Executed automated checks

- Python backend: `python -m pytest -q` — **49 passing checks** on the public synthetic sample version.
- GitHub Pages demo logic: `node --test tests/test_recruiter_demo.cjs` — **15 passing checks**.
- Syntax checks: `node --check docs/demo-core.js` and `node --check docs/demo.js` — passed.
- Backend agent orchestration calls a mocked model provider in the tests; there is **no claim of a live provider run**.
- Browser automation was attempted, but the environment returned `ERR_BLOCKED_BY_ADMINISTRATOR` for localhost, file and data URLs. Therefore actual browser click-through and iPhone compatibility are **not yet independently verified**.

## Public demo browser acceptance checklist

1. Open the deployed site in a private/incognito browser: the landing page opens **without signup or password**.
2. Read the fictional profile and see averages, chart and schedule completion.
3. Click **+ Add example reading**. Save 7.4 mmol/L in the preselected unrecorded slot; the total reading count increases by one and schedule completion changes.
4. Reload: the new example is retained in the same browser's localStorage. Check the site has not sent data to external APIs.
5. Enter a duplicate for the same date and testing occasion: a visible error prevents saving.
6. Select a different testing occasion for the chart and verify the graph and mean only use that occasion.
7. Open **Testing calendar**: 14 fictional dates, 28 planned checks, correct three-day rotating occasion, recorded/missing labels.
8. Enable **Supplement diary**, mark/unmark one fictional dose, preview a notification; **no real email or push should be sent**.
9. Enable **Food preferences**, select Indian and milk allergy, and verify paneer is excluded. The UI must not claim the filter guarantees safety.
10. Run **Agent trace**. Confirm all four stages explicitly disclose deterministic/simulated operation and use current recorded counts.
11. Click **Reset example**: original synthetic readings and optional-feature state return.
12. Repeat on desktop Chrome and iPhone Safari, including keyboard-only navigation and screen readers where feasible.

## Separate private-backend acceptance tests, not established by the public demo

- Authentication, session isolation and CSRF behavior.
- Patient-consented scheduling and reliable delivery of real email/iOS Home Screen Web Push.
- Real AI model calls under explicit consent, logged traces, and independent checks for invented facts and unsafe dosing advice.
- Database backup/recovery, rate limiting, deletion and retention, security review, and formal clinical safety validation.

**Interpretation:** The prototype demonstrates real deterministic data processing and a credible full-stack architecture. Automated checks **do not mean** the product is clinically validated or its external integrations are working in production.
