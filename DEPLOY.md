# Deploy Axora Finds: API on Render, website on Vercel (or Render)

Order matters: database, then email, then the API, then the website, then connect the two.

## 0. Put the code on GitHub
Push the whole project (`apps/api` and `apps/web`). Never commit `.env`.

## 1. Database (Render)
New > PostgreSQL. When it is ready, copy its **Internal Database URL**.
(Check Render's current limits: free databases expire after a limited time, so use a paid one for a real site.)

## 2. Email: this is why OTP failed on Render
Render's **free** web services block outbound SMTP (ports 25, 465, 587), so Gmail/SMTP can never send there.
Pick ONE option:

| Option | Cost | Setup |
| --- | --- | --- |
| **Brevo over HTTPS** (recommended to start) | free tier | `EMAIL_PROVIDER=brevo`, `BREVO_API_KEY` |
| **Resend over HTTPS** | free tier, needs a domain you own | `EMAIL_PROVIDER=resend`, `RESEND_API_KEY` |
| Gmail SMTP | paid Render instance only | `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` (Gmail app password) |

Brevo steps:
1. Create a Brevo account. Under **SMTP & API > API keys**, generate a key.
2. Under **Senders, domains & dedicated IPs > Senders**, add and verify the address you will send from.
3. Set `DEFAULT_FROM_EMAIL` to exactly `Axora Finds <that-address>`.

Deliverability: Gmail/Yahoo enforce DMARC, so mail sent *from* a `@gmail.com` address through a provider may be rewritten or land in spam. For real use, verify a domain you own and send from it.

## 3. API (Render Web Service)
New > Web Service > your repo, then:

| Setting | Value |
| --- | --- |
| Root Directory | `apps/api` |
| Runtime | Python 3 |

**Build Command** (copy this one line exactly):
```
pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate --noinput && python manage.py ensure_superuser
```

**Start Command:**
```
gunicorn config.wsgi:application --workers 2 --timeout 60
```

`ensure_superuser` creates your first staff login from `DJANGO_SUPERUSER_EMAIL` and `DJANGO_SUPERUSER_PASSWORD`, and does nothing if it already exists, so it is safe on every deploy. (An older version of this guide used `|| true` in the Build Command. If you ever see `createsuperuser: error: unrecognized arguments: || true`, you copied that old text with escaped pipes; use the command above, which has no `||`.)

Environment variables:

| Name | Value |
| --- | --- |
| `PYTHON_VERSION` | `3.12.3` |
| `DJANGO_DEBUG` | `0` |
| `DJANGO_SECRET_KEY` | long random string: `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `DATABASE_URL` | the Internal Database URL from step 1 |
| `DJANGO_SUPERUSER_EMAIL` / `DJANGO_SUPERUSER_PASSWORD` | your first staff login (created at build; the password must pass Django's strength check or the build stops and says why) |
| `EMAIL_PROVIDER` / `BREVO_API_KEY` | from step 2 |
| `DEFAULT_FROM_EMAIL` | `Axora Finds <your-verified-sender>` |
| `TEAM_EMAIL` | where staff notifications go |
| `SITE_URL` | your website URL, e.g. `https://axora-finds.vercel.app` (links in emails) |
| `CORS_ALLOWED_ORIGINS` | the same website URL, `https://...` with no trailing slash |

Optional: `CORS_ALLOWED_ORIGIN_REGEXES=^https://axora-finds.*\.vercel\.app$` to also allow Vercel preview deployments.
Render supplies `RENDER`, `RENDER_EXTERNAL_HOSTNAME` and `RENDER_EXTERNAL_URL` itself; the API uses them for allowed hosts, HTTPS and CSRF.

## 4. Website
### Vercel
1. Add New > Project > import the repo.
2. **Root Directory:** `apps/web`. Framework: Vite. Build command `npm run build`, output `dist`.
3. Environment variable: `VITE_API_BASE` = `https://YOUR-API.onrender.com/api`.
4. Deploy. `apps/web/vercel.json` makes page refreshes work (`/properties`, `/otp`, ...).
5. If the build complains about Node, set Node.js Version to 22.x in Project Settings.

### Render Static Site (alternative)
Root Directory `apps/web`, Build `npm install && npm run build`, Publish Directory `dist`, env `NODE_VERSION=22.12.0` and `VITE_API_BASE`.
Under Redirects/Rewrites add: Source `/*`, Destination `/index.html`, Action **Rewrite**.

## 5. Connect and check
`VITE_API_BASE` is baked in when the site is built, so redeploy the website after changing it.
1. Open the website, sign up, and confirm the code email arrives and signs you in.
2. Open `https://YOUR-API.onrender.com/admin/`: it should be fully styled. Log in with the staff email.
3. Staff dashboard > email panel (or `/admin/pages/sitesettings/email-test/`) sends a test message and shows the exact error if it fails.
4. As an owner, upload a property with photos. Publish it in the staff area. The photos should show.

## 6. Free-plan notes
- The API sleeps after 15 minutes idle; the first request afterwards can take up to a minute.
- Uploaded photos are now stored in the database, so redeploys no longer lose them. Photos uploaded *before* this update were saved on Render's disk and are gone: re-upload them.

## Troubleshooting
| Symptom | Fix |
| --- | --- |
| "We could not send the verification email" | Render logs show `Could not send ...: <reason>` plus what to check. Use the email test page. |
| Email test says "Could not reach ... / timed out" with SMTP | You are on Render free: switch to Brevo/Resend (step 2). |
| Brevo says sender not valid | Verify the sender in Brevo; set `DEFAULT_FROM_EMAIL` to exactly that address. |
| Browser console: CORS error | `CORS_ALLOWED_ORIGINS` must be the exact `https://...` origin, no trailing slash or path. |
| Admin unstyled | Redeploy this update (WhiteNoise now serves admin files even without collectstatic). |
| Admin login: CSRF 403 | Redeploy this update, or set `CSRF_TRUSTED_ORIGINS=https://YOUR-API.onrender.com`. |
| Refreshing a page gives 404 on Vercel | `apps/web/vercel.json` must be deployed. |
| Account stuck "not verified" | Log in with the password: you are sent to the code page with a fresh code. Or sign up again with the same email. |

## 7. Your current `.env`, line by line
The `.env` file only works on your own computer. On Render and Vercel you type the values into each service's **Environment** settings instead; never upload `.env` to GitHub.

| Your `.env` line | On your computer | On Render |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | fine, but use 50+ characters | new random key (see step 3); never reuse the local one |
| `DJANGO_DEBUG=0` | works; use `1` for daily development | must be `0` |
| `POSTGRES_*` empty (SQLite) | fine | **do not use SQLite on Render**: its disk is wiped on every deploy and restart, so every user, listing and photo would vanish. Set `DATABASE_URL` to a Render PostgreSQL database |
| `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, `SITE_URL` | `http://localhost:5173` | your Vercel (or Render static) `https://...` address, no trailing slash |
| `EMAIL_BACKEND` / `EMAIL_HOST` / `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` (Gmail) | works | **blocked on Render's free plan.** Delete these and use `EMAIL_PROVIDER=brevo` + `BREVO_API_KEY` (step 2). If you ever keep both, the provider now wins over a leftover `EMAIL_BACKEND` line |
| `EMAIL_TIMEOUT=30` | fine | use `10` so a failure does not freeze a request |
| `DEFAULT_FROM_EMAIL="Axora Finds <no-reply@gmail.com>"` | Gmail rewrites it to your Gmail address | use an address you verified with the provider |
| `VITE_API_BASE=/api` | fine (the dev server proxies it) | on Vercel: `https://YOUR-API.onrender.com/api` |

## 8. If a secret was ever pasted somewhere public
If you shared your `.env` (in a chat, a zip, a screenshot or GitHub), treat its secrets as exposed:
1. Gmail: Google Account > Security > 2-Step Verification > App passwords. Delete the old one and create a new one.
2. `DJANGO_SECRET_KEY`: generate a new one with `python -c "import secrets; print(secrets.token_urlsafe(50))"`. Everyone is signed out when it changes; that is expected.
3. A database password, if you ever set one: change it in Render.

## 9. Using your own PostgreSQL (instead of one created on Render)
Any PostgreSQL works: Render's, Neon, Supabase, Aiven, DigitalOcean, or your own server. The API only needs one address, `DATABASE_URL`. (Tested here against PostgreSQL 16, including photo storage and moving data over from SQLite.)

1. **Create the database** and a user with a password. Note the host, port, database name, user and password.
2. **Build the address:** `postgresql://USER:PASSWORD@HOST:5432/DBNAME?sslmode=require`
   Special characters in the password must be percent-encoded: `@` is `%40`, `/` is `%2F`, `:` is `%3A`, `#` is `%23`, `?` is `%3F`, space is `%20`. To encode one: `python -c "import urllib.parse as u; print(u.quote('your password', safe=''))"`.
3. **Put it in Render:** your API service > Environment > `DATABASE_URL`. The Build Command's `migrate` creates every table on the first deploy; there is nothing else to run.
4. **Check the connection from your own computer first** (same address, so you know it works before Render tries):
   ```
   cd apps/api
   # Windows PowerShell:  $env:DATABASE_URL="postgresql://..."      Mac/Linux:  export DATABASE_URL="postgresql://..."
   python manage.py migrate
   ```
   If that finishes without errors, the address is right.

Good to know:
- **SSL:** hosted databases require encryption, so keep `?sslmode=require`. `POSTGRES_SSLMODE` overrides it if you need to. For a database on the same private network you can use `sslmode=disable`.
- **Region:** put the database in the same region as the Render service; each page makes several queries and distance adds up.
- **Which address:** for a Render database use its *Internal* address inside Render and its *External* address from your computer. For other providers use the direct (non-pooled) address if they offer one. If you must use a pooled address (Neon `-pooler`, Supabase port 6543, pgbouncer), also set `DB_DISABLE_SERVER_SIDE_CURSORS=1`.
- **Firewalls:** if the provider restricts IP addresses, Render's outbound addresses must be allowed (Render lists a service's outbound IPs in its dashboard), or leave access open and rely on the password plus SSL.
- **Backups and size:** photos are stored in the database (resized WebP, usually 100-400 KB each), so backups matter and so does the plan's storage limit. Managed providers back up on a schedule that depends on the plan; on your own server, set up backups yourself.
- **Connections:** the API keeps connections open for 60 seconds (`DB_CONN_MAX_AGE`). If your plan allows very few connections, use `--workers 1` or set `DB_CONN_MAX_AGE=0`.

### Moving the data you already have in SQLite
Do this once, into an **empty** database:
```
cd apps/api
# 1. with DATABASE_URL NOT set (so it reads SQLite):
python manage.py dumpdata --natural-foreign --natural-primary --exclude contenttypes --exclude auth.permission --exclude admin.logentry --exclude sessions.session --indent 1 -o data.json
# 2. set DATABASE_URL to the new database, then:
python manage.py migrate
python manage.py loaddata data.json
```
Use `-o data.json`, not `> data.json`: PowerShell redirection saves UTF-16, which Django cannot read. Users and passwords, listings, photos stored in the database, favorites and inspections all move across. Photos that an older version saved as files on disk do not move; re-upload them. Do not commit `data.json` (it contains emails and password hashes).

| Error | Usual cause |
| --- | --- |
| `password authentication failed` | wrong user/password, or a special character in the password is not percent-encoded |
| `no encryption` / `SSL required` | add `?sslmode=require` to `DATABASE_URL` |
| `could not translate host name` / timed out | wrong host; an Internal Render address used from outside Render; a firewall blocking Render |
| `too many connections` | use `--workers 1`, `DB_CONN_MAX_AGE=0`, or the provider's pooled address with `DB_DISABLE_SERVER_SIDE_CURSORS=1` |
| `relation "..." does not exist` | migrations did not run: the Build Command must include `python manage.py migrate --noinput` |
