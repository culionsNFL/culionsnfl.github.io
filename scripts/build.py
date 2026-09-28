#!/usr/bin/env python3
"""Build index.html for the CU Lions NFL Wins League site.

  python3 scripts/build.py [--offline path/to/games.csv]

Pipeline: fetch nflverse results -> compute standings (with invariant checks)
-> attach the hand-written blurbs and story -> inject into template.html ->
wrap as a standalone document -> write index.html.

compute.compute() raises SystemExit on any arithmetic inconsistency, so a bad
data feed fails the build instead of publishing wrong numbers.
"""
import argparse, csv, datetime, io, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import compute  # noqa: E402

SEASON = int(os.environ.get("SEASON", "2026"))

HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="Standings, results and weekly storylines for the CU Lions NFL Wins League.">
<meta name="robots" content="noindex">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'><text y='14' font-size='14'>%F0%9F%8F%88</text></svg>">
<meta http-equiv="Cache-Control" content="no-cache">
"""
TAIL = "\n</body>\n</html>\n"


def read_json(path, default):
    try:
        with io.open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return default


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", help="use a local games.csv instead of fetching")
    args = ap.parse_args()

    if args.offline:
        with io.open(args.offline, encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
    else:
        rows = compute.fetch()

    payload = compute.compute(rows, SEASON)
    payload["blurbs"] = read_json(os.path.join(ROOT, "content", "blurbs.json"), {})
    story = read_json(os.path.join(ROOT, "content", "story.json"), None)
    if story:
        payload["story"] = story
    payload["refreshNote"] = ("Scores and standings rebuild automatically every morning; "
                              "storylines are written by hand")

    with io.open(os.path.join(ROOT, "template.html"), encoding="utf-8") as fh:
        tpl = fh.read()

    block = ('<script id="payload" type="application/json">\n'
             + json.dumps(payload, indent=1, sort_keys=True)
             + '\n</script>')
    out, n = re.subn(r'<script id="payload" type="application/json">.*?</script>',
                     lambda _m: block, tpl, count=1, flags=re.S)
    if n != 1:
        raise SystemExit("FAIL: could not find the payload block in template.html")

    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    doc = HEAD + "<!-- built " + stamp + " -->\n</head>\n<body>\n" + out + TAIL

    with io.open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(doc)

    c = payload["checks"]
    print("built index.html — %d bytes | week %s, %s of %s played | %d wins / %d losses / %d ties / %d teams"
          % (len(doc), payload["currentWeek"], payload["curPlayed"], payload["curTotal"],
             c["wins"], c["losses"], c["ties"], c["teams"]))


if __name__ == "__main__":
    main()
