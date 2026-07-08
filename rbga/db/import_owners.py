"""Import owner contact details from the club's Owner.csv export.

    python -m rbga.db.import_owners <csv-path>
    ... | python -m rbga.db.import_owners -          # read the CSV from stdin

Expected header: "First Name/s","Last Name","Phone Number","Email","ID".
The games label owners by first name (BoardGame.owner holds e.g. "Zac",
"Quan", "RBGA"), so **First Name/s becomes Owner.name** and the rest is
folded into the free-text contact: "Last-name'd full name, phone, email"
with missing pieces omitted. Rows with nothing beyond the name (e.g. the
RBGA club row) are skipped — there is no contact to record.

Upserts by name (the column is unique), so re-running is safe and refreshes
contacts rather than duplicating. The CSV itself must NEVER be committed
(personal data, public repo); pipe it over SSH instead:

    ssh <box> "cd ~/servers/rbga && docker compose run --rm -T api \
        python -m rbga.db.import_owners -" < Owner.csv

Prints only names and a count, never the contact details themselves.
"""
import argparse
import csv
import sys

from sqlalchemy import select

from .database import SessionLocal
from .models import Owner


def _clean(value: str | None) -> str | None:
    """Trim whitespace; treat empty strings as NULL."""
    if value is None:
        return None
    value = value.strip()
    return value or None


def parse_rows(lines: list[str]) -> list[tuple[str, str]]:
    """(name, contact) pairs from the CSV text; rows with no contact info
    beyond the name are dropped."""
    # Belt-and-braces: a surviving UTF-8 BOM would corrupt the first header name.
    if lines and lines[0].startswith("﻿"):
        lines = [lines[0].lstrip("﻿"), *lines[1:]]
    reader = csv.DictReader(lines)
    out: list[tuple[str, str]] = []
    for row in reader:
        name = _clean(row.get("First Name/s"))
        if not name:
            continue
        last = _clean(row.get("Last Name"))
        full_name = f"{name} {last}" if last else None
        parts = [full_name, _clean(row.get("Phone Number")), _clean(row.get("Email"))]
        contact = ", ".join(p for p in parts if p)
        if not contact:
            continue  # nothing to record (e.g. the RBGA club row)
        out.append((name, contact))
    return out


def upsert_owners(pairs: list[tuple[str, str]]) -> tuple[int, int]:
    """Insert or update each (name, contact); returns (created, updated)."""
    created = updated = 0
    with SessionLocal() as db:
        for name, contact in pairs:
            row = db.scalar(select(Owner).where(Owner.name == name))
            if row is None:
                db.add(Owner(name=name, contact=contact))
                created += 1
            else:
                row.contact = contact
                updated += 1
        db.commit()
    return created, updated


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import owner contacts from Owner.csv.")
    parser.add_argument("csv_path", help="Path to the CSV, or - to read stdin")
    args = parser.parse_args(argv)

    if args.csv_path == "-":
        # Read bytes and decode ourselves: the export carries a UTF-8 BOM, and
        # text-mode stdin decodes with the locale codepage (e.g. cp1252 on
        # Windows), which would mangle it into junk in the first header name.
        lines = sys.stdin.buffer.read().decode("utf-8-sig").splitlines(keepends=True)
    else:
        with open(args.csv_path, encoding="utf-8-sig", newline="") as fh:
            lines = fh.readlines()

    pairs = parse_rows(lines)
    if not pairs:
        print("No owner rows with contact details found; nothing to import.")
        return 1

    created, updated = upsert_owners(pairs)
    print(f"Imported {created + updated} owners ({created} new, {updated} updated):")
    for name, _ in pairs:
        print(f"  {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
