# VTU Clubs: website + backend in one project

```
vtu-clubs/
  frontend/   the website (index.html + assets/images). Served by the backend, no separate web server needed.
  backend/    FastAPI + Supabase (see backend/README.md for Supabase setup, endpoints and deployment)
  Dockerfile  builds both together
  CLAUDE.md   what was built and where it stopped
```

## Run it (Windows)
```
cd vtu-clubs\backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env          (then edit .env: DATABASE_URL, SECRET_KEY, Supabase keys)
alembic upgrade head            (or paste backend\supabase\schema.sql into the Supabase SQL Editor)
python -m app.scripts.seed
python -m app.scripts.create_admin yourname --super
uvicorn app.main:app --reload
```
Then open:
- http://127.0.0.1:8000/       the website (Home, clubs, Gallery, Register, Admin)
- http://127.0.0.1:8000/docs   API explorer

No Supabase yet? Set `DATABASE_URL=sqlite:///./dev.db` in `.env` to try everything locally.
With `EMAIL_BACKEND=console` the OTP code is printed in the terminal window running uvicorn.

Always run commands from the `backend` folder. Requires Python 3.9+.
