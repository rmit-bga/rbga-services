# RBGA Services

Services for the RMIT Board Game Association, built as **one small app, not a
pile of microservices**: the club's tools are low-volume and maintained by
rotating student execs, so handover beats scaling. Everything lives in the
`rbga` Python package and shares one Postgres database:

| Feature | Where | Notes |
|---------|-------|-------|
| Key tracker | `rbga/api/routers/keys.py`, `rbga/bot/__main__.py` | Ported from Owen's [RBGAKeyTracker](https://github.com/Scroojalix/RBGAKeyTracker). Full CRUD over REST *and* Discord. |
| Board-game inventory | `rbga/api/routers/boardgames.py`, `rbga/bot/boardgames.py` | REST + Discord CRUD. Seed from a CSV with `rbga/db/import_boardgames.py`. |
| Anonymous complaints | `rbga/api/routers/complaints.py`, `rbga/bot/complaints.py` | Submitted via `/complain` in Discord or `POST /complaints`; routed to handlers in Discord. Stores nothing identifying. See "Complaints rules" below. |
| Discord bot | `rbga/bot/` | Keys (`/keys`, `/whohas`, `/take`, `/return`, `/addkey`, `/removekey`), board games (`/game ...`, `/owner ...`), complaints (`/complain`, `/complaints-setup`). Full list: `docs/bot-guide.md`. |

**New maintainer? Start with [`docs/handover.md`](docs/handover.md).**

## Two processes, one image

- **API** (FastAPI, HTTP): `uvicorn rbga.api.main:app`
- **Bot** (discord.py, long-running gateway connection): `python -m rbga.bot`

They're separate processes because their runtimes differ, but they build from the
same Dockerfile and import the same `rbga/db` layer. Adding a *feature* means
adding a module, not a new service.

## Local dev (SQLite, no Postgres needed)

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
uvicorn rbga.api.main:app --reload                  # http://localhost:8000/docs
```

With no `DATABASE_URL` set it uses a local `rbga_dev.db` SQLite file and
auto-creates the tables, so the API runs with zero setup. Interactive docs at
`/docs`.

To run the bot locally, set `DISCORD_TOKEN` (see `.env.example`) then
`python -m rbga.bot`. Bot reads (`/keys`, `/game list`, …) are open to everyone;
mutations are gated to the exec role named by `DISCORD_KEYS_ROLE` (fail-closed: no
role configured means no mutations).

### Seeding the board-game inventory

```bash
python -m rbga.db.import_boardgames "path/to/Board Games.csv" [--replace]
```

Skips the SharePoint `ListSchema` header, trims titles, treats blanks as NULL, and
refuses to run against a non-empty table unless `--replace`.

## Full stack (Postgres + api + bot)

```bash
cp .env.example .env   # fill in values
docker compose up -d --build
```

## Layout

```
rbga/
  db/       models.py + database.py     (one schema of truth, shared)
            import_boardgames.py        (CSV seed for the inventory)
  api/      main.py + routers/          (FastAPI: keys, boardgames, complaints)
  bot/      __main__.py + common.py     (discord.py; `python -m rbga.bot`)
            boardgames.py               (the /game and /owner command groups)
            complaints.py               (/complain, routing, handler buttons)
migrations/                             (Alembic schema history)
scripts/backup-db.sh                    (nightly Postgres dump, run by cron)
docs/                                   (handover, operations, deploy, policy, guides)
tests/                                  (pytest; run before every deploy)
compose.yml  Dockerfile  pyproject.toml
.github/workflows/ci-cd.yml            (test + build + auto-deploy to production)
```

## Tests

```bash
pip install -e ".[dev]"
pytest -q
```

CI runs the suite on every PR and before every deploy; a failing test blocks
the deploy.

## Deploy

Production is an Oracle Cloud VM. **Merging to `main` deploys**: CI runs the
tests, builds the image and pushes it to GHCR, then a self-hosted runner on the
VM pulls it, runs `alembic upgrade head`, restarts the stack and health-checks
it. The VM never builds images (it has 1 GB of RAM). Running it day to day:
[`docs/operations.md`](docs/operations.md). Building a host from scratch:
[`docs/deploy.md`](docs/deploy.md).

## Migrations

Schema is managed by **Alembic** (`migrations/`). The API runs `alembic upgrade
head` on startup (so local `uvicorn` stays zero-setup), and the deploy runs it too
before services start. Add a migration with
`alembic revision -m "..."` (autogenerate against `Base.metadata`), then
`alembic upgrade head`.

## Complaints rules

Complaints are the one piece of sensitive data here. The member-facing promises
are in [`docs/complaints-policy.md`](docs/complaints-policy.md); these are the
rules the code keeps them with. Don't break them:

- **Store and log nothing identifying.** A complaint is only `created_at`,
  `category`, `body`, and an optional `contact` the submitter chose to give. No
  IP, user agent, or Discord user. `/complain` forwards the text but never
  `interaction.user`.
- **Reading is separate from submitting.** `GET`/`PATCH /complaints` need the
  `COMPLAINTS_API_TOKEN` reviewer token, a different credential from
  `RBGA_API_TOKEN`. Every auth check fails closed: no token configured means no
  access.
- **The public submit is throttled.** The rate limiter keys on a salted hash of
  the IP, held only in memory (`rbga/api/ratelimit.py`), never the raw IP.
- **The bot has no complaints DB access.** It connects as the `rbga_bot` role,
  which can't see the `complaints` schema, and reaches complaints only through
  the API. Discord notifications carry metadata only; the body is shown
  ephemerally on the *View* button.
- **Closed complaints are purged** by `python -m rbga.db.purge_complaints`
  (daily cron), per policy §8.

## Not done yet

- **Web complaints form.** `POST /complaints`, CORS and rate limiting are ready;
  the form itself belongs in the **rmit-bga/website** repo and must show the
  policy §3 text. Members can already complain in Discord with `/complain`.
- **BGG auto-fill needs a token.** `/game add` can pull details from a BGG link,
  but BGG now requires a registered-app Bearer token, so set `BGG_API_TOKEN` (see
  `.env.example`) to enable it.
- **Instagram announcement mirror.** On the `instagram-story-mirror` branch, not
  yet merged.
