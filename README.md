# CU Lions NFL Wins League — standings site

A self-updating standings page for an eight-owner NFL team-draft pool.
One point per team win, half a point per tie, regular season only.

Live at `https://<username>.github.io/` once GitHub Pages is switched on.

---

## Getting it live (about five minutes, once)

You don't need to give anyone a password or a token to do this.

1. **Create a GitHub account** at github.com if you don't have one.
   The username becomes the address — `culions` gives you `culions.github.io`.

2. **Create a new repository** named exactly `<username>.github.io`
   (for example `culions.github.io`). Make it **Public** — GitHub Pages
   needs public on a free account. Don't add a README; this folder has one.

3. **Upload these files.** On the empty repo page choose
   *uploading an existing file*, then drag in everything from this folder,
   including the `.github`, `scripts` and `content` folders. Commit.

4. **Turn on Pages.** Settings → Pages → Source: *Deploy from a branch*,
   branch `main`, folder `/ (root)`. Save.

5. Wait a minute, then open `https://<username>.github.io/`.

That's the whole setup. Send that link to the league and never send another.

### One extra setting worth ticking

Settings → Actions → General → Workflow permissions → **Read and write
permissions**. The daily rebuild needs it to commit the updated page.
Without it the scheduled job will run and fail at the last step.

---

## How updates happen

**Scores and standings: automatic.** `.github/workflows/update.yml` runs every
morning at about 7:20am ET. It pulls the latest results, recomputes everything,
and commits a new `index.html` only if something actually changed. You can also
trigger it by hand from the **Actions** tab → *Rebuild standings* → *Run workflow*.

**Storylines: by hand.** The game recaps, previews and the story section at the
top are written, not generated. They live in `content/` and get picked up by the
next build.

---

## What's in here

| Path | What it does |
|---|---|
| `index.html` | The built page. **Generated — don't edit it directly.** |
| `template.html` | The page itself: layout, styling, all the rendering logic. |
| `scripts/compute.py` | Fetches nflverse results, computes records and points, validates. |
| `scripts/build.py` | Runs compute, folds in `content/`, writes `index.html`. |
| `content/blurbs.json` | Per-game recaps and previews, keyed `"<week>:<AWAY>@<HOME>"`. |
| `content/story.json` | The story section: one lede plus the beats under it. |
| `.github/workflows/update.yml` | The daily rebuild. |
| `.nojekyll` | Stops GitHub trying to process the site as a Jekyll blog. |

### Rebuilding locally

```sh
python3 scripts/build.py                     # fetch live results
python3 scripts/build.py --offline games.csv # use a saved copy
```

Needs Python 3 and nothing else — no packages to install.

---

## The correctness check

`compute.py` refuses to produce a payload unless the league arithmetic holds:

- total wins equal total losses
- the tie count is even
- no team has played more than 17 games
- the eight rosters cover exactly 32 franchises, no gaps or duplicates
- owner points reconcile against games actually decided

Any failure exits non-zero, which fails the build, which means nothing gets
committed. A broken upstream feed shows you yesterday's correct page rather
than today's wrong one. This matters more than it sounds: an earlier version of
this project pulled from a source that confidently reported a 15-2 team that was
actually 9-8.

## Editing the content files

`content/blurbs.json` is a flat object. The key is the week number, a colon, the
away team, an `@`, and the home team — all standard abbreviations:

```json
{ "3:ATL@GB": "The team that had scored 16 points in two weeks..." }
```

`content/story.json` holds the section above the standings:

```json
{
  "note": "Week 3 · Thursday in the book",
  "lede": "One sentence that frames the week.",
  "beats": [
    { "owner": "Brian", "tag": "Brian · Into a tie for second", "text": "..." },
    { "tag": "The rest of the week", "text": "..." }
  ]
}
```

`owner` is optional — supply it and the beat gets a rule in that owner's colour,
the same colour they carry in the standings and on the chart. Leave it off for
league-wide notes. Beats lay themselves out so a row never ends with one orphan.

## Changing the league

Rosters live in one place: the `ROSTERS` dictionary at the top of
`scripts/compute.py`. Edit it there and the standings, chart, colours, owner
labels on every game, and the both-sides-drafted notes all follow. The build
will refuse to run if the rosters don't cover exactly 32 teams.

For next season, change `ROSTERS` and set `SEASON` in the workflow environment,
or leave it and edit `DEFAULT_SEASON` in `compute.py`.

## Data source

Game results and closing market lines come from
[nflverse/nfldata](https://github.com/nflverse/nfldata) (`data/games.csv`),
a community-maintained dataset. No API key, no scraping, no rate limits worth
worrying about.

## Known quirks

- **Updates can take a few minutes to reach everyone.** GitHub Pages sits
  behind a CDN. The build is instant; the cache isn't.
- **Trend features stay hidden until they mean something.** The chart and the
  movement arrows only use *completed* weeks, so mid-week they won't include
  the week in progress. This is deliberate — drawing a chart out to a week
  that's one game old makes it look like everyone collapsed.
- **The banner photo slot is empty.** `.banner-photo` in `template.html` is
  ready for an image; it needs to be embedded as a data: URI.
