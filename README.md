# Axora Finds

Verified rental homes in Nigeria. Visitors browse listings and request an inspection; owners sign up and submit listings; staff verify payments, confirm inspections and publish listings. Staff work from a signed-in dashboard in the Vue app **and** from Django admin. The aim is to cut the stress and high agent fees of house hunting.

Stack: Vue 3, TypeScript, Tailwind CSS 4, Pinia, GSAP, VueUse Motion, vee-validate + zod (frontend) and Django, Django REST framework, SimpleJWT (API).

```
axora-finds/
  apps/web/   Vue + Vite single-page app
  apps/api/   Django API + admin (SQLite by default, PostgreSQL optional)
  .env.example
```

## Run it locally

You need Node 20.19+ (or 22.12+) and Python 3.10+.

```bash
cp .env.example .env            # one .env at the repo root, shared by API and web

# 1. API (terminal 1)
cd apps/api
python -m venv .venv
source .venv/bin/activate     
pip install -r requirements.txt
python manage.py migrate
python manage.py loaddata properties     # 8 published rentals, 6 demo reviews + demo site settings
python manage.py createsuperuser         # this is your staff login
python manage.py runserver

# 2. Web (terminal 2)
cd apps/web
npm install
npm run dev                     # http://localhost:5173 (proxies /api and /media to :8000)
```

Staff queue: http://127.0.0.1:8000/admin/ and the signed-in dashboard at http://localhost:5173/admin . Tests: `cd apps/api && python manage.py test`.

The Vue app's `package.json` is written by hand from the brief's dependency list; no scaffolder was used. Vite stays as the bundler because `@vitejs/plugin-vue` and `@tailwindcss/vite` are part of the required stack.

## How staff work

Staff accounts sign in through the normal login page; a staff account lands on `/admin`, the
frontend operations dashboard. The same queues are available in Django admin (`/admin/` on the
API host), and both places enforce identical rules. The frontend dashboard has tabs for the
overview, listings, inspections, reviews, contact messages/newsletter subscribers, site settings
and email delivery.

1. **Settings** (frontend) or **Pages > Site settings** (Django admin): enter the official bank name, account name and number, then tick **Is live**. This row is the only place the account exists. It is never in the frontend.
2. **Inspections** (pending queue): select requests and run **1. Mark payment verified**, then **2. Confirm inspection**, or **Reject inspection**. Confirm is refused until payment is verified (or the property has no fee).
3. **Listings > Properties**: select pending listings and run **Publish selected listings** or **Reject selected listings**. A listing needs at least one photo before it can be published.
4. **Reviews**: signed-in visitors' testimonials wait here unpublished. Publish them on the home page (or hide them again).
5. **Accounts > Users**: create staff accounts (set role to Staff). Role Staff sets Django's `is_staff` automatically and grants the model permissions the queues use, so the account can work in both Django admin and the Vue dashboard immediately.

Staff decisions also trigger the matching email: payment verified, inspection confirmed/rejected, listing published/rejected, and review published. Inspections and listings submitted from the website email the team and send the visitor/owner a receipt. Each dashboard action reports whether that email was accepted, with the exact error when it was not.

Django admin's home page has the same queue counts at a glance, plus **Send a test email** under
Site settings.

## Email notifications

Templates live in `apps/api/templates/emails/` (one `.html` and one `.txt` per message; the HTML parts share `base.html` and the text parts share `_details.txt`). The senders are in `apps/api/config/emails.py`. Sending is best-effort: a mail outage is logged and never breaks a form submission or a staff action.

Every HTML email embeds `apps/api/static/img/logo.png` as an inline `Content-ID` part, so the logo appears even when the browser blocks remote images. No public image URL or static file server is needed.

| Message | Goes to | Trigger |
| --- | --- | --- |
| Welcome | new account | registration |
| Newsletter confirmation / team alert | subscriber / team | newsletter form |
| Contact acknowledgement / team alert | visitor / team | contact form |
| Inspection received | visitor | `POST /api/inspections` |
| Inspection request alert | team | `POST /api/inspections` |
| Payment verified | visitor | staff action |
| Inspection confirmed / rejected | visitor | staff action |
| Listing received / team alert | owner / team | `POST /api/properties` |
| Listing published / rejected | owner | staff action |
| Review received / team alert | author / team | `POST /api/reviews` |
| Review published | author | staff action |

Configuration comes from `.env` (see `.env.example`): `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `EMAIL_USE_SSL`, `EMAIL_TIMEOUT`, `TEAM_EMAIL`, `DEFAULT_FROM_EMAIL` and `SITE_URL`. Restart the Django server after changing `.env`; editing it does not reload a running process. With no `EMAIL_HOST`, development prints messages to the terminal and tests use Django's in-memory outbox.

Check the setup by sending a real message through the configured backend:

```bash
cd apps/api
python manage.py send_test_email --to you@example.com
```

The command prints the backend, host, port, encryption and From address, then the exact SMTP error if delivery fails (for example a Gmail `535` authentication error). The same check, with a **Send test email** form, lives in the frontend dashboard's **Email** tab and in Django admin under **Pages > Site settings > Send a test email**. Both show which templates are missing and the last delivery error.

For Gmail, use a 16-character App Password, keep 2-Step Verification on, and use `EMAIL_PORT=587`, `EMAIL_USE_TLS=1`, `EMAIL_USE_SSL=0`. Spaces in the App Password are stripped automatically, so pasting it in Google's four-group format is safe. Check the Spam folder too: Gmail may deliver the first message there.

**"Connection unexpectedly closed"** means the mail server dropped the connection; the record and the staff decision were still saved. This is a network/SMTP problem, not a template error. Check that outbound port 587 is allowed, try `EMAIL_PORT=465` with `EMAIL_USE_SSL=1` and `EMAIL_USE_TLS=0`, and turn off any VPN or antivirus mail shield. Some home, office and mobile networks block all outbound SMTP; on one of those, use a mail provider that sends over HTTPS (port 443). After fixing delivery, press **Resend email** on the confirmed/rejected inspection, published/rejected listing or published review (the same action exists in Django admin). The decision is not repeated or changed.

With no `EMAIL_HOST`, development prints messages to the terminal and tests use Django's in-memory outbox. With `DJANGO_DEBUG=0` and no host, the backend stays on SMTP so delivery is reported as "not configured" instead of silently discarding messages. A missing `.txt` part no longer breaks a send: the HTML is converted to plain text at runtime, and the Email tab flags the missing template.

The test suite forces Django's in-memory (locmem) backend, so `python manage.py test` never contacts a mail server even when `.env` points at SMTP.

Team alerts use the visitor's address as `Reply-To`, so staff can answer directly. Emails never contain the bank account: a transfer inspection tells the visitor to return to the listing, where the signed-token flow reveals it.


## Rules from the brief and where they are enforced

| Rule | Enforced by |
| --- | --- |
| Bank account never hardcoded in Vue | Stored in `SiteSettings`; frontend only calls `GET /api/payments/account` |
| Account shown only after the form succeeds, only for transfer, only to the creator | Signed 30-minute token returned by `POST /api/inspections` for transfer requests; same signed-in user required if the request was made signed in; `no-store` header |
| Not confirmed in the submitting request | Serializer ignores `status`/`payment_status`/`fee_amount`; always created `pending` |
| Staff verify payment before confirming | `Inspection.confirm()` refuses, admin fields are read-only, and a database `CHECK` constraint blocks it even for raw updates |
| Pay in person is a request | Stored `unpaid` + `pending`, no token, no account modal |
| Owner listings hidden until staff publish | Always saved `pending`; public API returns only `published` |
| Reviews hidden until staff publish | `Review.is_published` defaults off; `GET /api/reviews` returns only published rows |
| Favorites persist per user | `Favorite` rows per seeker, loaded after login |
| No card numbers | No such fields anywhere |
| Grid never empty | `fixtures/properties.json` (8 rentals, two 2-bedroom parlour flats in Onitsha at N300,000) |
| Email sends through SMTP when configured | `config/emails.py`; development uses the console backend when no `EMAIL_HOST`, tests use locmem, and production with no host reports "not configured" instead of discarding messages; stored records remain in admin |

## API

| Endpoint | Who |
| --- | --- |
| `GET /api/properties?state&city&q&max_price&bedrooms&type&page&page_size` | public, published only |
| `GET /api/properties/mine` | owner, their own listings in every state |
| `GET /api/properties/:slug` | public, published only |
| `POST /api/properties` (multipart, `photos` files) | owner, saved as pending |
| `POST /api/inspections` (name, phone, email, property, date, note, payment_choice) | public |
| `GET /api/payments/account` (header `X-Inspection-Token`) | creator of a transfer request |
| `POST /api/auth/register`, `/api/auth/token`, `/api/auth/token/refresh`, `GET /api/auth/me` | public / signed in |
| `POST /api/newsletter`, `POST /api/contact` | public |
| `GET /api/reviews`, `POST /api/reviews` | public list / signed-in submission (moderated) |
| `GET /api/favorites`, `POST /api/favorites/:id`, `DELETE /api/favorites/:id` | seeker |
| `GET /api/staff/overview` | staff: queue counts, email health and recent items |
| `GET /api/staff/listings`, `POST /api/staff/listings/:id/publish`, `/reject`, `/resend-email` | staff: moderate owner listings, retry the decision email |
| `GET /api/staff/inspections`, `POST /api/staff/inspections/:id/verify-payment`, `/confirm`, `/reject`, `/resend-email` | staff: inspection queue, retry the decision email |
| `GET /api/staff/reviews`, `POST /api/staff/reviews/:id/publish`, `/unpublish`, `/resend-email` | staff: moderate testimonials, retry the published email |
| `GET /api/staff/messages`, `DELETE /api/staff/messages/:id` | staff: contact inbox |
| `GET /api/staff/subscribers`, `DELETE /api/staff/subscribers/:id` | staff: newsletter list |
| `GET/PUT /api/staff/settings`, `GET /api/staff/users`, `GET /api/staff/email`, `POST /api/staff/email/test` | staff |

`bedrooms=2` means 2 or more. Public forms are rate limited per client.

## Motion

Per the brief's latest stack: **VueUse Motion** (`src/plugins/motion.ts`) for the hero entrance, scroll reveals and button hover; **Vue Transition / TransitionGroup** for page changes and the property grid; **GSAP** for the listing-card stagger, the account modal and the success states. All 150-250ms ease-out and skipped under `prefers-reduced-motion`. (The first half of the brief said GSAP only for the hero; the later VueUse Motion update takes over that part.)

The home-page review rail is the one deliberate exception: a slow CSS marquee that moves left to right, pauses on hover and with its **Pause reviews** button, and becomes a normal horizontal scroll under `prefers-reduced-motion`.

## Things to review before launch

- **Bank details**: the seed row is a clearly marked demo account (`0000000000`) with **Is live** off. With `DJANGO_DEBUG=0` the API refuses to reveal it until staff enter real details and tick **Is live**.
- **Photos**: the seed listings hotlink Unsplash images; swap them for real listing photos in admin. The frontend falls back to an icon if an image fails to load.
- **Reviews**: the six home-page testimonials in `fixtures/properties.json` are demo content. Replace or unpublish them in **Pages > Reviews** before launch; new submissions stay hidden until staff publish them.
- **Legal pages** (Terms, Privacy, Inspection and Refund Policy, Rental Agreement) are short draft text in `apps/web/src/lib/legal.ts`. Have them reviewed and replace them with your real policies.
- **Price symbol**: shown as `N300,000.00` as in the brief. Change `NAIRA_SYMBOL` in `src/lib/money.ts` to use the naira sign.
- **Auth tokens** are kept in `localStorage`. Rate-limit counters use Django's in-memory cache; use a shared cache (Redis or database) if you run several processes.
- `lucide-vue-next` is what the brief names; the package is now marked deprecated in favour of `@lucide/vue` (a drop-in swap of the import path).
- Tailwind 4 needs a modern browser (Chrome/Edge 111+, Safari 16.4+, Firefox 128+).

## Going live

Set `DJANGO_DEBUG=0`, a long `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS`, and Postgres (`POSTGRES_*`). Set the email values (`EMAIL_BACKEND=smtp`, `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`, `TEAM_EMAIL`) and the public `SITE_URL` so notification links point at the real site. Run `python manage.py collectstatic`, serve `/static/` and `/media/` from your web server, and run Django behind gunicorn/uwsgi with HTTPS (`DJANGO_SECURE_SSL_REDIRECT=1`, `DJANGO_BEHIND_PROXY=1` when a proxy terminates TLS). Build the web app with `npm run build` and serve `apps/web/dist`; set `VITE_API_BASE` if the API is on another origin. If Django admin and the Vue app share a host, send `/admin/` (with the trailing slash) to Django and `/admin` (no slash) to the SPA.
