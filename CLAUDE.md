# CLAUDE.md: VTU Clubs project

Context file for Claude Code (or any developer) picking this project up. It records what was built, how it works,
and exactly where the work stopped.

## 1. What this project is
A college club management website for VTU with four clubs: **Tech, Sports, Culture, Multi Media**.
Students register with college details, verify their email with an OTP and receive a unique club ID.
Admins manage gallery photos, announcements, registration links and members.

Planned stack (from the original plan document): HTML/CSS/JS frontend, Python FastAPI backend, SQL database.
The database was changed to **Supabase (Postgres)** at the user's request.

## 2. What was done, in order
1. **Frontend prototype, version 1.** A single-page site was built from the plan. It has the dark and gold theme,
   four floating club cards, a right-to-left announcement ticker, club panels, a filtered gallery and a demo
   registration, OTP and club-ID flow.
2. **Frontend prototype, version 2.** The user's uploaded images were embedded (VTU logo, four club badges, two campus
   panoramas). The site was split into separate hash-routed pages: `#home`, `#tech`, `#sports`, `#culture`,
   `#multimedia`, `#gallery`, `#announcements`, `#register`, `#admin`. It also got 3D effects: a rotating badge ring,
   three.js embers, mouse parallax, tilt cards and 3D page transitions. A demo admin dashboard was added with login
   `admin` / `admin123`. It is a prototype only: OTP, admin login and data all live in the browser (localStorage).
   - Published at: https://claude.ai/artifact/WudSrQnC5uw2E1Vr8PRm3E (source: `vtu-clubs.html`, about 784 KB with images embedded).
   - It is not in this zip.
3. **Backend (this zip).** FastAPI + SQLAlchemy 2 on Supabase Postgres, with Supabase Storage for photos.
   Everything in section 3 below.

## 3. Backend architecture
```
app/
  main.py            FastAPI app, CORS, security headers, production safety checks, /uploads mount (local dev only)
  config.py          Settings from .env (pydantic-settings)
  database.py        Engine (Supabase-safe: sslmode=require, prepare_threshold=None for pgbouncer), get_db
  models.py          students, admins, clubs, memberships, club_counters, announcements, photos,
                     email_otps, pending_registrations, registration_links, audit_logs
  schemas.py         Pydantic request/response models and validation (USN regex, phone, year)
  security.py        bcrypt, JWT, HMAC-hashed OTPs, CSRF token generation
  dependencies.py    Cookie sessions, require_student / require_admin (+CSRF) / require_superadmin, rate limiter
  routers/           clubs, auth, memberships, announcements, gallery, admin
  services/          email_service, captcha_service, storage_service, membership_service
  scripts/           seed.py (4 clubs), create_admin.py
alembic/versions/    0001 create tables, 0002 enable Row Level Security (Postgres only)
tests/               pytest suite (SQLite, in-memory email outbox)
api-client/api.js    fetch wrappers for the frontend
```

### Key design decisions
- **Registration is three steps:** `POST /api/auth/register` parks the form as a `pending_registrations` row.
  `POST /api/auth/send-otp` emails the code. `POST /api/auth/verify-otp` checks captcha and OTP, then creates the
  student and membership. Nothing is a member before the OTP is verified.
- **Club ID** is `<PREFIX>-<joining year>-<0001>`, with prefixes TECH, SPORTS, CULT and MM. It is generated in
  `membership_service.next_number` by locking a `club_counters` row (`SELECT ... FOR UPDATE`). The unique
  constraints on `membership_code` and `(student_id, club_id)` act as a backstop.
- **OTP:** 6 digits, stored only as an HMAC-SHA256 hash, 5-minute expiry, 3 attempts, 60-second resend cooldown, single use.
  Captcha (Turnstile, hCaptcha or reCAPTCHA) is checked on verify-otp and skipped when `CAPTCHA_SECRET` is empty.
- **Student login** is passwordless (email OTP, `purpose="login"`), because the registration form has no password.
- **Admin auth:** bcrypt passwords. The JWT is in an HttpOnly cookie `admin_session` scoped to path `/api/admin`.
  A CSRF cookie plus an `X-CSRF-Token` header is required on every non-GET admin request. The token is returned by
  `/api/admin/login` and `/api/admin/me` because a cross-origin frontend cannot read the cookie. Roles are `admin`
  and `superadmin`, and the DB role is always re-checked. Sensitive actions are written to `audit_logs`.
- **Uploads:** size cap, real image decode with Pillow, only JPEG/PNG/WebP/GIF, random filenames.
  Stored in Supabase Storage via its REST API (httpx, no supabase-py), or in `uploads/` if Supabase is not configured.
- **Supabase specifics:** RLS is enabled on all tables with no policies. The backend connects as the owner role, which
  bypasses RLS, so only the public REST API is blocked. Use the Session pooler connection string.
- **Production guard:** with `APP_ENV=production` the app refuses to start with a weak `SECRET_KEY`, a non-SMTP email
  backend or insecure cookies, and `/docs` is disabled.

## 4. Commands
```bash
pip install -r requirements.txt
cp .env.example .env              # fill in Supabase URL, DB URL, service key, SECRET_KEY
alembic upgrade head
python -m app.scripts.seed
python -m app.scripts.create_admin NAME --super
uvicorn app.main:app --reload     # docs at /docs
pytest
```
Quick local run with no Supabase: `DATABASE_URL=sqlite:///./dev.db` (tables are auto-created for SQLite only).

## 5. WHERE IT ENDED: current status
**Done:** all backend code, migrations, seed and admin scripts, tests, README, Dockerfile, frontend API client and this file.

**Not verified: read this first.** The backend was written in an environment with no network access, so dependencies
were never installed. The code compiles (`python -m compileall`), but **nothing has been executed**: no server start,
no migration against Supabase, and none of the pytest tests have been run. Expect a few small bugs on the first run.
Package versions in `requirements.txt` were pinned from memory and should be checked.

**Not done:**
- The frontend is now wired to this API (see section 8), but that wiring has not been tested in a browser.
- Captcha widget (e.g. Cloudflare Turnstile) is not placed on any page.
- No Supabase project has been connected, and no real SMTP email has been tested.
- The VTU logo and badges exist only as embedded images in the prototype. They have not been saved as files under
  `frontend/assets/images/`.
- The question of how many admins are needed was never answered. Only one `--super` admin script exists, plus the
  superadmin-only `POST /api/admin/admins` endpoint.
- The rate limiter is in memory (fine for one instance only).

## 6. Suggested next steps, in order
1. Install dependencies, run `pytest`, and fix failures.
2. Create the Supabase project, fill `.env`, run `alembic upgrade head`, the seed script and `create_admin`.
3. Open `/docs` and walk the registration flow by hand (register, send-otp, verify-otp), then the admin flow.
4. Split the prototype into real frontend pages and replace its demo logic with calls from `api-client/api.js`.
5. Add the captcha widget and send its token as `captcha_token` to `/api/auth/verify-otp`.
6. Configure SMTP, then deploy (see README), setting `COOKIE_SAMESITE`/`COOKIE_SECURE` correctly for the frontend origin.
7. Decide the admin count and approval policy (`REQUIRE_ADMIN_APPROVAL`, `REQUIRE_REGISTRATION_LINK`, `ALLOWED_EMAIL_DOMAINS`).

## 6b. Fix log
- Python 3.9 compatibility: `X | None` annotations crash on Python 3.9 (`TypeError: unsupported operand type(s) for |`).
  They were replaced with `Optional[X]` in utils.py, security.py, dependencies.py, captcha_service.py and routers/admin.py.
  Keep using `Optional[...]` so the project still runs on 3.9.

## 8. Update: frontend and backend combined
- Project root is now `vtu-clubs/` with `frontend/`, `backend/`, a root `Dockerfile`, `README.md` and this file.
- The frontend is split into `index.html`, `assets/css/style.css` and `assets/js/main.js` (paths are relative, so it also opens from disk, but the API calls need the backend running).
- `frontend/index.html` is the hash-routed site (#home, #tech, #sports, #culture, #multimedia, #gallery, #announcements,
  #register, #admin). Images are real files in `frontend/assets/images/` (no more embedded base64).
- The backend serves it: `app/main.py` mounts `frontend/` at `/` as the LAST mount, so one server and one origin
  (no CORS, cookies work with the default Lax settings). Open http://127.0.0.1:8000/ and /docs.
- The old demo logic is gone. The page now calls the real API: announcements and gallery are loaded from the server,
  registration uses register, send-otp and verify-otp (the OTP arrives by email, or in the uvicorn terminal with
  EMAIL_BACKEND=console), and the admin page uses the real login, CSRF header, dashboard, announcements, photo upload,
  registration links (`#register?link=TOKEN`), member search, status changes and CSV export.
- When no photos are uploaded the gallery shows decorative sample crops of the campus artwork.
- Not done or untested: nothing here has been executed. No captcha widget, no password-based student login page
  (students log in only through the OTP API; the site has no student login screen yet), and the three.js and Google
  Fonts files load from CDNs.

## 7. Conventions for future changes
- Backend code stays sync (`def` endpoints, sync SQLAlchemy); FastAPI runs them in a threadpool.
- Club IDs and OTP checks must stay server-side. Never generate IDs in JavaScript.
- Every new admin route must depend on `require_admin` (or `require_superadmin`) and call `audit()` for sensitive actions.
- Use `utcnow()` / `aware()` from `app/utils.py` for datetimes (SQLite returns naive values).
- Never commit `.env` or the Supabase service-role key.
- Schema changes: edit `models.py`, then `alembic revision --autogenerate -m "..."`. Do not edit 0001.
