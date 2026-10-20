# magpie

A rental-listing watcher. Every 10 minutes it checks Czech property sites for flats to rent in a chosen
area and price range, and pushes a notification to your phone (via [ntfy](https://ntfy.sh)) the moment a
new one appears. It runs for free on GitHub Actions.

The included `config.yaml` watches **central to western Brno around Brněnská přehrada, up to 14 000 Kč a
month including fees, whole flats only**.

## What it does

- Scrapes **iDNES Reality**, **Realitymix** and **Bazoš** (via its RSS feed)
- Filters on:
  - **Area:** neighbourhood names, then GPS or postcode when a listing gives nothing better
  - **Total price:** rent plus fees, read from structured fields or from the description text
  - **Flat type:** skips rooms in shared flats, wanted ads and short-term lets
- Notifies **once per flat**, even when the same flat is posted on several sites, and again only if its
  price drops
- Notifications show rent, fees and area and open the listing on tap. They are marked
  `⚠ fees not listed` or `⚠ area unclear` when the listing doesn't say
- Sends one warning if a site keeps failing (for example, after a layout change), and a note when it
  recovers
- Respects `robots.txt`: every request is checked against the site's rules first

### Sites it doesn't scrape

**Sreality**, **Bezrealitky** and **UlovDomov** block bots in their `robots.txt`: Sreality across the
whole site, the other two on the search pages and data endpoints. Their own apps have instant alerts for
saved searches ("hlídací pes"). Set those up alongside magpie for full coverage.

## Setup

1. **Phone:** install the ntfy app ([Android](https://play.google.com/store/apps/details?id=io.heckel.ntfy) /
   [iOS](https://apps.apple.com/app/ntfy/id1625396347)). Subscribe to a topic with a long random name.
   Anyone who knows the name can read the alerts. To generate one:
   ```
   python3 -c "import secrets; print('magpie-' + secrets.token_urlsafe(12))"
   ```
2. **GitHub:** add the topic name as a repository secret, under *Settings → Secrets and variables →
   Actions → New repository secret*. Use the name `NTFY_TOPIC`.
3. **Merge to `main`.** GitHub only runs scheduled workflows from the default branch.
4. **Test:** go to *Actions → magpie → Run workflow* and tick "Only send a test notification". Your
   phone should buzz.

The first real run sends the flats that are already listed, quietly, so your phone doesn't buzz for
each one. After that, every new match is sent at high priority.

## Running locally

```
uv sync
uv run python main.py --dry-run -v              # print matches and skip reasons, send nothing
NTFY_TOPIC=your-topic uv run python main.py     # one real check
NTFY_TOPIC=your-topic uv run python main.py --loop 10
uv run pytest
```

State is kept in `state/seen.json`, which is git-ignored. On GitHub it's kept in the Actions cache.

## Changing what it looks for

All of it is in `config.yaml`:
- **Budget:** `price.max_total`
- **Area:** `area.include` and `area.exclude` name the neighbourhoods. `area.polygon` is the GPS
  fallback.
- **Alerts with an unclear area:** set `area.notify_unknown_area: false` to drop them
- **Search pages:** `sources.*.url`. Any iDNES or Realitymix results URL works.

## Notes

- GitHub runs scheduled jobs on a best-effort basis. At busy times a run can start 10–20 minutes late.
- GitHub disables scheduled workflows in public repositories after 60 days without repository activity.
  It emails you first, and one click re-enables it.
- Reading fees from description text is a heuristic. When it can't tell, magpie compares the rent alone
  and flags the alert, so an unclear listing gets sent rather than silently dropped.
