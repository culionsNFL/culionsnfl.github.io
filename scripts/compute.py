#!/usr/bin/env python3
"""Compute NFL pick'em league standings from nflverse game results.

Emits the JSON payload embedded in the standings artifact.
Validates league-wide invariants before emitting; exits non-zero on failure.
"""
import csv, io, json, sys, urllib.request, datetime

DEFAULT_SEASON = 2026
URL = "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"

ROSTERS = {
    "Patrick":  ["DET", "IND", "CAR", "CLE"],
    "Mark":     ["BAL", "SF",  "CHI", "LV"],
    "Zach":     ["LA",  "LAC", "GB",  "MIA"],
    "Bill":     ["CIN", "DAL", "TB",  "NYG"],
    "Jon":      ["BUF", "KC",  "PIT", "TEN"],
    "Harrison": ["NE",  "HOU", "MIN", "WAS"],
    "Anthony":  ["PHI", "DEN", "ARI", "NYJ"],
    "Brian":    ["SEA", "JAX", "NO",  "ATL"],
}


def fetch():
    req = urllib.request.Request(URL, headers={"User-Agent": "pickem/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return list(csv.DictReader(io.StringIO(r.read().decode("utf-8"))))


def compute(rows, season):
    reg = [r for r in rows if r["season"] == str(season) and r["game_type"] == "REG"]
    if not reg:
        raise SystemExit(f"FAIL: no REG games found for {season}")

    teams = sorted({r["home_team"] for r in reg} | {r["away_team"] for r in reg})
    if len(teams) != 32:
        raise SystemExit(f"FAIL: expected 32 teams, got {len(teams)}")

    owner_of = {t: o for o, ts in ROSTERS.items() for t in ts}
    if set(owner_of) != set(teams) or len(owner_of) != 32:
        missing = set(teams) - set(owner_of)
        extra = set(owner_of) - set(teams)
        raise SystemExit(f"FAIL: roster mismatch. undrafted={missing} unknown={extra}")

    rec = {t: {"w": 0, "l": 0, "t": 0} for t in teams}
    weekly = {o: [0.0] * 18 for o in ROSTERS}
    last_week = 0
    unplayed_weeks = set()

    def played(g):
        return g["home_score"] not in ("", "NA") and g["away_score"] not in ("", "NA")

    for g in reg:
        wk = int(g["week"])
        if not played(g):
            unplayed_weeks.add(wk)
            continue
        hs, as_ = int(float(g["home_score"])), int(float(g["away_score"]))
        h, a = g["home_team"], g["away_team"]
        last_week = max(last_week, wk)
        if hs > as_:
            rec[h]["w"] += 1; rec[a]["l"] += 1
            weekly[owner_of[h]][wk - 1] += 1.0
        elif as_ > hs:
            rec[a]["w"] += 1; rec[h]["l"] += 1
            weekly[owner_of[a]][wk - 1] += 1.0
        else:
            rec[h]["t"] += 1; rec[a]["t"] += 1
            weekly[owner_of[h]][wk - 1] += 0.5
            weekly[owner_of[a]][wk - 1] += 0.5

    # ---- invariants: fail loudly rather than publish bad numbers ----
    tw = sum(v["w"] for v in rec.values())
    tl = sum(v["l"] for v in rec.values())
    tt = sum(v["t"] for v in rec.values())
    if tw != tl:
        raise SystemExit(f"FAIL: league wins {tw} != losses {tl}")
    if tt % 2:
        raise SystemExit(f"FAIL: odd tie count {tt}")
    for t, v in rec.items():
        gp = v["w"] + v["l"] + v["t"]
        if gp > 17:
            raise SystemExit(f"FAIL: {t} shows {gp} games played")

    pts = {o: round(sum(rec[t]["w"] + 0.5 * rec[t]["t"] for t in ts), 1)
           for o, ts in ROSTERS.items()}
    if abs(sum(pts.values()) - (tw + tt / 2.0)) > 1e-6:
        raise SystemExit("FAIL: owner points do not sum to league games decided")

    # ---- the week ahead ----
    cur = min(unplayed_weeks) if unplayed_weeks else None

    def num(v):
        return None if v in ("", "NA", None) else float(v)

    # Carry the current week plus the one before it: enough for a running
    # recap through the weekend without the page growing all season.
    anchor = cur if cur is not None else last_week
    show = [w for w in (anchor - 1, anchor) if w >= 1]

    games_out = []
    cur_played = cur_total = 0
    for g in reg:
        wk = int(g["week"])
        if wk not in show:
            continue
        d = played(g)
        if wk == cur:
            cur_total += 1
            if d:
                cur_played += 1
        games_out.append({
            "wk": wk,
            "away": g["away_team"],
            "home": g["home_team"],
            "kick": f"{g['gameday']} {g['gametime']}",
            # spread_line is from the HOME team's perspective: positive = home favored.
            "spread": num(g["spread_line"]),
            "total": num(g["total_line"]),
            "done": d,
            "hs": int(float(g["home_score"])) if d else None,
            "as": int(float(g["away_score"])) if d else None,
            "qbHome": g["home_qb_name"],
            "qbAway": g["away_qb_name"],
            "div": g["div_game"] == "1",
            "stadium": g["stadium"],
        })
    games_out.sort(key=lambda x: (x["kick"], x["home"]))

    return {
        "season": season,
        "lastCompletedWeek": last_week,
        # Weeks that are actually FINISHED. Trend lines and week-over-week
        # movement must use this, not last_week — mid-week, last_week is the
        # week in progress and a chart drawn to it reads as a collapse.
        "completeWeeks": (cur - 1) if cur is not None else last_week,
        "currentWeek": cur,
        "updated": datetime.datetime.now(datetime.timezone.utc)
                    .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rosters": ROSTERS,
        "teams": rec,
        "weekly": {o: [round(x, 1) for x in w[:last_week]] for o, w in weekly.items()},
        "points": pts,
        "games": games_out,
        "curPlayed": cur_played,
        "curTotal": cur_total,
        "checks": {"wins": tw, "losses": tl, "ties": tt, "teams": len(teams)},
    }


if __name__ == "__main__":
    season = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SEASON
    print(json.dumps(compute(fetch(), season), indent=1, sort_keys=True))
