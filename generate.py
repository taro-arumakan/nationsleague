#!/usr/bin/env python3
"""Generate the Nations League UK free-to-air calendar (docs/uk.ics).

data/matches.json holds every Nations League fixture of the season, refreshed by
fetch.py. Only games that are live on free UK TV go into the calendar, and the
channel follows the rights split (by nation, not picked game by game; ITV and
the BBC hold these through June 2028):

  England                            -> ITV  (ITV1 / ITVX, STV in Scotland)
  Scotland, Wales, Northern Ireland  -> BBC  (iPlayer; Wales also on S4C)

Every other game is Prime Video pay-per-view in the UK, so it's left out.

data/broadcasters.json "overrides" (keyed by match id) beat the rule - e.g. to
add the June 2027 final once a free-to-air deal is announced (ITV had it in
2025), for a home-nation derby, or a late channel change. {"uk": ""} drops a match.

Output is deterministic (DTSTAMP = DTSTART), so re-running with unchanged input
produces byte-identical files and the update workflow only commits real changes.
Events are emitted in UTC (...Z); calendar apps show each kickoff in local time.
"""
import json
import re
import sys
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
DOCS = ROOT / "docs"

PRODID = "-//taro-arumakan//NationsLeague//EN"
FEED = "uk.ics"
CALNAME = "Nations League ⚽ UK TV (BBC/ITV)"
CALDESC = ("UEFA Nations League - every game that's live on free UK TV: England on ITV; "
           "Scotland, Wales & Northern Ireland on BBC (Wales also on S4C). "
           "Kickoffs auto-convert to your local time.")

ITV_TEAMS = {"england"}
BBC_TEAMS = {"scotland", "wales", "northernireland"}


def norm(name):
    s = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z]", "", s)


def teams_of(m):
    return {norm(m["home"]), norm(m["away"])}


def uk_channel(m, overrides):
    """Return (channel, detail) for a free-to-air game, or (None, None)."""
    ex = overrides.get(m["id"])
    if ex is not None:
        uk = ex.get("uk") or None
        return uk, ex.get("detail") or (uk and default_detail(uk, m))
    t = teams_of(m)
    if t & ITV_TEAMS:
        uk = "ITV"
    elif t & BBC_TEAMS:
        uk = "BBC"
    else:
        return None, None
    return uk, default_detail(uk, m)


def default_detail(uk, m):
    if uk == "ITV":
        return "ITV1 / ITVX (STV in Scotland)"
    if uk == "BBC":
        return "BBC / iPlayer" + (" | S4C (in Welsh)" if "wales" in teams_of(m) else "")
    return uk


def esc(t):
    return (t.replace("\\", "\\\\").replace(";", "\\;")
            .replace(",", "\\,").replace("\n", "\\n"))


def fold(line):
    """RFC 5545 line folding on UTF-8 byte boundaries (<=75 octets/line)."""
    b = line.encode("utf-8")
    if len(b) <= 73:
        return line
    chunks, i, limit = [], 0, 73
    while i < len(b):
        j = min(i + limit, len(b))
        while j < len(b) and (b[j] & 0xC0) == 0x80:
            j -= 1
        chunks.append(b[i:j].decode("utf-8"))
        i, limit = j, 72
    return "\r\n ".join(chunks)


def summary_for(m, uk):
    fixture = f'{m["home"]} v {m["away"]}'
    title = fixture if m["stage"] == "League phase" else f'{m["label"]}: {fixture}'
    return f"{title} - {uk}"


def description_for(m, detail, location):
    # Line 1: game (league/group or round + venue), then channel, then result.
    lines = [f'{m["label"]} / {location}' if location else m["label"], f"UK: {detail}"]
    if m.get("score"):
        lines.append(f'Result: {m["home"]} {m["score"]} {m["away"]}')
    return "\n".join(lines)


def build_event(m, uk, detail):
    location = ", ".join(x for x in (m.get("venue"), m.get("city")) if x)
    if len(m["kickoff"]) == 10:                      # date known, kickoff time TBC
        day = datetime.strptime(m["kickoff"], "%Y-%m-%d")
        start = [f'DTSTART;VALUE=DATE:{day:%Y%m%d}',
                 f'DTEND;VALUE=DATE:{day + timedelta(days=1):%Y%m%d}']
        stamp, sort_key = f"{day:%Y%m%dT%H%M%SZ}", day
    else:
        dt = datetime.strptime(m["kickoff"], "%Y-%m-%dT%H:%M:%SZ")
        dur = timedelta(hours=2) if m["stage"] == "League phase" else timedelta(hours=2, minutes=30)
        stamp, sort_key = f"{dt:%Y%m%dT%H%M%SZ}", dt
        start = [f"DTSTART:{stamp}", f"DTEND:{dt + dur:%Y%m%dT%H%M%SZ}"]
    return (sort_key, m["id"]), [
        "BEGIN:VEVENT",
        f'UID:unl-{m["id"]}@nationsleague-calendar',
        f"DTSTAMP:{stamp}",
        *start,
        f"SUMMARY:{esc(summary_for(m, uk))}",
        *([f"LOCATION:{esc(location)}"] if location else []),
        f"DESCRIPTION:{esc(description_for(m, detail, location))}",
        "CATEGORIES:Nations League,Football",
        "TRANSP:TRANSPARENT",
        "STATUS:CONFIRMED",
        "END:VEVENT",
    ]


def write_calendar(path, event_lines):
    out = [
        "BEGIN:VCALENDAR", "VERSION:2.0", f"PRODID:{PRODID}",
        "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
        f"X-WR-CALNAME:{esc(CALNAME)}", "X-WR-TIMEZONE:UTC",
        f"X-WR-CALDESC:{esc(CALDESC)}",
        "REFRESH-INTERVAL;VALUE=DURATION:PT12H", "X-PUBLISHED-TTL:PT12H",
    ] + event_lines + ["END:VCALENDAR"]
    path.write_text("\r\n".join(fold(l) for l in out) + "\r\n", encoding="utf-8")


def main():
    matches = json.loads((DATA / "matches.json").read_text(encoding="utf-8"))["matches"]
    overrides = json.loads((DATA / "broadcasters.json").read_text(encoding="utf-8")).get("overrides", {})

    events, per_channel, derbies = [], {}, []
    for m in matches:
        uk, detail = uk_channel(m, overrides)
        if not uk:
            continue
        t = teams_of(m)
        if t & ITV_TEAMS and t & BBC_TEAMS and m["id"] not in overrides:
            derbies.append(f'{m["home"]} v {m["away"]} ({m["id"]})')
        per_channel[uk] = per_channel.get(uk, 0) + 1
        events.append(build_event(m, uk, detail))

    DOCS.mkdir(parents=True, exist_ok=True)
    lines = [l for _, ls in sorted(events, key=lambda x: x[0]) for l in ls]
    write_calendar(DOCS / FEED, lines)
    print(f"{FEED}: {len(events)} of {len(matches)} matches are free-to-air  "
          f"{dict(sorted(per_channel.items()))}  ({(DOCS / FEED).stat().st_size} bytes)")

    # ---- validation ---------------------------------------------------------
    if derbies:   # England v another home nation: ITV by rule, but worth checking
        print(f"check channel (England v home nation, no override): {derbies}")
    if not matches or not events:
        print("!! VALIDATION FAILED: no matches / no free-to-air games", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
