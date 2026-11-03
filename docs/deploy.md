# Deploy notes

Operational reference for whoever runs the stack. Host-specific details (addresses,
credentials) live outside the repo; keep them in the deploy host's own notes,
never here.

## Pattern

One compose stack per host, in a dedicated directory (e.g. `~/servers/rbga/`):

1. Clone (or let CI bootstrap) the repo into the deploy directory.
2. `cp .env.example .env` and fill it in. `.env` is gitignored; never commit it.
3. `docker compose pull && docker compose --profile caddy up -d` (drop
   `--profile caddy` on a host that uses a Cloudflare tunnel instead). This
   pulls the CI-built image from GHCR. Don't use `--build` on a small VM: a
   Docker build can exhaust its memory and freeze it.
4. Install the cron jobs: the complaints purge and the database backup (both
   below).

Pushes to `main` auto-deploy via `.github/workflows/ci-cd.yml`: the tests run,
a hosted runner builds the image and pushes it to GHCR, then a **self-hosted
runner on the box** resets the deploy checkout to `origin/main`, pulls the
image, runs `alembic upgrade head`, and restarts the stack. The
API publishes on host port `30010`; the DB has no host port; the bot needs none.

## Public HTTPS

Two options, pick per host:

- **Cloudflare tunnel (no public IP needed).** Add an ingress rule for the API
  hostname pointing at `http://localhost:30010` in the host's cloudflared config,
  route the DNS, restart cloudflared.
- **Caddy compose profile (host with a public IP + domain).** Point a DNS name
  (a free DuckDNS name works) at the host, set `CADDY_DOMAIN`, open 80/443 (on
  Oracle: the OCI security list **and** the instance firewall), then
  `docker compose --profile caddy up -d`.

Either way, set `CORS_ALLOW_ORIGINS` to the front-end origin(s) that call the API
(the GitHub Pages site).

## Bot DB role (complaints isolation, policy §9)

The bot connects with its own least-privilege Postgres role that has **no access
to the complaints schema**, so a leak of the bot credentials can't reach
complaints. Create it once per database, as the postgres superuser:

```sql
CREATE ROLE rbga_bot LOGIN PASSWORD '<generated>';
GRANT USAGE ON SCHEMA public TO rbga_bot;
GRANT SELECT, INSERT, UPDATE, DELETE ON keys, board_games, owners TO rbga_bot;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO rbga_bot;
REVOKE ALL ON SCHEMA complaints FROM rbga_bot, PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA complaints FROM rbga_bot, PUBLIC;
```

Table grants only cover tables that exist when they run; so that tables added
by future migrations are granted automatically, also run — **as the role that
runs migrations** (the `DATABASE_URL` user, not the superuser, because default
privileges apply to objects created by the role that sets them):

```sql
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO rbga_bot;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO rbga_bot;
```

(Migration `0011` applies both of these on existing deployments. Complaints
isolation is unaffected: it is the schema-level REVOKE above, and these
defaults are scoped to `public`.)

Then set `BOT_DATABASE_URL` to that role's connection string.

## Complaints retention purge

Run the purge on a schedule (see `rbga/db/purge_complaints.py` and policy §8).
Cron on the deploy host:

```bash
0 3 * * * cd ~/servers/rbga && docker compose run --rm api python -m rbga.db.purge_complaints >> ~/servers/rbga/purge.log 2>&1
```

The cron is deliberately daily even though deletion happens at the turn of the
calendar year: the purge is idempotent (it deletes complaints closed in a
previous year, so most runs delete nothing) and a daily schedule self-heals if
the box is down on 1 January.

`COMPLAINTS_RETENTION_YEARS` (currently 1, i.e. a closed complaint is deleted
at the first new year after it closes) is the exec's number; change it by
editing the one env var.

## Database backup

`scripts/backup-db.sh` writes a nightly `pg_dump` to `~/backups/rbga/` and keeps
14 days. Cron on the deploy host, scheduled before the 3 am purge:

```bash
30 2 * * * ~/servers/rbga/scripts/backup-db.sh >> ~/servers/rbga/backup.log 2>&1
```

Restoring, and copying dumps off the box: `docs/operations.md`.
