# Optional: deploy the **protected Python backend** to HTTPS (not required for recruiters)

This is a **hands-on guide**, not a claim that a website has already been deployed. For the **no-login recruiter demonstration**, follow [GitHub Pages setup](GITHUB_PAGES_SETUP.md) instead; the protected backend is a different deployment. A real project deployment involves confidential API keys and health data; never paste them into a public repository or this chat.

## Overview of services

| Component | Suggested provider | Charge | Critical caveat |
|---|---|---|---|
| Source code / scheduled dispatcher | GitHub / GitHub Actions | Public repo/limited Actions usually free | Scheduled Actions can be delayed or disabled after inactivity |
| Python web app / HTTPS | Render free web service | Free tier | Sleeps after inactivity and needs waking; no persistent disk |
| Database | Neon free PostgreSQL | Free tier limits | Requires external database URL; monitor allowance/expiry |
| Email to own inbox | Resend HTTPS API | Free limited testing possible | Without verified sender domain, can only send to your own Resend-account email |
| iPhone notification | Native Web Push / VAPID | No Apple Developer Program required | HTTPS, iOS 16.4+, installed Home Screen PWA, user grants permission |
| AI agents | OpenAI API | **Not necessarily free** | Own API key, explicit patient consent, possible charges |

**Free-tier hosting is not appropriate for reliable time-critical healthcare reminders.** Always retain your clinician's normal monitoring instructions and a backup alarm/calendar reminder.

## A. Put only the *public source* on GitHub

1. Download and extract the **PUBLIC SOURCE ZIP**, not the private local account package.
2. Create an empty GitHub repository such as `glucodiary-ai` (public if you want recruiters to see the code). If you want to store medical records, do NOT store them in GitHub.
3. Open PowerShell in extracted directory and run:

```powershell
git init
git add .
git commit -m "Initial GlucoDiary AI full-stack prototype"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/YOUR-REPOSITORY.git
git push -u origin main
```

Replace `YOUR-USERNAME/YOUR-REPOSITORY` with your real information. Confirm that `.env`, SQLite files, VAPID private keys and patient records do not appear in the commit (`git status` and the GitHub Files tab).

## B. Make a free persistent database (Neon)

1. Sign in to <https://console.neon.tech/> and create a free Postgres project.
2. Copy the *connection string* from its dashboard. It should resemble `postgresql://USER:PASSWORD@HOST/DBNAME?sslmode=require`; keep it secret.
3. Set this connection string as `DATABASE_URL` in Render. The app automatically converts it to SQLAlchemy's `postgresql+psycopg://` driver URL.
4. Do **not** use the bundled SQLite database on Render. Render free service disk is ephemeral and data would disappear on restarts/redeploys.

## C. Create the hosted site (Render)

1. At <https://dashboard.render.com/>, choose **New → Web Service** and connect the GitHub repository.
2. Python runtime; plan **Free**; build command `pip install -r requirements.txt` and start command `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Alternatively use the supplied `render.yaml` blueprint.
3. Configure environment variables in Render **Environment**, not GitHub code:

| Key | Value |
|---|---|
| `DATABASE_URL` | Your secret Neon connection string |
| `COOKIE_SECURE` | `true` |
| `ALLOW_SIGNUP` | `false` for your protected account |
| `BOOTSTRAP_TOKEN` | Generate and securely store a random long token for first-time setup |
| `REMINDER_RUNNER_SECRET` | Another independent random long token for GitHub Actions |
| `RESEND_API_KEY` | Resend secret (when ready) |
| `RESEND_FROM` | `GlucoDiary <onboarding@resend.dev>` only for self-testing; otherwise your verified domain |
| `OPENAI_API_KEY` | Your own API key (when ready; **may incur fees**) |
| `VAPID_PUBLIC_KEY` | Generated public push key |
| `VAPID_PRIVATE_KEY` | Generated private push key, escaped with `\\n`, kept secret |
| `VAPID_SUBJECT` | `mailto:your-email@example.com` |

Generate random setup and runner tokens locally with Python: `python -c "import secrets; print(secrets.token_urlsafe(48))"`. Generate two distinct tokens.
4. Deploy and open the actual `https://...onrender.com/` URL shown in your Render dashboard (the hostname is provided by Render, not by this guide).
5. Under **Initial private setup**, enter the `BOOTSTRAP_TOKEN`, your login email, and a **new password that you have not shared**. Your first private account and a fictional 28-slot sample schedule will be created in PostgreSQL. After confirming sign-in, remove or rotate the setup token in Render.
6. If you plan to support other patients, `ALLOW_SIGNUP=true` enables basic self-registration, but this version lacks email verification and clinical compliance and is NOT ready for a public patient service.

## D. Actual email delivery

**Use Resend HTTP API on Render Free.** Render Free **blocks outbound SMTP ports 25, 465 and 587**, so ordinary Gmail SMTP/app-password connections will not work on that free host.

1. Register at <https://resend.com/> using the SAME email address to which you want to send test notifications.
2. Create an API key and save it as `RESEND_API_KEY` in Render.
3. For protected testing, the default `onboarding@resend.dev` sender may send only to the email address registered in Resend. To serve other recipients, verify a domain and change `RESEND_FROM`.
4. In GlucoDiary → Reminders & settings, choose your *own* time values, enable email, explicitly confirm the schedule and save.
5. Click **Send a test notification** and confirm that a new email actually arrives in your inbox. Checking only an HTTP 200 response is insufficient.
6. Scheduled emails also require the separate runner below; the app itself does not continuously run on a sleeping Free host.

Do not configure your protected Gmail password as the SMTP password. If using SMTP on another host, a separate Google app password may be available when 2-Step Verification is enabled.

## E. iPhone Home Screen notifications

1. From the project directory, generate the VAPID keypair once: `python scripts/generate_vapid_keys.py`. Copy the PUBLIC and PRIVATE values into Render environment secrets. Never commit the private key.
2. Redeploy the site after setting VAPID keys.
3. On iPhone running iOS 16.4+, visit the HTTPS site in Safari. Use **Share → Add to Home Screen**, then **open the installed Home Screen app**.
4. Sign in. In Reminders & settings, tap **Connect iPhone / browser push**, then tap **Allow** when iOS asks for notification permission.
5. Tick **Send iPhone / browser push reminders** and **I confirm**; save the times. Tap **Send a test notification** and verify an iOS notification actually arrives on your phone.
6. iOS focus settings, permission changes, network failures and hosting delays can prevent delivery. Do not rely on a PWA as a medical alarm.

## F. Schedule the backend dispatcher using GitHub Actions

The public repository includes `.github/workflows/reminders.yml` as a **manual-only** integration test: no scheduled checks run automatically. After deploying a private backend and confirming secrets, an independent reliable scheduler may be configured separately.

In GitHub → Repository → Settings → Secrets and variables → Actions → New repository secret, add:
- `GLUCODIARY_SERVICE_URL` = the exact HTTPS Render URL from your dashboard (no trailing slash required)
- `GLUCODIARY_RUNNER_TOKEN` = the same secret you set in Render as `REMINDER_RUNNER_SECRET`

Navigate to **Actions → Scheduled reminder check → Run workflow** to test the endpoint. Scheduled Actions can be late, throttled, disabled after repository inactivity or delayed by Render's cold start. The dispatcher will ignore reminders more than 90 minutes old, and it checks previously delivered items to reduce duplicates. A reliable production job/queue with transactional claiming is not included.

## G. Activate AI analysis (optional)

1. Get your own API key through <https://platform.openai.com/> and check the current price and data processing terms. **API usage is separate from ChatGPT subscription access.**
2. Add `OPENAI_API_KEY` to Render environment. Redeploy.
3. Enter at least two glucose readings, visit AI insights, read the data sharing consent, enable the checkbox and press **Run AI agents**.
4. Check the human-readable result and the four-step trace. The pipeline performs evidence preparation plus three distinct model calls (pattern, explanation, safety review). A disallowed suggestion is held; numbers remain available independently.
5. Explicitly disable AI sharing when no longer wanted. Removing the key makes the app fall back to ordinary deterministic charts (it does NOT pretend a model has run).

## H. Final acceptance checklist

- Account login works; after refresh, saved reading still exists.
- A different test user cannot access this user's records.
- 28 fictional monitoring tasks and four fictional supplement entries appear.
- Reminder times are user-selected, and only consented channels enable.
- Real test email arrives at the expected account.
- Real test notification appears on the installed iPhone PWA.
- GitHub Actions manual reminder workflow succeeds; inspect its run log.
- Real model key configured; agent trace shows distinct steps and a passed/held review.
- All automated tests pass on GitHub Actions.

## Authoritative references

- Apple: <https://webkit.org/blog/13878/web-push-for-web-apps-on-ios-and-ipados/>
- Render Free restrictions: <https://render.com/docs/free>
- Render SMTP port block: <https://render.com/changelog/free-web-services-will-no-longer-allow-outbound-traffic-to-smtp-ports>
- Neon pricing & limits: <https://neon.com/pricing>
- GitHub scheduled workflow limitations: <https://docs.github.com/en/actions/reference/events-that-trigger-workflows#schedule>
- Google app passwords: <https://support.google.com/accounts/answer/185833>
- NHS glucose safety guidance: <https://www.nhs.uk/conditions/high-blood-sugar-hyperglycaemia/>
