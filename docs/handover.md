# Handover: start here

If you've just inherited the RBGA tech, read this first. It explains what
exists, where it runs, who owns what, and what to do in your first week.

## What this is, in one paragraph

The club runs one small app with two parts. A **Discord bot** lets execs track
who holds the cabinet keys, manage the board-game library, and handle anonymous
complaints. A **web API** serves the game library to the club website and
accepts complaints. Both parts run as Docker containers on one free Oracle
Cloud VM. They share one Postgres database. Merging code into `main` on GitHub
deploys it automatically. Day to day, nothing needs a person: the system
deploys, renews its HTTPS certificate, purges old complaints and backs itself up.

## Map

| Thing | Where |
|---|---|
| Code | [github.com/rmit-bga/rbga-services](https://github.com/rmit-bga/rbga-services) (public) |
| Production server | Oracle Cloud VM, `rmitbga.duckdns.org`; stack in `~/servers/rbga` |
| Public API | `https://rmitbga.duckdns.org` (health check: `/health`, API docs: `/docs`) |
| Club website | [rmit-bga/website](https://github.com/rmit-bga/website) → `https://rmit-bga.github.io/website/` (calls the API for the game library) |
| Docker images | `ghcr.io/rmit-bga/rbga-services` (built by CI) |
| Credentials | Handover secrets document plus the club's password store. **Never in this repo** |

## Which document do I read?

| You want to... | Read |
|---|---|
| Use the bot as an exec | [`bot-guide.md`](bot-guide.md) |
| Keep production running, fix an outage, restore a backup | [`operations.md`](operations.md) |
| Rebuild the server from scratch | [`deploy.md`](deploy.md) |
| Understand the complaints rules (what we promise members) | [`complaints-policy.md`](complaints-policy.md) |
| Build something on the website that uses the game library | [`board-games-api.md`](board-games-api.md) |
| Change the code | [`../README.md`](../README.md) |

## Accounts the club must own

Every account below should be in the **club's** name and in the club's password
store, with **at least two current committee members** able to get in. If only
one person can log in to something, that's the next outage waiting to happen.

| Account | What breaks without it |
|---|---|
| GitHub `rmit-bga` (owns the repo, the image registry, and the DuckDNS login) | Can't change code, deploy, or fix DNS |
| Oracle Cloud tenancy `rbga` | Can't reach, reboot or rebuild the server |
| DuckDNS (signs in with the GitHub account above) | Can't repoint the domain |
| Discord Developer Portal app "RBGA Bot" | Can't reset the bot token or change its permissions |
| BoardGameGeek API registration | `/game add` loses BGG auto-fill (low impact) |

For the GitHub and Oracle logins, store the **2FA recovery codes** next to the
password. A lost phone otherwise locks the club out for good.

## Rules that keep it alive

These all come from real incidents or real risks. Don't relax them without
understanding why they exist.

- **Never build Docker images on the VM.** It has 1 GB of RAM; a build froze it
  once. CI builds; the VM only pulls.
- **Never run the bot in two places.** Two copies with the same token both
  answer every command. Production is the only place `DISCORD_TOKEN` is set.
- **Never press Terminate on the Oracle instance.** It deletes the database. If
  the VM is frozen, use Reboot (see `operations.md`).
- **Keep "require approval for fork PR workflows" on** (repo Settings → Actions).
  The repo is public and the deploy runner lives on the production VM, so an
  unreviewed PR could otherwise run code on the server.
- **Complaints never reach logs, Discord message history, or the bot's DB
  access.** Read the "Complaints" rules in the README before touching that code.
- **Don't commit secrets, IP addresses or `.env` files.** The repo is public.

## Incoming: your first week

- [ ] Get access to the club password store, and confirm you can log in to
      GitHub `rmit-bga`, Oracle Cloud and the Discord Developer Portal.
- [ ] Get the handover secrets document from the outgoing maintainer, through
      the password store rather than email or Discord.
- [ ] SSH in with the key from that document, add **your own** key to
      `~/.ssh/authorized_keys`, confirm it works, then remove the old key.
- [ ] Do the full credential rotation in the handover secrets document (§7).
      After that, nothing the previous maintainer held still works.
- [ ] Check backups are running: `tail ~/servers/rbga/backup.log` shows a run
      from last night. Copy one dump off the box (see `operations.md`).
- [ ] Make a trivial PR (fix a typo in these docs), merge it, and watch it
      deploy in the Actions tab. Now you've done a full deploy cycle.
- [ ] In Discord, check `/keys`, `/game list`, and that `/complaints-setup`
      opens and points at the current committee/exec channels and president.
- [ ] Update the "Last handed over" line at the bottom of this file.

## Outgoing: before you leave

- [ ] Successor has done every item in the first-week list above. (Rotation is
      what actually removes your access, so it must happen.)
- [ ] Remove yourself as a collaborator on `rmit-bga/rbga-services`, and from
      the Discord Developer Portal team.
- [ ] Delete your copies of the SSH key and the handover secrets document.
- [ ] Hand over anything that only exists on your machine (local notes,
      unmerged branches). Push or delete each one.
- [ ] Update `/complaints-setup` if the president or channels are changing at
      the same time.

## Not finished

Open work a successor might pick up. Details are in the README's "Not done yet":
the web complaints form on the club website, and the Instagram
announcement mirror (the `instagram-story-mirror` branch, not yet merged).

---

Last handed over: *(not yet; first handover due December 2026)*
