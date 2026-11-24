# NOW — databrew rolling data-journalism feed

The NOW feed combines official WATCH updates, real databrew STORIES, project introductions, and an optional inbound Meta Threads mirror. A separate opt-in automation can now publish new NOW content to Meta Threads; there are no fabricated posts.

## Connect an actual Meta Threads account

1. Create/configure a Meta Threads developer app for the Threads account and authorize it with the read permission (`threads_basic`).
2. Exchange for a valid access token as described in [Meta's Threads API documentation](https://www.postman.com/meta/threads/collection/dht3nzz/threads-api).
3. Add the token as the `THREADS_ACCESS_TOKEN` GitHub **Actions repository secret** (not a variable, not a committed file). Never share it in a chat or put it in GitHub Pages JavaScript.
4. To enable inbound mirroring separately, set the GitHub Actions repository variable `THREADS_SYNC_ENABLED=true`, then run **Sync Threads to databrew NOW** manually. Its recurring schedule is approximately every four hours.
5. Check `now/threads.json` for an `updated_at`, a Threads profile URL, and an array of publicly viewable posts. The frontend then displays a real Threads follow link and per-post links to comments/conversation on Threads.

Authentication and long-lived token refresh/rotation remain administrator duties. Expired token errors appear in the GitHub Action logs, not on the public site. The script never guesses a profile URL. Do not add credentials in files or browser scripts.

### Current scope and limitations

- Optional inbound sync: Threads → NOW. Separately opt-in to NOW → Threads posting with `THREADS_PUBLISH_ENABLED=true`; these two directions can be enabled independently.
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

The `Build databrew NOW daily feed` GitHub Action checks sources **six times daily** at approximately **01:23, 05:23, 09:23, 13:23, 17:23, and 21:23 KST** (UTC: 16:23, 20:23, 00:23, 04:23, 08:23, 12:23; GitHub Actions may be delayed). The schedule is intentionally offset from minute :00. It supports manual dispatch and reads *already published, public* source JSON without inventing data:

| NOW item | Input | Observation-date rule |
| --- | --- | --- |
| BOK워치 | BOK `meta.json` + dated `snapshots/YYYY-MM-DD.json` | **50% 1-month synthetic KOFR OIS + 50% 91-day monetary stabilization bond (통안증권 91일)**; 91-day model uses BOK's `min_hike` method with all in-tenor policy meetings; CD91 original result is a calibration-only cross-check |
| FX워치 | `https://raspos.github.io/fx-odds/data/latest.json` | `base_date` (ECOS reference rate; never call it the 15:30 closing price) |
| APT워치 | `https://raspos.github.io/apt-watch/data.json` | `negoIndex.asOf` or asking last success; withhold numeric index if verification is held |
| 서울 아파트 신고가 | `https://raspos.github.io/seoul-apartment-tracker/data/{meta.json,daily.json.gz}` | `snapshotDate`; show the last 30 *contract dates*' records and delayed-reporting caveat |
| Existing and new projects | Current `index.html` project cards | Old projects have no invented launch date; newly detected projects get first-seen timestamp |
| STORIES | Current `articles.json`, article source HTML, and `now/story-summaries.json` | 4–5 line verified editorial summary; new articles fall back to 4–5 literal source excerpts, not AI guesses |
| Threads | Existing `threads.json` | Meta's own timestamp, once the user authenticates |

**WATCH series monitor (2026-11-24):** The five WATCH projects are BOK워치, FX워치, DEBT워치, PAY워치 and APT워치. The first, second and fifth have verified daily public JSON adapters; DEBT워치 and PAY워치 currently remain clickable projects with a transparent "daily metrics not connected" label, rather than invented numbers or borrowed metrics. The **Seoul apartment record-high tracker** is a sixth, separate automated source but is not one of the five WATCH brand projects.

**What changed in the refresh workflow:** `now/source-status.json` records the last actual source check time, last observation day and whether each source was readable. It is committed even if no new data appear in `now/activity.json`. This distinguishes an operating polling job from a stalled source. A failed adapter does not erase the previous verified article. The NOW sidebar shows every WATCH service, clearly distinguishing source observation dates from check times and warning when the last check failed. In addition, a stale hard-coded integration assertion requiring BOK WATCH to always show exactly 81.3% was removed: legitimate market probability changes are no longer blocked by an old test snapshot.

**Source publish dependency:** refreshing NOW cannot force source projects to update. If APT WATCH, FX WATCH or the Seoul records tracker stops releasing files, NOW retains the last dated card and never labels an old number as today's reading. A failed source does not replace prior snapshots with zeros. The generator is intentionally source-specific and does not try to invent DEBT워치 or PAY워치 daily metrics before their JSON schemas and refresh schedules are verified. Both remain discoverable as projects.

**Lee Jae-myung X Tracker:** remains in the historical PROJECTS directory, marked "automatic collection paused" because X API credentials are unavailable. The NOW automation neither scrapes X nor needs an X token. Threads uses a different Meta API.

**Security and hygiene:** no access token is needed for the daily WATCH/PROJECTS/STORIES feed. Keep Meta token only in the `THREADS_ACCESS_TOKEN` Actions secret for the *separate* Threads workflow. The frontend and history JSON contain no API tokens. The watch feed is one dated item per service per day, replaced if the upstream revises its data on the same date, and capped to 180 most recent watch items; project events are created when a new card is detected.

```bash
python scripts/build_now_activity.py
python -m http.server 8080
# open /now/
```

The script needs network access to read published source data; GitHub Actions provides it. The released `now/activity.json` retains source-dated WATCH cards and all 27 currently registered projects. A successful source poll with unchanged observations updates the separate `source-status.json` without falsely re-dating old numbers.

## Editorial project stories

Every one of the 27 currently registered projects has an individually edited, roughly 3–4-line, 90–150 character introduction in `now/project-stories.json`. The NOW feed shows this `story` instead of the one-line archive teaser, with the original project thumbnail and direct service link. The content is grounded in each project's existing detail page. The generator validates the supplied story length on each run and retains it when revising project metadata. Newly detected projects can enter the feed automatically with their ordinary card teaser; a reviewed concise 90–150 character introduction should be added to the same file for full publication. No fictional launch dates are assigned to existing projects.

BOK WATCH NOW uses a **user-specified 50/50 ensemble** rather than copying the BOK site's OIS-only main display or the inaccurate internal `memo.json` text. On the latest source day, 2026-11-20: OIS 64.94%, MSB91 97.58% using the original `min_hike` solver, so NOW's displayed weighted hike probability is **81.26% → 81.3%**. The original CD91 solver is reproduced as a guard: 80.49%. A 91-day yield contains expectations for the November and January policy meetings, so that inferred November probability is assumption-sensitive and this is clearly disclosed. The post includes at least five factual Korean clauses without standard sentence-final verb endings.

## Frontend and STORY rendering (v3)

The databrew home page presents a slim **NOW** ticker with no introductory marketing copy. The latest eight actual WATCH/STORIES/new-project/connected-Threads posts rotate through the one-line preview, moving about every 5 seconds. Hover, keyboard focus and reduced-motion accessibility suppress automatic movement. Clicking opens the exact NOW item. The now/threads.json feed is empty until the owner authorizes Meta; no fake Threads entries are generated.

NOW displays full WATCH reports as 5+ fact-based, news-fragment clauses. Source-day, observation window, 1d/7d changes if verifiable, methodological caveat and unusual supporting moves are kept in prose, not '했습니다/입니다' sentences. STORIES use five curated lines from actual source articles where available; newly published articles can provide `now_summary` in `articles.json`, and otherwise the generator extracts 4–5 actual source paragraphs without inventing new claims. Editing summaries belongs in `now/story-summaries.json`. Existing project stories remain individually edited at 90–150 Korean characters (roughly three to four displayed lines).

Auto-publishing FROM NOW TO Meta Threads is implemented but **not live until explicitly authorized** using a long-lived token in GitHub Actions Secrets, `THREADS_PUBLISH_ENABLED=true` and `THREADS_EXPECTED_USERNAME=<handle>` in repository Variables. Follow the configuration and safety procedure below.


## NOW → Meta Threads: guarded automatic publishing

The workflow `.github/workflows/publish-now-threads.yml` runs after a successful **Build databrew NOW daily feed** workflow. It also checks at approximately **11:20 and 23:20 Korea time** as a fallback. Actions jobs may be delayed by GitHub. No service logs token values.

### Activate

1. In **Meta for Developers**, create a Threads API app and authorize the correct Threads account with `threads_basic` and `threads_content_publish` (and `threads_manage_replies` for full-length multi-post reply chains). The token must be a **Threads user token**, not an Instagram/Facebook Page token. Use Meta's [official Threads Postman collection](https://www.postman.com/meta/threads/collection/dht3nzz/threads-api) to verify credentials and request a long-lived token. The user must authorize the account; an app registration alone does not grant publishing rights.
2. In the **raspos/databrew** GitHub repo, go to **Settings → Secrets and variables → Actions → Secrets** and create the repository secret **`THREADS_ACCESS_TOKEN`**. Never paste the token into issues, PRs, chat or public JavaScript.
3. Under **Settings → Secrets and variables → Actions → Variables**, create **`THREADS_PUBLISH_ENABLED`** with value **`true`**. Also set the repository variable **`THREADS_EXPECTED_USERNAME`** to the exact intended Threads handle (without `@`). The publisher verifies that the authorized token belongs to this handle before doing anything. Missing or mismatched account configuration blocks live posting.
4. Under **Actions → Publish databrew NOW to Meta Threads → Run workflow**, leave **dry_run=true** to preview the eligible posts with no network publishing and no checkpoint change. A second manual run with **dry_run=false**, **backfill_latest=false** validates the token and creates a baseline checkpoint. Historic WATCH/STORIES/project posts are **not broadcast** in bulk.
5. After initialization, newly released or revised WATCH entries, published STORIES and genuinely new projects cross-post automatically. The source item is linked back to its exact NOW page. For a safe first live smoke test, set **dry_run=false**, **backfill_latest=true**, **max_items=1** in the manual workflow. You can then use **max_items=2** or **4** for a larger explicitly requested backfill. This also works after initialization but will not repeat an edition already recorded as published.

### Publishing behavior and limits

- The eligible sources are the latest source-dated **WATCH** (up to 3 days old), freshly published **STORIES** (up to 14 days) and newly detected **PROJECTS** with a real `first_seen` (up to 14 days). The 26 pre-existing projects are never marketed as new. Inbound Meta Threads posts cannot loop back into outbound publication.
- Scheduled runs publish up to **four NOW items**. Manual runs can limit this to **one, two or four NOW items**. Article and WATCH texts are sent in full, not replaced by AI paraphrases. If they exceed Threads' 500-character post limit, the script creates up to **four linked text posts**; part one includes the source title and exact NOW URL.
- Publication records live in `now/threads-publication.json` and store only public post IDs, item fingerprints and timestamps—not credentials. Identical item editions are suppressed on subsequent runs. Revised source text can result in a new Threads post, but source observation dates remain intact.
- The **first enabled run** defaults to checkpoint-only (zero Meta posts). Manual `dry_run=true` never posts or changes the checkpoint. An explicit manual backfill is available after initialization, with the same four-item cap and deduplication.
- Failed or uncertain Graph API POSTs are deliberately **not blindly retried**. The checkpoint records an `inflight` marker so an administrator can compare the real Threads account with the run before resolving it. The workflow commits checkpoint updates even after a failed publish; the next run refuses to duplicate a potentially successful request. A partially posted reply chain can remain visible until resolved.
- The access token is subject to Meta expiration/refresh requirements. The workflow does **not** pretend to rotate the repository secret automatically: renew/replace it as needed, ideally before the 60-day long-lived token expiry. Configure a separate renewal process before unattended long-term operation.
- `THREADS_PUBLISH_ENABLED=false` immediately disables outbound posting at the next run. Inbound collection stays disabled unless `THREADS_SYNC_ENABLED=true` is configured independently, to avoid accidentally mirroring personal Threads history onto the public NOW page.
- To revert/delete a published Threads post, use Threads itself. Removing a NOW item locally does not automatically delete a previously published Meta post.

### Local verification

```bash
python -m unittest discover -s tests -p 'test_publish_now_threads.py' -v
THREADS_DRY_RUN=true python scripts/publish_now_threads.py
```

Meta API references: [Threads official collection](https://www.postman.com/meta/threads/collection/dht3nzz/threads-api) and [text-container/reply publishing request](https://www.postman.com/meta/threads/documentation/dht3nzz/threads-api?entity=request-34203612-f8bf85ba-a2a2-47f8-9183-f94cd3e9c9d3).

## Per-post sharing and discussion (NOW cards)

Every WATCH, STORY and PROJECT entry now has a `댓글` button and a `공유` button. Threads-sourced entries use their original Threads conversation for comments, rather than duplicating that conversation in GitHub.

### Share

- `공유` opens per-post links to **Threads, X, Facebook** and a **copy-link** action; mobile browsers that support the Web Share API also show `다른 앱으로 공유` (which can offer KakaoTalk when available).
- Shared links point to the exact NOW entry, e.g. `https://raspos.github.io/databrew/now/?filter=watch&item=watch%3Abok%3A2026-11-20`. The existing NOW deep-link handler selects the correct tab, expands the feed if needed and scrolls to the entry.
- No Threads, X, Facebook or Kakao SDK keys are needed to display these links. All third-party share composers require the **reader** to complete posting; databrew does not publish using the reader's account.
- Open Graph crawlers on this static GitHub Pages site see the general NOW page metadata rather than a different title/image for every query-parameter deep link. Per-post social cards require generated static permalinks or a server-side OG metadata endpoint. The title is still prefilled for Threads and X.

### Reader comments (utterances/GitHub Issues)

This is a GitHub Pages static site with no authenticated database. Instead of displaying an unprotected fake comment form or exposing write tokens in JavaScript, NOW uses [utterances](https://utteranc.es/), an open-source GitHub-Issues-backed comment service.

1. The repository owner must install and authorize the [utterances GitHub App](https://github.com/apps/utterances) for **`raspos/databrew`** (select only this repository). This action requires an interactive GitHub administrator approval; the deployment cannot silently install an app on the owner's behalf.
2. Confirm **GitHub Issues** are enabled under the [repository's General settings](https://github.com/raspos/databrew/settings) (Features → Issues).
3. Open [NOW](https://raspos.github.io/databrew/now/), choose any WATCH, STORY or PROJECT card and press `댓글`. The first real reader comment creates an issue automatically. Each item is mapped by the permanent identity `databrew-now:<post type>:<post id>`, **not** by the changing order of the feed or the shared page pathname.
4. Visitors must authorize GitHub through utterances before posting. The discussion and replies are stored publicly as GitHub issues. Moderation is available in [databrew Issues](https://github.com/raspos/databrew/issues), including removing inappropriate comments and locking threads. Anonymous comments are not supported.
5. The external utterances script and iframe are **lazy-loaded only when a user clicks** a comment button; they are not loaded for every card or on initial page view. At most one comment drawer is open at a time. Theme changes update the active iframe.
6. Share buttons work immediately without the GitHub App. Until steps 1–2 are completed, the comments area may show an utterances access/configuration error: **do not claim live comment submission has been verified**. The GitHub App installation and a real end-to-end comment test are still required.

Discussion data is handled by GitHub, and login is required. A future anonymous/non-GitHub commenting experience would need a separate backend, moderation, anti-spam and privacy policy.
