# Personalized Networking Assistant

An AI-powered web application that generates smart, tailored conversation
starters for professional or social networking events. It extracts themes
from an event description using **DistilBERT** (zero-shot classification,
run locally) and generates context-aware conversation prompts using
**Google's Gemini API**. It also offers quick fact-checking via the
**Wikipedia API**, and lets registered users log their conversation
history and rate suggestions.

## Features

- **User accounts** — register and log in; every user's history and
  feedback is private to them.
- **Profile-based personalization** — set your role, industry, and
  networking goal once; every suggestion generated afterward is written
  with that context in mind.
- **Tone control** — pick formal, casual, or witty phrasing per request,
  without changing anything else about the pipeline.
- **Smart conversation starters** — describe an event and your interests,
  get 2–3 tailored conversation openers.
- **Icebreaker confidence scoring** — each suggestion is rated 1–5 with a
  plain-language reason (e.g. "ends in a question", "references your
  interests"), so it's clear at a glance which starters are strongest.
- **Quick fact verification** — look up a short, reliable summary of any
  topic via Wikipedia.
- **History & feedback** — review past generated conversations (including
  the tone and confidence scores used) and which suggestions you rated
  👍/👎, scoped to your account.
- **Rate limiting** — the two most expensive endpoints (conversation
  generation and fact-checking) are throttled per client to prevent abuse.
- **Resilient error handling** — if an AI model fails to load (e.g. no
  network on first startup), the rest of the app keeps working and the
  affected endpoints return a clear "temporarily unavailable" message
  instead of crashing; database and unexpected errors are handled the
  same way — logged in full server-side, never shown to the client as a
  raw stack trace.
- **Polished, multipage UI** — a Home/Profile/Fact Check/History/Feedback
  sidebar layout with a consistent SaaS-style theme, loading states on
  every network call, and friendly, specific error messages throughout.

## Architecture

```
┌─────────────┐        HTTP + JWT        ┌──────────────────┐
│  Streamlit  │ ───────────────────────► │     FastAPI       │
│  Frontend   │ ◄─────────────────────── │     Backend        │
└─────────────┘                          └──────────┬─────────┘
                                                     │
                          ┌──────────────────────────┼──────────────────────┐
                          │                          │                      │
                   ┌──────▼──────┐          ┌────────▼─────────┐   ┌────────▼────────┐
                   │  DistilBERT │          │   Gemini API      │   │  Wikipedia API   │
                   │ (zero-shot, │          │ (gemini-2.5-flash,│   └──────────────────┘
                   │ run locally)│          │  hosted)          │
                   └─────────────┘          └────────┬──────────┘
                                                     │
                                            ┌────────▼────────┐
                                            │  SQLite Database │
                                            │ users / history / │
                                            │     feedback      │
                                            └────────────────────┘
```

**Two different approaches to running the AI models, deliberately:**
DistilBERT (theme extraction) runs **locally** via `transformers.pipeline()`
— it's small and fast enough on CPU that there's no reason to add a
network dependency for it. Conversation generation instead calls
**Google's Gemini API** (gemini-2.5-flash by default) — a model that size
would be far too slow to run locally on CPU for an interactive request,
and produces noticeably better, more instruction-following output than a
small local generative model would. See `app/services/topic_generator.py`'s
docstring for the full reasoning.

**Authentication:** Username/password accounts, hashed with bcrypt. On
login, the backend issues a signed JWT access token. The frontend stores
this token in its session and sends it as a `Bearer` token on every
subsequent request. Protected endpoints reject requests with a missing,
invalid, or expired token (`401 Unauthorized`).

**Authorization / data isolation:** Every conversation and feedback record
is tied to the `user_id` of whoever created it. Users can only ever read
their own history and feedback — there is no endpoint that returns another
user's data.

**Rate limiting:** `/generate-conversation` (10 requests/minute) and
`/fact-check` (20 requests/minute) are limited per client IP via `slowapi`.
Exceeding the limit returns `429 Too Many Requests`.

## Tech Stack

| Layer                | Technology                                          |
|------------------------|--------------------------------------------------------|
| Backend                | FastAPI                                                 |
| Frontend               | Streamlit                                               |
| Theme extraction       | DistilBERT (zero-shot classification, local CPU)        |
| Conversation generation | Gemini API (gemini-2.5-flash by default, hosted, configurable) |
| Fact-checking          | Wikipedia REST API                                       |
| Database               | SQLite via SQLAlchemy                                   |
| Auth                   | JWT (python-jose) + bcrypt (passlib)                    |
| Rate limiting          | slowapi                                                 |
| Containerization       | Docker + Docker Compose                                 |
| Testing                | pytest, httpx TestClient                                |

Theme extraction runs entirely on **CPU, locally, with no API key**.
Conversation generation requires a free Google account and a
`GEMINI_API_KEY` (see Setup below) since it calls a hosted model rather
than running one locally.

## Project Structure

```
networking-assistant/
├── .streamlit/
│   └── config.toml              # Streamlit theme (colors/font) -- see frontend/common.py for the rest of the UI polish
├── app/
│   ├── main.py                  # FastAPI app entry point, DB init, rate limiter wiring
│   ├── models.py                # Pydantic request/response schemas
│   ├── db_models.py             # SQLAlchemy ORM models (User, ConversationHistory, Feedback)
│   ├── database.py              # DB engine/session setup
│   ├── auth.py                  # Password hashing, JWT create/decode
│   ├── dependencies.py          # get_current_user FastAPI dependency
│   ├── rate_limit.py            # slowapi Limiter configuration
│   ├── routes/
│   │   ├── auth.py               # /auth/register, /auth/login
│   │   └── conversation.py       # all other API routes (protected)
│   └── services/
│       ├── event_analyzer.py    # DistilBERT theme extraction
│       ├── topic_generator.py   # Gemini API conversation generation (tone + profile aware)
│       ├── scorer.py            # Rule-based icebreaker confidence scoring
│       ├── fact_checker.py      # Wikipedia fact-checking
│       ├── history_logger.py    # Conversation history persistence (DB)
│       ├── feedback_logger.py   # Feedback persistence (DB)
│       └── profile_service.py   # Profile (role/industry/goal) persistence (DB)
├── frontend/
│   ├── app.py                   # Home page: login/register gate + generate flow
│   ├── common.py                # Shared session/auth helpers used by every page
│   └── pages/                   # Streamlit auto-discovers these as sidebar nav
│       ├── 1_👤_Profile.py
│       ├── 2_🔍_Fact_Check.py
│       ├── 3_🕘_History.py
│       └── 4_📊_Feedback.py
├── scripts/
│   └── benchmark_theme_extraction.py  # Small theme-extraction accuracy check
├── tests/                       # pytest test suite
├── data/                        # generated at runtime: app.db (gitignored)
├── Dockerfile.backend
├── Dockerfile.frontend
├── docker-compose.yml
├── requirements.txt             # full backend dependencies (incl. torch/transformers)
├── requirements-frontend.txt    # minimal frontend-only dependencies
├── .env.example
└── README.md
```

## Documentation

The documentation pack lives in [Documentation](./Documentation/README.md), with the eight
template phases nested underneath it.

## Setup (without Docker)

**Requirements:** Python 3.10+ (3.11+ recommended)

1. **Create and activate a virtual environment**

   ```bash
   python -m venv venv

   # macOS/Linux
   source venv/bin/activate

   # Windows
   venv\Scripts\activate
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

   > First run will download the DistilBERT model weights (a few hundred
   > MB) from Hugging Face for local theme extraction — this only happens
   > once and is cached locally afterward. Conversation generation does
   > NOT download anything; it calls a hosted model over the network
   > instead (see step 3).

3. **Configure environment variables**

   ```bash
   cp .env.example .env
   ```

   Most variables have a safe default for local development, but
   **`GEMINI_API_KEY` is required for conversation generation to work.**
   Get a free key at https://aistudio.google.com/apikey and set it in
   `.env`. Without it, `/generate-conversation` will return a `503` —
   every other feature (auth, profile, history, feedback, fact-check, and
   theme extraction) works fine without it.

   Also set a real `SECRET_KEY` before running anywhere other than your
   own machine — see comments in `.env.example`.

## Running the App (without Docker)

You need **two terminals** (one for the backend, one for the frontend).

**Terminal 1 — Backend (FastAPI)**

```bash
uvicorn app.main:app --reload
```

- API: http://127.0.0.1:8000
- Interactive Swagger docs: http://127.0.0.1:8000/docs
- On first startup, the SQLite database and tables are created
  automatically at `data/app.db`.

**Terminal 2 — Frontend (Streamlit)**

```bash
streamlit run frontend/app.py
```

- App UI: http://localhost:8501

> The frontend expects the backend to already be running at
> `http://127.0.0.1:8000`. Start the backend first. On first load you'll
> see a Log In / Register screen — create an account to use the app.

## Running with Docker

**Requirements:** Docker and Docker Compose.

```bash
docker compose up --build
```

This builds and starts both containers:

- Frontend UI: http://localhost:8501
- Backend API: http://localhost:8000
- Swagger docs: http://localhost:8000/docs

The SQLite database is persisted in a named Docker volume (`app-data`), so
accounts/history/feedback survive `docker compose down`. To wipe all data,
use `docker compose down -v` instead.

To override the default secret key when running via Docker, set it in your
shell before starting, or in a `.env` file in the project root (Docker
Compose automatically reads `.env` from the project directory):

```bash
SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))") docker compose up --build
```

To stop the containers:

```bash
docker compose down
```

## Running Tests

```bash
pytest
```

With a coverage report:

```bash
pytest --cov=app
```

Tests use an isolated in-memory SQLite database per test (see
`tests/conftest.py`) — they never touch your real `data/app.db`. Test
coverage includes:

- `test_event_analyzer.py`, `test_topic_generator.py` — AI service logic
- `test_scorer.py` — icebreaker confidence scoring heuristics
- `test_fact_checker.py` — Wikipedia integration, with the network call
  mocked so tests run without internet access
- `test_history_logger.py`, `test_feedback_logger.py` — database persistence
- `test_auth.py` — registration, login, and credential-failure handling
- `test_routes.py` — full API integration tests, including auth enforcement,
  per-user data isolation, profile updates, and tone/confidence scoring
- `test_error_handling.py` — verifies model-unavailable failures return a
  clean 503 with no internal error details leaked to the client

## API Reference

All endpoints except `/`, `/auth/register`, and `/auth/login` require an
`Authorization: Bearer <token>` header.

| Method | Endpoint                | Description                                       |
|--------|---------------------------|----------------------------------------------------|
| GET    | `/`                        | Health check                                       |
| POST   | `/auth/register`           | Create a new account                               |
| POST   | `/auth/login`               | Log in, receive a JWT access token                  |
| POST   | `/analyze-event`            | Extract themes from an event description            |
| POST   | `/fact-check`                | Get a Wikipedia summary for a topic (rate-limited)  |
| POST   | `/generate-conversation`     | Full pipeline: analyze → generate → score → log (rate-limited) |
| POST   | `/feedback`                  | Record like/dislike on a suggestion                 |
| GET    | `/history`                    | Your 5 most recent generated conversations          |
| GET    | `/feedback-history`            | Your 10 most recent feedback entries                |
| GET    | `/profile`                     | Your saved role / industry / networking goal        |
| PUT    | `/profile`                     | Update your role / industry / networking goal       |

Full interactive documentation (with request/response schemas) is available
at `/docs` once the backend is running.

> **Note:** the Swagger UI's "Authorize" button expects OAuth2 form-encoded
> credentials, but `/auth/login` accepts a plain JSON body. To test
> protected endpoints from `/docs`, first call `POST /auth/login` directly
> (via "Try it out"), copy the `access_token` from the response, then paste
> it into the Authorize dialog as the bearer token.

## Model Evaluation

`scripts/benchmark_theme_extraction.py` is a small, informal accuracy
check for the DistilBERT zero-shot theme extraction in
`app/services/event_analyzer.py`. It runs 15 hand-written event
descriptions through `extract_event_themes` and checks whether the
top-predicted theme matches what a human would expect, printing a
markdown table + top-1 accuracy that can be pasted straight into a report.

Run it locally (after installing `requirements.txt`) with:

```bash
python scripts/benchmark_theme_extraction.py
```

This is intentionally framed as a sanity check, not a rigorous
evaluation — 15 examples is far too small a sample to make a real accuracy
claim, and "expected theme" is a judgment call rather than labeled ground
truth. It's meant to demonstrate that the model was actually tested
against concrete cases, not just wired up and trusted.

## Limitations & Future Work

Being explicit about where this system currently falls short:

- **Conversation generation now depends on an external network service.**
  Since replacing the local GPT-2 model with Google's Gemini API,
  `/generate-conversation` requires network access and a valid
  `GEMINI_API_KEY`, and its latency/availability now depend on a
  third-party service rather than being fully self-contained. The
  trade-off is real: output quality is substantially better than a small
  local model could produce, but the app is no longer usable fully
  offline the way DistilBERT-based theme extraction still is. If this
  ever needs to run in a fully offline/air-gapped environment, swapping
  `app/services/topic_generator.py` back to a local pipeline (as
  `event_analyzer.py` still does) would be the fix.
- **Zero-shot classification is sensitive to label phrasing.** DistilBERT's
  zero-shot pipeline scores a description against candidate label strings;
  changing "climate change" to "climate action," for instance, can shift
  results. The `DEFAULT_THEMES` list was chosen by inspection, not tuned
  systematically.
- **The confidence scorer is heuristic, not learned.** It rewards
  structural properties (question phrasing, length, keyword overlap) that
  correlate with a *usable* icebreaker, but it has no way to judge whether
  a grammatically fine suggestion is actually a good one to say out loud.
  A learned scorer trained on real thumbs-up/down feedback (which the app
  already collects) would be a natural next step.
- **SQLite is a single-file database.** It's the right choice for a
  small, single-instance deployment, but it doesn't support concurrent
  writes from multiple backend processes — a real multi-user deployment
  at scale would need Postgres, which `DATABASE_URL` already supports
  swapping in without code changes.
- **No password reset or email verification.** Registration only asks for
  a username and password; there's no recovery flow if a password is
  forgotten, and usernames aren't verified as belonging to a real person.
- **Tone control is prompt-level only.** The three tone options are
  instructions given directly to Gemini (see `_build_user_message()` in
  `app/services/topic_generator.py`). Instruction-tuned models generally
  follow this kind of steering well, but it's still a soft instruction
  rather than a guarantee — "witty" and "casual" outputs can occasionally
  read similarly.
- **Future work:** persisting the DistilBERT candidate-label set per user
  (so someone who mostly attends legal or medical events could bias theme
  extraction toward those categories), using the feedback table to
  eventually re-rank generated suggestions instead of relying purely on
  the rule-based confidence score, and adding a retry/backoff wrapper
  around the Gemini API call for transient failures (a rate limit or
  momentary provider hiccup currently surfaces as a 503 on the first try
  rather than being retried automatically).

## Assumptions Made

Since the original project brief didn't specify auth, a database, or
deployment tooling, the following industry-standard choices were made:

- **Database:** SQLite, for zero external setup. Swappable for
  Postgres/MySQL by changing `DATABASE_URL` — no code changes needed.
- **Auth:** Stateless JWT bearer tokens rather than server-side sessions,
  so the API remains horizontally scalable.
- **Password hashing:** bcrypt via `passlib`, the standard choice for
  password storage.
- **Rate limiting:** Per-IP limits via `slowapi`, applied only to the two
  most expensive/abusable endpoints rather than globally.
- **Token lifetime:** 60 minutes by default, configurable via
  `ACCESS_TOKEN_EXPIRE_MINUTES`.

## Notes

- **Theme extraction (DistilBERT) runs locally on CPU** — no API key
  required. **Conversation generation calls a hosted model** via Google's
  Gemini API and requires a valid `GEMINI_API_KEY` (see Setup above and
  `.env.example`). This is a deliberate split, not an inconsistency — see
  the Architecture section for why.
- The first request to `/analyze-event` after starting the backend will
  be slower than subsequent ones, since the DistilBERT model is loaded
  into memory once at startup. `/generate-conversation` doesn't have this
  warm-up cost (there's no local model to load) but does depend on the
  Gemini API being reachable and responsive per-request.
- **If DistilBERT fails to download/load at startup** (no network,
  Hugging Face Hub unreachable, etc.), the application still starts
  normally — only `/analyze-event` and `/generate-conversation` (which
  depends on theme extraction too) return a `503 Service Unavailable`
  with a friendly message. Auth, profile, history, feedback, and
  fact-checking are unaffected. **If the Gemini API call itself fails**
  (missing/invalid `GEMINI_API_KEY`, rate limit, the model being
  temporarily overloaded, network issues), only `/generate-conversation`
  returns a `503` — theme extraction and everything else keeps working.
  Either way, the real underlying error is logged server-side (see the
  backend's console output) for debugging, never shown to the client.
- `SECRET_KEY` defaults to an obviously-insecure placeholder for local
  development. Always override it (via `.env` or your shell environment)
  before running anywhere that isn't your own machine.
- **If you ran an earlier version of this project before**, delete your
  local `data/app.db` file before starting the backend again. There's no
  migration tooling (e.g. Alembic) set up yet, so the profile and
  tone/confidence-score columns added to the database won't exist on an
  old database file — `init_db()` only creates missing tables, it doesn't
  alter existing ones. Deleting the file lets it be recreated fresh with
  the current schema.
