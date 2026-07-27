"""Backfill board-game purchase prices from the SharePoint CSV export.

    python -m rbga.db.import_prices <csv-path> [--dry-run] [--overwrite]
    ... | python -m rbga.db.import_prices -          # read the CSV from stdin

The original inventory import (rbga/db/import_boardgames.py) left out the price
column, so board_games.price is unset. A fresh export adds a "Purchase Value"
column; this fills it in.

Rows are matched to existing games by **normalized title**, not BGG link: the
export has two mislinked rows (Exploding Kittens carries Heat's link, The Mind
carries Uno's), so bgg_link is an unreliable key. Title is clean — the only
repeated title (Polyhedral Dice Set x4) shares one price.

Fill-only by default: a price already set (e.g. by an exec via /game edit) is
left untouched. Pass --overwrite to replace existing prices too. --dry-run
reports what would change without writing.

Prices and titles are already public (they ride the /board-games API), so the
summary prints them freely. Pipe over SSH into the prod container:

    ssh <box> "cd ~/servers/rbga && docker compose run --rm -T api \
        python -m rbga.db.import_prices - --dry-run" < "Board Games.csv"
"""
import argparse
import csv
import sys

from sqlalchemy import select

from .database import SessionLocal
from .models import BoardGame


def _norm_title(title: str) -> str:
    """Collapse whitespace and lowercase, so a trailing space or double space
    in either the CSV or the DB doesn't defeat the match."""
    return " ".join(title.split()).lower()


def _parse_price(raw: str) -> float:
    """'22.95' / '50' -> float. Raises ValueError on junk or a negative
    (mirrors the bot's parse_money guard)."""
    val = float(raw.strip().lstrip("$"))
    if val < 0:
        raise ValueError(f"'{raw.strip()}' is negative")
    return val


def parse_prices(lines: list[str]) -> tuple[dict[str, float], list[str]]:
    """(normalized-title -> price, conflicts) from the CSV text. A title seen
    with two different prices is dropped and named in `conflicts`; blank names
    or prices are skipped."""
    # A surviving UTF-8 BOM would corrupt the first header name.
    if lines and lines[0].startswith("﻿"):
        lines = [lines[0].lstrip("﻿"), *lines[1:]]
    # Some exports lead with a SharePoint `ListSchema=...` metadata blob; drop it.
    if lines and lines[0].startswith("ListSchema="):
        lines = lines[1:]

    prices: dict[str, float] = {}
    conflicts: list[str] = []
    reader = csv.DictReader(lines)
    for row in reader:
        name = (row.get("Name") or "").strip()
        raw = (row.get("Purchase Value") or "").strip()
        if not name or not raw:
            continue
        try:
            price = _parse_price(raw)
        except ValueError:
            continue  # non-numeric price cell; nothing to migrate from it
        key = _norm_title(name)
        if key in prices and prices[key] != price:
            if name not in conflicts:
                conflicts.append(name)
            del prices[key]  # ambiguous: don't guess which price is right
            continue
        prices[key] = price
    return prices, conflicts


def apply_prices(
    prices: dict[str, float], *, overwrite: bool = False, dry_run: bool = False
) -> dict:
    """Set price on games matched by normalized title. Fill-only unless
    `overwrite`. Returns a stats dict with counts and the unmatched lists."""
    filled: list[str] = []
    skipped_set: list[str] = []  # matched but already priced (fill-only)
    unmatched_db: list[str] = []  # DB games with no CSV price
    matched_keys: set[str] = set()

    with SessionLocal() as db:
        games = db.scalars(select(BoardGame)).all()
        for g in games:
            key = _norm_title(g.title)
            if key not in prices:
                unmatched_db.append(g.title)
                continue
            matched_keys.add(key)
            if g.price is not None and not overwrite:
                skipped_set.append(g.title)
                continue
            g.price = prices[key]
            filled.append(g.title)
        if not dry_run:
            db.commit()

    unmatched_csv = sorted(k for k in prices if k not in matched_keys)
    return {
        "total_games": len(games),
        "csv_prices": len(prices),
        "filled": filled,
        "skipped_already_set": skipped_set,
        "unmatched_db": unmatched_db,
        "unmatched_csv": unmatched_csv,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Backfill board-game purchase prices from the SharePoint CSV export."
    )
    parser.add_argument("csv_path", help="Path to the CSV, or - to read stdin")
    parser.add_argument(
        "--dry-run", action="store_true", help="Report what would change without writing."
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace prices that are already set (default: fill only empty ones).",
    )
    args = parser.parse_args(argv)

    if args.csv_path == "-":
        # Decode ourselves: the export carries a UTF-8 BOM, and text-mode stdin
        # would decode with the locale codepage and mangle the first header name.
        lines = sys.stdin.buffer.read().decode("utf-8-sig").splitlines(keepends=True)
    else:
        with open(args.csv_path, encoding="utf-8-sig", newline="") as fh:
            lines = fh.readlines()

    prices, conflicts = parse_prices(lines)
    if not prices:
        print("No priced rows found in the CSV; nothing to migrate.")
        return 1

    stats = apply_prices(prices, overwrite=args.overwrite, dry_run=args.dry_run)

    tag = "[dry-run] would fill" if args.dry_run else "Filled"
    print(
        f"{tag} {len(stats['filled'])} of {stats['total_games']} games "
        f"from {stats['csv_prices']} CSV prices "
        f"({len(stats['skipped_already_set'])} already priced, left as-is)."
    )
    if conflicts:
        print(f"\nSkipped {len(conflicts)} title(s) with conflicting prices in the CSV:")
        for name in conflicts:
            print(f"  {name}")
    if stats["unmatched_db"]:
        print(f"\n{len(stats['unmatched_db'])} game(s) had no matching CSV price:")
        for title in stats["unmatched_db"]:
            print(f"  {title}")
    if stats["unmatched_csv"]:
        print(f"\n{len(stats['unmatched_csv'])} CSV price(s) matched no game:")
        for key in stats["unmatched_csv"]:
            print(f"  {key}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
