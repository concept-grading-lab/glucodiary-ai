# GlucoDiary AI — Tested No-Login Recruiter Demo

**Public demo: interactive, no sign-in, entirely fictional glucose values. Not for clinical use.**

This project demonstrates how a clinician-defined glucose testing calendar, manual meter readings, descriptive trend analysis and optional supplement/food tools could be combined with explainable agent workflows. The public workflow is a transparent **simulation**, not live LLM agents.

## Easiest: run with just one file

Download **`index.html`**. It is a complete, self-contained website with its CSS and JavaScript embedded. Double-click it to open in Chrome. No ZIP, Python or other downloads are required just to explore the demo. Some browsers restrict persistent storage for local files; hosted GitHub Pages allows the normal browser-local persistence functionality.

## Publish on GitHub Pages (no backend needed)

1. Create a public GitHub repository named `glucodiary-ai` at https://github.com/new.
2. On its repository homepage, use **Add file → Upload files**.
3. Upload the downloaded **`index.html`** (exact filename, no other file required). Optionally add `README.md`, `EVALUATION_REPORT.md`, `ARCHITECTURE.md` and source files for recruiters to inspect.
4. Commit the files to `main`.
5. Open **Settings → Pages → Build and deployment → Deploy from a branch → main → /(root) → Save**.
6. When Pages reports that deployment succeeded, use **Visit site**. A typical URL is `https://YOUR-USERNAME.github.io/glucodiary-ai/`.
7. Test the hosted URL from a private/incognito window and from a phone.

The public site is **static**: it does not use the separate Python API. The same JavaScript calculations are also provided as individual `demo-core.js`, `demo.js` and `demo.css` files to facilitate code review. `index.html` already embeds them and does not fetch them.

## What you can demonstrate

- View a fictional 14-day monitoring period (28 scheduled checks, rotating additional testing occasions).
- Directly enter and delete sample glucose readings and see the mean, chart and completed-test statistics update.
- Select a meal/bedtime context; observe relevant data only.
- Enable the optional fictional supplement tracker and preview, but **do not send**, a reminder.
- Enable food suggestions, try cuisine and allergen filters (illustrative only, not allergy-safe advice).
- Run a deterministic four-step evidence and simulated agent trace using the currently recorded fictional data.
- Refresh for browser-local retention; reset all fictional entries.

## Testing

See `EVALUATION_REPORT.md` for exact coverage and limitations. At final local verification (19 November 2026): **49 Python tests, 20 JavaScript tests, and 10 interactive Chromium DOM scenarios passed**. The test runner accessed the exact HTML/CSS/JS through browser DOM injection because this environment blocks browser URL navigation. This is **not equivalent to verifying a deployed GitHub Pages URL** or physical iPhone Safari.

Reproduce from the full source structure with Python, Node.js and optionally Chromium/Playwright:

```shell
python -m pip install -r requirements.txt
python -m pytest -q
node --test tests/test_recruiter_demo.cjs
node --check docs/demo-core.js
node --check docs/demo.js
# Optional graphical Chromium interaction test:
python -m pip install playwright
python -m playwright install chromium
python tests/test_browser_e2e.py
```

To use the individual modular source code instead of the bundled HTML, the originals are in `docs/index.html`, `docs/demo.css`, `docs/demo-core.js` and `docs/demo.js`.

## Safety, privacy and truth in portfolio claims

Never enter actual health data on the public demo. The website has no real login, hosted database, live AI-provider API calls, real email notification service or iPhone Web Push integration. The optional recipes do not provide medically validated nutrition or allergy safety advice. A protected patient app and real notifications would require separate hosting, credentials, consent, clinical-safety assessment and end-to-end device verification. The `app/` Python source is included as a **separate protected-backend prototype**, not executed by GitHub Pages.

Official GitHub Pages instructions: https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site
