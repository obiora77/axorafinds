# Axora Finds

Verified rental homes in Nigeria. Visitors browse listings and request an inspection; owners sign up and submit listings; staff verify payments, confirm inspections and publish listings in Django admin. The aim is to cut the stress and high agent fees of house hunting.

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
python manage.py loaddata properties     # 8 published rentals + demo site settings
python manage.py createsuperuser         # this is your staff login
python manage.py runserver

# 2. Web (terminal 2)
cd apps/web
npm install
npm run dev                     # http://localhost:5173 (proxies /api and /media to :8000)
```

Staff queue: http://127.0.0.1:8000/admin/ . Tests: `cd apps/api && python manage.py test` (31 tests).

The Vue app's `package.json` is written by hand from the brief's dependency list; no scaffolder was used. Vite stays as the bundler because `@vitejs/plugin-vue` and `@tailwindcss/vite` are part of the required stack.

## How staff work

All in Django admin:

1. **Pages > Site settings**: enter the official bank name, account name and number, then tick **Is live**. This row is the only place the account exists. It is never in the frontend.
2. **Inspections** (pending queue): select requests and run **1. Mark payment verified**, then **2. Confirm inspection**, or **Reject inspection**. Confirm is refused until payment is verified (or the property has no fee).
3. **Listings > Properties**: select pending listings and run **Publish selected listings** or **Reject selected listings**. A listing needs at least one photo before it can be published.
4. **Accounts > Users**: create staff accounts (set role to Staff).

## Rules from the brief and where they are enforced

| Rule | Enforced by |
| --- | --- |
| Bank account never hardcoded in Vue | Stored in `SiteSettings`; frontend only calls `GET /api/payments/account` |
| Account shown only after the form succeeds, only for transfer, only to the creator | Signed 30-minute token returned by `POST /api/inspections` for transfer requests; same signed-in user required if the request was made signed in; `no-store` header |
| Not confirmed in the submitting request | Serializer ignores `status`/`payment_status`/`fee_amount`; always created `pending` |
| Staff verify payment before confirming | `Inspection.confirm()` refuses, admin fields are read-only, and a database `CHECK` constraint blocks it even for raw updates |
| Pay in person is a request | Stored `unpaid` + `pending`, no token, no account modal |
| Owner listings hidden until staff publish | Always saved `pending`; public API returns only `published` |
| Favorites persist per user | `Favorite` rows per seeker, loaded after login |
| No card numbers | No such fields anywhere |
| Grid never empty | `fixtures/properties.json` (8 rentals, two 2-bedroom parlour flats in Onitsha at N300,000) |
| Email only if `EMAIL_HOST` is set | `config/notify.py`; otherwise everything is stored and visible in admin |

## API

| Endpoint | Who |
| --- | --- |
| `GET /api/properties?state&city&q&max_price&bedrooms&type&page&page_size` | public, published only |
| `GET /api/properties/:slug` | public, published only |
| `POST /api/properties` (multipart, `photos` files) | owner, saved as pending |
| `POST /api/inspections` (name, phone, email, property, date, note, payment_choice) | public |
| `GET /api/payments/account` (header `X-Inspection-Token`) | creator of a transfer request |
| `POST /api/auth/register`, `/api/auth/token`, `/api/auth/token/refresh`, `GET /api/auth/me` | public / signed in |
| `POST /api/newsletter`, `POST /api/contact` | public |
| `GET /api/favorites`, `POST /api/favorites/:id`, `DELETE /api/favorites/:id` | seeker |

`bedrooms=2` means 2 or more. Public forms are rate limited per client.

## Motion

Per the brief's latest stack: **VueUse Motion** (`src/plugins/motion.ts`) for the hero entrance, scroll reveals and button hover; **Vue Transition / TransitionGroup** for page changes and the property grid; **GSAP** for the listing-card stagger, the account modal and the success states. All 150-250ms ease-out and skipped under `prefers-reduced-motion`. (The first half of the brief said GSAP only for the hero; the later VueUse Motion update takes over that part.)

## Things to review before launch

- **Bank details**: the seed row is a clearly marked demo account (`0000000000`) with **Is live** off. With `DJANGO_DEBUG=0` the API refuses to reveal it until staff enter real details and tick **Is live**.
- **Photos**: the seed listings hotlink Unsplash images; swap them for real listing photos in admin. The frontend falls back to an icon if an image fails to load.
- **Legal pages** (Terms, Privacy, Inspection and Refund Policy, Rental Agreement) are short draft text in `apps/web/src/lib/legal.ts`. Have them reviewed and replace them with your real policies.
- **Price symbol**: shown as `N300,000.00` as in the brief. Change `NAIRA_SYMBOL` in `src/lib/money.ts` to use the naira sign.
- **Auth tokens** are kept in `localStorage`. Rate-limit counters use Django's in-memory cache; use a shared cache (Redis or database) if you run several processes.
- `lucide-vue-next` is what the brief names; the package is now marked deprecated in favour of `@lucide/vue` (a drop-in swap of the import path).
- Tailwind 4 needs a modern browser (Chrome/Edge 111+, Safari 16.4+, Firefox 128+).

## Going live

Set `DJANGO_DEBUG=0`, a long `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS`, and Postgres (`POSTGRES_*`). Run `python manage.py collectstatic`, serve `/static/` and `/media/` from your web server, and run Django behind gunicorn/uwsgi with HTTPS (`DJANGO_SECURE_SSL_REDIRECT=1`, `DJANGO_BEHIND_PROXY=1` when a proxy terminates TLS). Build the web app with `npm run build` and serve `apps/web/dist`; set `VITE_API_BASE` if the API is on another origin.
