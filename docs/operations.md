# Operations runbook

Day-to-day running of the production stack: how to deploy, roll back, read
logs, recover from common failures, and back up and restore the database.
`docs/deploy.md` covers building a host from scratch. Credentials (the SSH key,
the `.env` values) are **not** in this repo; they are handed over separately
(see `docs/handover.md`).

All commands below run on the production VM, in the stack directory, unless
stated otherwise:

```bash
ssh -i <your-key> opc@rmitbga.duckdns.org
cd ~/servers/rbga
```

## Is it up?

```bash
curl https://rmitbga.duckdns.org/health        # from anywhere: {"status":"ok"}
docker ps --format '{{.Names}}  {{.Status}}'    # on the VM: rbga-db, rbga-api, rbga-bot, rbga-caddy
```

In Discord, `/game list` should answer within a few seconds.

## Deploying a change

You don't deploy by hand. **Merge a PR into `main`** and GitHub Actions does
the rest (`.github/workflows/ci-cd.yml`):

1. `test`: runs the test suite. A failing test stops the deploy.
2. `build`: builds the Docker image on GitHub's machines and pushes it to
   `ghcr.io/rmit-bga/rbga-services` (tagged `latest` and the commit SHA).
3. `deploy`: on the VM's self-hosted runner, pulls the new image, runs
   database migrations, restarts the containers, and checks `/health`.

Watch progress in the repo's **Actions** tab. Each deploy restarts the bot, so
Discord commands fail for about 30 seconds to 2 minutes ("This interaction
failed"). That is expected; retry once it has reconnected.

**Never build the image on the VM** (`docker compose up --build` or
`docker build`). The VM has about 1 GB of RAM, and a build can freeze the whole
machine. That is why builds happen in CI.

## Rolling back

Every deploy is tagged with its commit SHA. To go back to a known-good version:

```bash
# Pick the SHA of the last good commit from the GitHub commit list, then:
echo 'RBGA_IMAGE_TAG=<full-sha>' >> .env
docker compose pull api bot
docker compose --profile caddy up -d
```

Fix the problem on `main`, then **delete the `RBGA_IMAGE_TAG` line** from
`.env`, or later deploys will keep running the pinned old version.

A rollback does not undo database migrations. If the bad change included a
migration, check `migrations/versions/` for its `downgrade()` before rolling
back, and take a backup first (below).

## Logs

```bash
docker logs --tail 100 rbga-api
docker logs --tail 100 -f rbga-bot      # -f follows live; Ctrl+C to stop
docker logs --tail 50 rbga-caddy        # HTTPS / certificate problems
```

Logs are size-capped by `compose.yml`, so old lines roll off on their own. The
API deliberately logs nothing that could identify a complaint submitter; keep
it that way when adding logging.

## Restarting things

```bash
docker compose restart bot              # just the bot
docker compose --profile caddy up -d    # bring everything to the declared state
```

Always include `--profile caddy` on `up`. Without it, Caddy (and so public
HTTPS) is left out.

## Common problems

| Symptom | Likely cause | Fix |
|---|---|---|
| "This interaction failed" right after a merge | Bot restarting during a deploy | Wait 2 minutes and retry |
| Bot offline for a long time | Bot crashed, or Discord token reset | `docker logs rbga-bot`; a login error means the token in `.env` is wrong |
| `permission denied for table ...` in bot logs | A table the bot role can't read | See "Bot DB role" in `docs/deploy.md` |
| `/health` fails but containers are up | Caddy can't get or renew a certificate | `docker logs rbga-caddy`; check DuckDNS still points at the VM and ports 80/443 are open |
| SSH hangs, website down, OCI says "Running" | VM out of memory and thrashing | Reboot from the OCI console (below) |
| Deploy job stuck in "Queued" | Self-hosted runner is down or unregistered | See "Deploy runner" below |

## Deploy runner

Deploys run on a GitHub Actions runner installed on the VM (`~/actions-runner`,
a systemd service running as `opc`). If it's down, merges to `main` pass CI but
the deploy job sits in "Queued" forever, and nothing visibly breaks. Check it
after every merge, and every few months anyway:

```bash
systemctl list-units --all 'actions.runner*'    # want: active running
tail -5 "$(ls -t ~/actions-runner/_diag/Runner_*.log | head -1)"
```

If the service is just stopped, `sudo systemctl restart 'actions.runner.*'`.

If the log says **"The runner no longer exists on the server"**, GitHub has
deleted the registration (this happened in September 2026). The runner wipes
its own config when that happens, so register it again:

1. Logged in as `rmit-bga`: repo Settings → Actions → Runners → **New
   self-hosted runner** → Linux. Copy the token from the `config.sh` line (it
   expires in an hour).
2. On the VM:
   ```bash
   cd ~/actions-runner
   sudo ./svc.sh uninstall          # remove the old service
   ./config.sh --url https://github.com/rmit-bga/rbga-services --token <TOKEN> \
     --name rbga-oracle --labels oracle --unattended
   sudo restorecon -Rv ~/actions-runner   # SELinux: keep the runner binaries executable
   sudo ./svc.sh install opc
   sudo ./svc.sh start
   ```
3. Confirm it shows **Idle** in Settings → Actions → Runners, then re-run the
   last failed or queued deploy from the Actions tab.

The `oracle` label matters: the deploy job targets `[self-hosted, oracle]`.

## If the VM freezes

The VM once froze because a background package-cache job (`dnf-makecache`) used
up all its memory. That timer is now disabled, every container has a hard
memory cap, and `earlyoom` kills the biggest process before the machine locks
up. If it freezes anyway:

1. Oracle Cloud console → Compute → Instances → the instance → **Reboot**.
2. The graceful reboot will hang because the OS can't respond. Oracle
   force-restarts it after about 15 minutes.
3. **Never choose Terminate.** That deletes the VM and its disk, including the
   database.

Don't re-enable `dnf-makecache.timer`.

## Backups and restore

`scripts/backup-db.sh` dumps the whole database to `~/backups/rbga/` and keeps
14 days of dumps. Install it once with `crontab -e` as `opc`:

```cron
30 2 * * * ~/servers/rbga/scripts/backup-db.sh >> ~/servers/rbga/backup.log 2>&1
```

It runs before the 3 am complaints purge. Check it with `tail ~/servers/rbga/backup.log`.

**These backups live on the same VM.** They cover a bad migration, an
accidental delete or a corrupted database, but not losing the VM itself (for
example, Oracle reclaiming an idle free-tier instance, or someone pressing
Terminate). Every so often, and before any risky change, copy the newest dump
off the box:

```bash
# from your own computer
scp -i <your-key> "opc@rmitbga.duckdns.org:backups/rbga/$(ssh -i <your-key> opc@rmitbga.duckdns.org 'ls -t backups/rbga | head -1')" .
```

Dumps contain complaints, so store any off-box copy somewhere access-controlled
and delete old copies. A dump can hold complaints that the retention purge has
since deleted.

### Restoring

```bash
docker compose stop api bot
docker compose exec -T db sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists' \
  < ~/backups/rbga/rbga-<timestamp>.dump
docker compose --profile caddy up -d
```

On a **fresh** database (a rebuilt VM), first create the `rbga_bot` role
(`docs/deploy.md`, "Bot DB role"), because roles are not stored in the dump.
Then restore and run the default-privileges SQL from the same section.

## Rotating a credential

The full list of credentials, and what each one protects, is in the handover
secrets document. The general pattern:

1. Generate a new value. For API tokens: `openssl rand -hex 32`.
2. Edit `~/servers/rbga/.env`.
3. `docker compose --profile caddy up -d` (containers pick up the new value
   when recreated).
4. Check `/health`, `/keys` in Discord, and that `/complaints-setup` opens.

Rotating `COMPLAINTS_API_TOKEN` doesn't lose complaints. New ones are still
accepted; the bot just can't route them until it restarts with the new token.

## Database migrations

Schema changes go through Alembic (`migrations/versions/`). The deploy job runs
`alembic upgrade head` automatically before restarting services, so a merged
migration applies itself. To add one, see the "Migrations" section of the
README. Take a backup before merging anything that drops or rewrites data.

## Free-tier caveats

- The VM is an Oracle **Always Free** `E2.1.Micro` (1 GB RAM). Oracle can
  reclaim Always Free instances it considers idle. If the club ever receives an
  idle-reclamation email, act on it promptly. Upgrading the account to
  Pay-As-You-Go stops reclamation and still bills nothing while usage stays
  inside the free allowances.
- The domain is a free DuckDNS name. It points at a reserved IP, so it
  shouldn't change, but if the VM is ever rebuilt with a new IP, update it in
  DuckDNS.
