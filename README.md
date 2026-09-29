# Nations League Game Calendar

A subscribable `.ics` calendar of every UEFA Nations League game that's live on
**free UK TV**, tagged with its channel. Scores and knockout ties fill in
automatically as the competition plays out.

Hosted free on GitHub Pages. No server, no tracking.
**Landing page:** https://yadot.sniarti.fi/nationsleague/

## The feed

| Feed | Contains | Title example |
| --- | --- | --- |
| `uk.ics` | Every England, Scotland, Wales & NI game | `England v Spain - ITV` | `Portugal v Wales - BBC` |

`https://yadot.sniarti.fi/nationsleague/uk.ics` - or `webcal://…/uk.ics` to open
Apple Calendar directly.

**Subscribe:** iPhone/Mac → open the `webcal://` link → Add. Google Calendar → Other
calendars ▸ **+** ▸ *From URL* → paste the HTTPS URL. Outlook → Subscribe from web.

Kickoffs are stored in **UTC**, so every client shows them in *your* local time zone.

## Channels

The UK rights are split by nation rather than picked game by game (both deals run
to June 2028), so every game is labelled from the start:

- **England** → `ITV` (ITV1 / ITVX; STV in Scotland)
- **Scotland, Wales, Northern Ireland** → `BBC` (BBC TV / iPlayer; Wales also on S4C, in Welsh)

Games without a home nation are Prime Video pay-per-view in the UK, so they're left
out. No UK deal for the June 2027 final has been announced yet (ITV showed it in
2025); it gets added as an override once one is.

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

To add a game the rule doesn't cover (the final, once its broadcaster is known) or
fix one that differs (say a home-nations derby, or a late switch), add an override
keyed by the match id from `data/matches.json`:

```json
"overrides": { "2048018": { "uk": "BBC", "detail": "BBC One / iPlayer" } }
```

## Data sources & caveats

- Fixtures, kickoff times, venues and results: UEFA's match feed (the JSON behind
  [uefa.com](https://www.uefa.com/uefanationsleague/)). It's undocumented, so it's polled gently.
- Channels: the UK rights split to June 2028 (ITV: England; BBC: Scotland, Wales,
  Northern Ireland; S4C: Wales in Welsh). See the
  [FA](https://www.englandfootball.com/articles/2023/Sep/19/itv-england-men-games-tv-deal-2024-2028-20230919)
  and [Sportcal](https://www.sportcal.com/news/mens-home-nations-uefa-fixtures-staying-on-bbc-until-mid-2028/)
  announcements; per-game listings on [Where's the Match](https://www.wheresthematch.com/uefa-nations-league-on-tv/).

Channels can change late. Verify with the broadcaster before kickoff.
