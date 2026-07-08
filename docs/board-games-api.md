# Board-games inventory API — front-end handover

How to consume the RBGA board-games inventory from the club website. Written for
whoever builds the games-library section of the landing page (the `website`
repo, deployed to GitHub Pages at `https://rmit-bga.github.io/website/`).

The API is part of [rmit-bga/rbga-services](https://github.com/rmit-bga/rbga-services)
(FastAPI; source: `rbga/api/routers/boardgames.py`). Interactive OpenAPI docs
live at `<base>/docs`.

## Base URL

| Environment | Base URL |
|---|---|
| Production | `https://rmitbga.duckdns.org` |
| Local dev of the API itself | `http://localhost:8000` (`uvicorn rbga.api.main:app --reload`) |

Health check: `GET /health` → `{"status": "ok"}`.

**CORS is already configured** for the GitHub Pages origin
`https://rmit-bga.github.io` — a plain `fetch()` from the deployed site works
today. If the site ever moves to a different origin, `CORS_ALLOW_ORIGINS` in the
API's `.env` (on the Oracle VM) must be updated to match; until then requests
from that new origin will be blocked by the browser.

## Endpoints for the front-end

Both are public — no auth, no API key.

### `GET /board-games`

The full inventory as a single JSON array, sorted by title. Currently ~174
games; there is **no pagination** and no search parameter, so fetch once and
filter/search client-side.

One optional query parameter:

- `?tag=<name>` — case-insensitive **exact** tag match, e.g.
  `/board-games?tag=card%20game` (74 results today). Tags are free-form labels
  auto-filled from BoardGameGeek categories: "Card Game", "Bluffing",
  "Abstract Strategy", "Party Game", etc. There is no endpoint listing all
  tags — derive the tag set from the full response if you want a filter UI.

### `GET /board-games/{id}`

A single game. Unknown id → `404` with body `{"detail": "No such board game"}`.

### Do not use: `POST` / `DELETE /board-games`

These exist but are admin operations gated by an `X-API-Token` header the
front-end will never hold. Inventory management happens through the club's
Discord bot (`/game` commands) — don't build any write UI against the API.

## Response schema

Every field except `id`, `title`, and `missing` can be `null` — code
defensively.

| Field | Type | Notes |
|---|---|---|
| `id` | int | Stable identifier. |
| `title` | string | Always present. |
| `publisher` | string \| null | |
| `min_players` | int \| null | |
| `max_players` | int \| null | |
| `location` | string \| null | Where the box physically lives (club storage). |
| `notes` | string \| null | Free-form. |
| `owner` | string \| null | Display name only (often `"RBGA"`). Owner *contact* details deliberately have no public endpoint — do not request one. |
| `condition` | string \| null | Free-form, e.g. `"Like New"`. |
| `bgg_link` | string \| null | BoardGameGeek page URL. |
| `image` | string \| null | **Caution:** a real URL for BGG-imported games, but a bare filename (no scheme) for legacy CSV imports. Only use it if it starts with `http`; otherwise show a fallback tile. |
| `thumbnail` | string \| null | BGG's small image variant. **Prefer this in card grids** — the full `image` is often a multi-MB original. |
| `price` | number \| null | Internal purchase-value field; fine to ignore on the public page. |
| `sell_price` | number \| null | Internal asking-price field; fine to ignore on the public page. |
| `tags` | string[] \| null | Free-form labels (see `?tag=` above). |
| `last_seen_at` | ISO datetime \| null | Stocktake: when the game was last physically sighted. |
| `missing` | bool | Stocktake: the last stocktake couldn't find it. Consider hiding these games or badging them "missing". |

### Sample record (real, from production)

```json
{
  "id": 50,
  "title": "6 nimmt! 25 Jahre",
  "publisher": "AMIGO",
  "min_players": 2,
  "max_players": 10,
  "location": null,
  "notes": null,
  "owner": "RBGA",
  "condition": "Like New",
  "bgg_link": "https://boardgamegeek.com/boardgame/268586/6-nimmt-25-jahre",
  "image": "https://cf.geekdo-images.com/DFeZsC973xdZ1CKUzmjAUw__original/img/Tq8bVKV-ihLPfFPpf8FjfTpXiZk=/0x0/filters:format(jpeg)/pic4496538.jpg",
  "thumbnail": "https://cf.geekdo-images.com/DFeZsC973xdZ1CKUzmjAUw__small/img/TTIPiPwQpowcHjYMxtk920ZwR3c=/fit-in/200x150/filters:strip_icc()/pic4496538.jpg",
  "price": null,
  "sell_price": null,
  "tags": ["Card Game", "Number"],
  "last_seen_at": "2026-07-07T11:42:58.667629",
  "missing": false
}
```

## Practical guidance

- **Fetch once, filter client-side.** The whole inventory is one small array;
  a search box and tag filter should operate on the in-memory list, not
  re-query the API.
- **Handle fetch failure gracefully.** The API runs on a small free-tier VM and
  is briefly offline (~30s–2min) during each deploy. Show a friendly
  "couldn't load the library" state rather than a blank section.
- **Images are third-party.** `image`/`thumbnail` point at BoardGameGeek's CDN;
  use `loading="lazy"` and an `onerror` fallback tile.
