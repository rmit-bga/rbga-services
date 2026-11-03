# RBGA Discord Bot: Exec Guide

How to use the club's Discord bot. This is for the executive team: what each
command does, who can use it, and the quirks worth knowing before you rely on it.

## Who can do what

- **Everyone** can browse the game library and submit a complaint.
- **Execs** (anyone holding the exec Discord role; the role name is set by the
  server admin in the bot's config, `DISCORD_KEYS_ROLE`) get everything else:
  the whole key tracker, add/edit/remove games, stocktakes, and owner
  contacts. If you don't have the role, the bot replies "You need the … role to
  do that."
- **Complaints setup** (`/complaints-setup`) is tighter still: the server owner,
  or holders of a dedicated admin role if one is configured (it defaults to the
  same exec role).

Mutation replies are **ephemeral** (only you see them), so running exec commands
in a busy channel doesn't spam anyone.

---

## Keys (cabinet key tracker)

The entire key tracker is **exec only**, including the reads: who holds a
cabinet key isn't something members need to see.

| Command | What it does |
|---|---|
| `/keys` | List every registered key, its campus, and who holds it |
| `/whohas colour:` | Who currently holds a specific key |
| `/take colour: [holder:]` | Record that a key was taken. `holder` defaults to **you**; name someone else if you're logging it for them |
| `/return colour:` | Hand a key back (clears the holder) |
| `/addkey colour: campus:` | Register a new key |
| `/removekey colour:` | Delete a key entirely (not the same as returning it!) |

The `colour` field autocompletes from the keys that exist, so start typing and
pick from the list.

---

## Board games (inventory)

### Browsing (everyone)

| Command | What it does |
|---|---|
| `/game list` | Browse the inventory, paged with Prev/Next. A **🖼 Gallery / 📝 Text** button flips between the compact text list and image cards (10 per page; nicer for showing members what we have) |
| `/game info game:` | Full details for one game (price, condition, players, notes, photo) |

`/game list` takes optional filters: `owner`, `condition`, `search`, `tag`,
`location`, a `sort` field (Title, ID, Owner, or Condition; Title by default),
and a `direction` (Ascending or Descending).
`search` matches a game's title, publisher, owner, notes, or tags. The header
echoes back whatever filters are in effect, e.g.
`/game list owner:RBGA condition:Fair` shows **… · owner: RBGA · [Fair]**.

When picking a game (in `/game info`, `edit`, `remove`), start typing the title
and choose from the autocomplete; entries show as `#id Title` because we own
duplicate copies of some titles.

### Managing (exec only)

| Command | What it does |
|---|---|
| `/game add` | Add a game. **Run it with no options to get a quick form.** Paste a BoardGameGeek link and it auto-fills the title, publisher, player count, image, and tags |
| `/game edit game:` | Edit a game. **Pick just the game to get a pre-filled form**, or set individual options. Giving a new `bgg_link` re-fetches the BGG details |
| `/game remove game:` | Delete a game from the inventory |
| `/game stocktake` | Walk the shelf: the bot shows one game at a time and you press **Seen ✔ / Missing ✖ / Skip ▶** |
| `/game export` | The whole inventory as a CSV file (opens fine in Excel; includes prices and owners, hence exec-only). Takes the same filters as `/game list` |

Notes on these:

- **Editing can't blank a field.** Leaving an option (or a form field) empty
  means "leave it unchanged", not "clear it".
- **Sell price**: if you don't set one, the bot shows an *estimate* based on
  purchase price × condition (e.g. Like New ≈ 70%, Fair ≈ 40%). Set `sell_price`
  to override it with a real asking price.
- **Stocktake** is resumable and shareable: it defaults to only games not yet
  sighted today, any exec can press the buttons, and if it times out (15 min)
  progress is saved; just run `/game stocktake` again. Missing games show ⚠ in
  `/game list`.
- **BGG auto-fill** needs an API token configured on the server
  (`BGG_API_TOKEN`). If lookups fail with a "not set up yet" message, that's
  why. Add games manually with a title in the meantime.

### Owner contacts (exec only)

Games donated or lent by members have an `owner`. These commands keep a private
contact list so we can reach them (it's never shown publicly or via the website):

| Command | What it does |
|---|---|
| `/owner set name: contact:` | Save how to reach an owner (Discord handle, email, phone) |
| `/owner info name:` | Look up an owner's contact |
| `/owner list` | All saved contacts |

The bot also nudges you automatically: add a game for a brand-new owner and it
offers an "Add contact" button; remove/reassign an owner's last game and it asks
whether to drop their saved contact.

---

## Complaints

Read `docs/complaints-policy.md` before handling complaints; this section is
just the mechanics.

### Submitting (everyone)

Run `/complain about:` and choose who it's about (a member / the committee / an exec /
the president). The bot shows the anonymity promises and disclosures, then a
**Continue** button opens the form (what happened + optional contact).

- Submission is **anonymous**: the bot forwards only the text, never your
  Discord identity. Leaving the contact field blank keeps you fully anonymous.
- Complaints **about the president** aren't taken into the club's system at
  all; the command replies with RUSU / RMIT Safer Community links instead.

### Handling (whoever the notification reaches)

New complaints are routed by tier: about a **member** → committee channel,
about the **committee** → exec channel, about an **exec** → president's DM. The
notification shows **metadata only** (id, category, status) with three buttons:

- **View**: fetches the complaint body and shows it *only to you*
  (ephemerally). The text never sits in a channel.
- **Acknowledge**: marks it as being handled (the card updates for everyone).
- **Close**: asks for confirmation first, because closing is **final**. The
  buttons disappear and nobody can view the body again. Only close a complaint
  once it's genuinely resolved.

Closed complaints are purged automatically after the retention period
(currently one year boundary; see the policy §8).

### Setup (server owner / admin role)

`/complaints-setup` opens a private panel to pick the committee channel, exec
channel, and president. Run it once after a fresh deploy (or when handover
changes who the president is); no restart or config file is needed. Until a tier
is configured, `/complain` for that tier tells the submitter setup isn't done
yet.

---

## Quirks and troubleshooting

- **"This interaction failed" immediately**: the bot was probably mid-restart
  (each deploy takes it offline for ~30s-2min). Wait a moment and retry; it
  almost always works the second time.
- **Buttons stop responding on an old message**: the `/game list` pager (Prev/
  Next and the Gallery/Text toggle) and stocktake are deliberately short-lived
  (5-15 min). Just run the command again. Complaint buttons are the exception:
  they survive restarts and keep working.
- **"You need the … role to do that"**: you're missing the exec role; ask a
  server admin to grant it.
- **Nothing autocompletes**: autocomplete pulls from live data, so an empty
  database suggests nothing. You can still type values manually.
