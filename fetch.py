#!/usr/bin/env python3
"""Refresh data/matches.json from UEFA's match feed (the JSON behind uefa.com).

Pulls every Nations League match of the season - league phase, quarter-finals,
promotion/relegation play-offs and the Finals - and keeps only what the
calendar needs, one match per line so diffs stay readable. Final scores are
stored once a match is FINISHED; live scores are ignored, so the file only
changes when something the calendar shows changes.

The feed is undocumented, so be gentle: the workflow polls it every 6 hours.
Its CDN rejects the default Python User-Agent, hence the explicit one below.
"""
import json
import sys
import time
import urllib.request
from pathlib import Path

SEASON_YEAR = 2027            # UEFA names seasons by their end year: 2026/27 -> 2027
SEASON_LABEL = "2026/27"
COMPETITION_ID = 2014         # UEFA Nations League
API = "https://match.uefa.com/v5/matches"
UA = "nationsleague-calendar/1.0 (+https://github.com/taro-arumakan/nationsleague)"
PAGE = 100

OUT = Path(__file__).resolve().parent / "data" / "matches.json"

ROUND_LABEL = {               # round name -> singular label for titles
    "Quarter-finals": "Quarter-final",
    "Play-offs": "Play-off",
    "Semi-finals": "Semi-final",
    "3rd place": "Third-place play-off",
    "Final": "Final",
}


def get(url, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception as e:           # transient 429/5xx/network - back off and retry
            if i == tries - 1:
                raise
            print(f"retry {i + 1} after {e}", file=sys.stderr)
            time.sleep(5 * (i + 1))


def fetch_all():
    out, offset = [], 0
    while True:
        page = get(f"{API}?competitionId={COMPETITION_ID}&seasonYear={SEASON_YEAR}"
                   f"&limit={PAGE}&offset={offset}&order=ASC")
        out += page
        if len(page) < PAGE:
            return out
        offset += PAGE


def en(obj, *path):
    """Walk nested dicts, e.g. en(stadium, 'translations', 'name', 'EN')."""
    for k in path:
        obj = (obj or {}).get(k)
    return obj


def team(t):
    return en(t, "translations", "displayName", "EN") or (t or {}).get("internationalName") or "TBD"


def score_text(m):
    total = en(m, "score", "total")
    if m.get("status") != "FINISHED" or not total:
        return None
    s = f'{total["home"]}-{total["away"]}'
    extra = []
    agg = en(m, "score", "aggregate")
    if m.get("type") == "SECOND_LEG" and agg:
        extra.append(f'agg {agg["home"]}-{agg["away"]}')
    if "EXTRA" in (en(m, "winner", "match", "reason") or ""):
        extra.append("a.e.t.")
    pens = en(m, "score", "penalty")
    if pens:
        extra.append(f'{pens["home"]}-{pens["away"]} pens')
    return f'{s} ({", ".join(extra)})' if extra else s


def normalise(m):
    stage = en(m, "round", "metaData", "name") or "TBC"
    if stage == "League phase":
        label = en(m, "group", "metaData", "groupName") or stage
    else:
        label = ROUND_LABEL.get(stage, stage)
        leg = en(m, "leg", "translations", "name", "EN")
        if leg:
            label += f" {leg}"
    ko = m.get("kickOffTime") or {}
    rec = {
        "id": str(m["id"]),
        "kickoff": ko.get("dateTime") or ko.get("date"),   # date only = time TBC
        "stage": stage,
        "label": label,
        "home": team(m.get("homeTeam")),
        "away": team(m.get("awayTeam")),
        "venue": en(m, "stadium", "translations", "name", "EN"),
        "city": en(m, "stadium", "city", "translations", "name", "EN"),
    }
    score = score_text(m)
    if score:
        rec["score"] = score
    if m.get("status") not in (None, "UPCOMING", "LIVE", "FINISHED"):
        rec["status"] = m["status"]                     # e.g. POSTPONED
    return {k: v for k, v in rec.items() if v is not None}


def main():
    raw = fetch_all()
    matches = sorted((normalise(m) for m in raw), key=lambda r: (r["kickoff"] or "", r["id"]))

    old = json.loads(OUT.read_text(encoding="utf-8"))["matches"] if OUT.exists() else []
    if not matches or len(matches) < 0.9 * len(old):
        # Matches never disappear from a season; a short answer means a bad fetch.
        sys.exit(f"!! fetched {len(matches)} matches, had {len(old)} - keeping the old data")

    body = ",\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True) for r in matches)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        '{"season": "%s", "source": "%s?competitionId=%d&seasonYear=%d",\n"matches": [\n%s\n]}\n'
        % (SEASON_LABEL, API, COMPETITION_ID, SEASON_YEAR, body), encoding="utf-8")
    finished = sum(1 for r in matches if "score" in r)
    print(f"matches.json: {len(matches)} matches ({finished} finished)")


if __name__ == "__main__":
    main()
