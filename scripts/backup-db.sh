#!/usr/bin/env bash
# Nightly Postgres backup for the RBGA stack. Run from cron on the deploy host:
#
#   30 2 * * * ~/servers/rbga/scripts/backup-db.sh >> ~/servers/rbga/backup.log 2>&1
#
# Writes a compressed custom-format dump (restore with pg_restore; see
# docs/operations.md "Backups and restore") and deletes dumps older than
# KEEP_DAYS. Uses the db container's own POSTGRES_USER/POSTGRES_DB, so it never
# reads .env and never handles a password.
#
# The dump includes the complaints schema. Backup files are created owner-only
# (umask 077), and KEEP_DAYS bounds how long a purged complaint can outlive the
# retention purge inside an old dump (complaints policy §8).
#
# This protects against a bad migration, an accidental delete or a corrupted
# volume. It does NOT protect against losing the whole VM; for that, copy the
# newest dump somewhere off the box (see docs/operations.md).
set -euo pipefail
umask 077

STACK_DIR="${STACK_DIR:-$HOME/servers/rbga}"
BACKUP_DIR="${BACKUP_DIR:-$HOME/backups/rbga}"
KEEP_DAYS="${KEEP_DAYS:-14}"

mkdir -p "$BACKUP_DIR"
cd "$STACK_DIR"

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
out="$BACKUP_DIR/rbga-$stamp.dump"

# Write to a temp name first so a failed dump never looks like a good backup.
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$out.partial"
mv "$out.partial" "$out"

find "$BACKUP_DIR" -name 'rbga-*.dump' -mtime +"$KEEP_DAYS" -delete
find "$BACKUP_DIR" -name 'rbga-*.dump.partial' -mtime +1 -delete

echo "$(date -u +%FT%TZ) backup ok: $(basename "$out") ($(du -h "$out" | cut -f1))"
