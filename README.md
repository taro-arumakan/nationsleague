# Nations League Game Calendar

A subscribable `.ics` calendar of every UEFA Nations League game that's live on
**free UK TV**, tagged with its channel. Scores and knockout ties fill in
automatically as the competition plays out.

Hosted free on GitHub Pages. No server, no tracking.
**Landing page:** https://yadot.sniarti.fi/nationsleague/

## The feed

| Feed | Contains | Title example |
| --- | --- | --- |
| `uk.ics` | Home nations' games + the final | `England v Spain - ITV` | `Portugal v Wales - BBC` |

`https://yadot.sniarti.fi/nationsleague/uk.ics` - or `webcal://…/uk.ics` to open
Apple Calendar directly.

**Subscribe:** iPhone/Mac → open the `webcal://` link → Add. Google Calendar → Other
calendars ▸ **+** ▸ *From URL* → paste the HTTPS URL. Outlook → Subscribe from web.

Kickoffs are stored in **UTC**, so every client shows them in *your* local time zone.

## Channels

The UK rights are split by nation rather than picked game by game, so every game
is labelled from the start:

- **England** → `ITV` (ITV1 / ITVX; STV in Scotland)
- **Scotland, Wales, Northern Ireland** → `BBC` (BBC TV / iPlayer; Wales also on S4C, in Welsh)
- **The final** (June 2027) → `ITV`, whoever reaches it

Games without a home nation aren't on free UK TV, so they're left out.

## How it's built

```
fetch.py                   # UEFA match feed → data/matches.json (all matches, one per line)
data/broadcasters.json     # per-match channel overrides (normally empty)
generate.py                # matches.json + channel rule → docs/uk.ics
docs/uk.ics                # the published calendar
docs/index.html            # landing page
```

```sh
python3 fetch.py      # refresh fixtures & final scores
python3 generate.py   # rewrite docs/uk.ics (deterministic output)
```

## Staying current

`.github/workflows/update.yml` runs every 6 hours: fetch, regenerate, and commit
**only if something changed**. Knockout ties (March 2027) and the Finals (June 2027)
appear on their own once UEFA publishes them; subscribers just refresh.

If a channel ever differs from the rule (say a home-nations derby, or a late
switch), add an override keyed by the match id from `data/matches.json`:

```json
"overrides": { "2048018": { "uk": "BBC", "detail": "BBC One / iPlayer" } }
```

## Data sources & caveats

- Fixtures, kickoff times, venues and results: UEFA's match feed (the JSON behind
  [uefa.com](https://www.uefa.com/uefanationsleague/)). It's undocumented, so it's polled gently.
- Channels: the 2026/27 UK rights split (ITV: England + the final; BBC: Scotland,
  Wales, Northern Ireland; S4C: Wales).

Channels can change late. Verify with the broadcaster before kickoff.
