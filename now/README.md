# databrew NOW (experiment)

The NOW feed combines `../articles.json` (real databrew STORIES) with `now/threads.json` (posts from the account owner). No demo posts are invented, and the existing databrew home page stays intact.

## Connect an actual Meta Threads account

1. Create/configure a Meta Threads developer app for the Threads account and authorize it with the read permission (`threads_basic`).
2. Exchange for a valid access token as described in [Meta's Threads API documentation](https://www.postman.com/meta/threads/collection/dht3nzz/threads-api).
3. Add the token as the `THREADS_ACCESS_TOKEN` GitHub **Actions repository secret** (not a variable, not a committed file). Never share it in a chat or put it in GitHub Pages JavaScript.
4. Run the GitHub Action **Sync Threads to databrew NOW** manually once. On the default branch it also runs about every four hours, subject to GitHub Actions scheduler variability.
5. Check `now/threads.json` for an `updated_at`, a Threads profile URL, and an array of publicly viewable posts. The frontend then displays a real Threads follow link and per-post links to comments/conversation on Threads.

Authentication and long-lived token refresh/rotation remain administrator duties. Expired token errors appear in the GitHub Action logs, not on the public site. The script never guesses a profile URL. Do not add credentials in files or browser scripts.

### Current scope and limitations

- One-way synchronization: Threads → NOW. NOW never auto-publishes to Meta.
- The Threads conversation, replies, likes and follows remain on Meta; no fake counts or local reply forms.
- The same NOW page also displays existing articles, with clear STORY/THREADS labels.
- Scheduled runs only change the file when the actual post list changes, to avoid noisy commits.
- This static GitHub Pages MVP has no secure CMS login or account-based following. A real multi-author newsroom version needs a backend and moderation.
- Public content only; remove sensitive posts and revoke app access if necessary. Posts deleted on Threads disappear from NOW on the next successful sync; browser caches may persist briefly.
- For privacy, unlike embedding the full Meta widget, the NOW frontend currently renders only text/media and links. A visitor only loads Meta after choosing a Threads link. Media thumbnails may be loaded from Meta-hosted origins.

## Local test

```bash
python -m http.server 8080
# visit http://localhost:8080/now/
```

The script exits successfully without changes when `THREADS_ACCESS_TOKEN` is not provided. To test live sync locally with a token, set it privately as an environment variable and run `python scripts/sync_threads.py`; never commit your token.

## Automatic NOW content (v2)

The `Build databrew NOW daily feed` GitHub Action runs twice a day (09:35 and 21:35 KST) and supports manual dispatch. It reads *already published, public* source JSON without inventing data:

| NOW item | Input | Observation-date rule |
| --- | --- | --- |
| BOK워치 | `https://bokwatch.pages.dev/data/meta.json` + `data/snapshots/YYYY-MM-DD.json` | actual `asof` model snapshot; next meeting uses primary KOFR OIS scenario when selected, never internal memo's incorrect CD 91-day summary |
| FX워치 | `https://raspos.github.io/fx-odds/data/latest.json` | `base_date` (ECOS reference rate; never call it the 15:30 closing price) |
| APT워치 | `https://raspos.github.io/apt-watch/data.json` | `negoIndex.asOf` or asking last success; withhold numeric index if verification is held |
| 서울 아파트 신고가 | `https://raspos.github.io/seoul-apartment-tracker/data/{meta.json,daily.json.gz}` | `snapshotDate`; show the last 30 *contract dates*' records and delayed-reporting caveat |
| Existing and new projects | Current `index.html` project cards | Old projects have no invented launch date; newly detected projects get first-seen timestamp |
| STORIES | Current `articles.json` | Actual article publication date; already displays automatically |
| Threads | Existing `threads.json` | Meta's own timestamp, once the user authenticates |

**Source publish dependency:** refreshing NOW cannot force source projects to update. If APT WATCH, FX WATCH or the Seoul records tracker stops releasing files, NOW retains the last dated card and never labels an old number as today's reading. A failed source does not replace prior snapshots with zeros. The generator is intentionally source-specific and does not try to invent DEBT워치 or PAY워치 daily metrics before their JSON schemas and refresh schedules are verified. Both remain discoverable as projects.

**Lee Jae-myung X Tracker:** remains in the historical PROJECTS directory, marked "automatic collection paused" because X API credentials are unavailable. The NOW automation neither scrapes X nor needs an X token. Threads uses a different Meta API.

**Security and hygiene:** no access token is needed for the daily WATCH/PROJECTS/STORIES feed. Keep Meta token only in the `THREADS_ACCESS_TOKEN` Actions secret for the *separate* Threads workflow. The frontend and history JSON contain no API tokens. The watch feed is one dated item per service per day, replaced if the upstream revises its data on the same date, and capped to 180 most recent watch items; project events are created when a new card is detected.

```bash
python scripts/build_now_activity.py
python -m http.server 8080
# open /now/
```

The script needs network access to read published source data; GitHub Actions provides it. The released `now/activity.json` may initially include only the verified BOK item and the existing 26 projects until the first successful scheduled/manual collection.

## Editorial project stories

Every one of the 26 previously existing projects has an individually edited 400–500 character narrative in `now/project-stories.json`. The NOW feed shows this `story` instead of the one-line archive teaser, with the original project thumbnail and direct service link. The content is grounded in each project's existing detail page. The generator validates the supplied story length on each run and retains it when revising project metadata. Newly detected projects can enter the feed automatically with their ordinary card teaser; a reviewed 400–500 character story should be added to the same file for full publication. No fictional launch dates are assigned to existing projects.

BOK WATCH NOW headline is intentionally short: next meeting date, probability, genuine week-over-week change (if a comparable historical snapshot exists), correct primary model source, observation date and expected policy rate. The long internal `memo.json` is not an appropriate social post, and its currently misleading `CD 91일` label must not propagate to NOW. Source snapshot for 2026-11-20 reports 68.0% under **1-month synthetic KOFR OIS**, 77.67% on 2026-11-13, and an expected policy rate of 3.17%.
