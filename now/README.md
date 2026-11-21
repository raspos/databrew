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

The `Build databrew NOW daily feed` GitHub Action runs twice a day, at **11:00 and 23:00 KST** (02:00/14:00 UTC; Actions may start late), and supports manual dispatch. It reads *already published, public* source JSON without inventing data:

| NOW item | Input | Observation-date rule |
| --- | --- | --- |
| BOK워치 | BOK `meta.json` + dated `snapshots/YYYY-MM-DD.json` | **50% 1-month synthetic KOFR OIS + 50% 91-day monetary stabilization bond (통안증권 91일)**; 91-day model uses BOK's `min_hike` method with all in-tenor policy meetings; CD91 original result is a calibration-only cross-check |
| FX워치 | `https://raspos.github.io/fx-odds/data/latest.json` | `base_date` (ECOS reference rate; never call it the 15:30 closing price) |
| APT워치 | `https://raspos.github.io/apt-watch/data.json` | `negoIndex.asOf` or asking last success; withhold numeric index if verification is held |
| 서울 아파트 신고가 | `https://raspos.github.io/seoul-apartment-tracker/data/{meta.json,daily.json.gz}` | `snapshotDate`; show the last 30 *contract dates*' records and delayed-reporting caveat |
| Existing and new projects | Current `index.html` project cards | Old projects have no invented launch date; newly detected projects get first-seen timestamp |
| STORIES | Current `articles.json`, article source HTML, and `now/story-summaries.json` | 4–5 line verified editorial summary; new articles fall back to 4–5 literal source excerpts, not AI guesses |
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

Every one of the 26 previously existing projects has an individually edited, roughly 3–4-line, 90–150 character introduction in `now/project-stories.json`. The NOW feed shows this `story` instead of the one-line archive teaser, with the original project thumbnail and direct service link. The content is grounded in each project's existing detail page. The generator validates the supplied story length on each run and retains it when revising project metadata. Newly detected projects can enter the feed automatically with their ordinary card teaser; a reviewed concise 90–150 character introduction should be added to the same file for full publication. No fictional launch dates are assigned to existing projects.

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

## Guest comments and per-post sharing on NOW

NOW's WATCH/STORIES/PROJECTS cards now display `댓글` and `공유`. Comments are **nickname-only with no GitHub login, no other user login and no email field**. Imported Threads posts still link to their original Threads discussion; there is no duplicate third-party conversation.

### Status: source code prepared; public backend must be deployed separately

The public GitHub Pages site cannot itself save comments. The backend in `../comments-api/` is a Cloudflare Worker that uses D1 as the comment database, Turnstile for bot checks and an admin-only moderation API. Its source is deployed with the owner's Cloudflare account, not GitHub Pages. The checked-in `now/comments-config.json` deliberately has blank values: **do not claim guest comments already work publicly until the Worker, D1 and site key are configured**. With blank configuration the button gives a clear "service being connected" notice. Existing sharing continues to work.

### One-time Cloudflare setup

1. Sign in at [Cloudflare dashboard](https://dash.cloudflare.com/) and install Cloudflare's Wrangler CLI, or run the commands below from a shell with Node.js installed.
2. Navigate to the repo's `comments-api` folder and run `npx wrangler login`.
3. Create a D1 database:
   `npx wrangler d1 create databrew-now-comments`
   Copy the generated `database_id` into the **`comments-api/wrangler.toml`** field `REPLACE_WITH_D1_DATABASE_ID`. (This is an identifier, not a password.)
4. Initialize the remote database using the **existing schema**:
   `npx wrangler d1 execute DB --remote --file=./schema.sql`
   Run this command **after** `wrangler.toml` contains the correct D1 database ID. A local-only database would not save real readers' comments.
5. In [Cloudflare Turnstile](https://dash.cloudflare.com/?to=/:account/turnstile), create a widget for `raspos.github.io`. Copy its **public site key** and separately note the **secret key**. Turnstile runs on the static NOW page; the Worker checks every token via Cloudflare's server-side Siteverify API. Do not use the Turnstile secret in NOW JavaScript.
6. Set three private Worker secrets, one at a time (Wrangler prompts for the value):
   ```sh
   npx wrangler secret put TURNSTILE_SECRET
   npx wrangler secret put COMMENT_HASH_SALT
   npx wrangler secret put ADMIN_TOKEN
   ```
   `COMMENT_HASH_SALT` and `ADMIN_TOKEN` should be independent long random strings (prefer at least 32 random bytes). Keep them away from Git commits, chats, and web code. These tokens are separate from Meta Threads or GitHub Actions credentials.
7. Deploy:
   `npx wrangler deploy`
   Note the HTTPS Worker endpoint reported by Cloudflare, e.g. `https://databrew-now-comments.<your-subdomain>.workers.dev`. This is an example, not a configured or verified URL.
8. Edit the publicly readable **`now/comments-config.json`**:
   ```json
   {
     "api_base": "https://databrew-now-comments.YOUR-SUBDOMAIN.workers.dev",
     "turnstile_site_key": "YOUR-PUBLIC-TURNSTILE-SITE-KEY"
   }
   ```
   Commit that file. **Only** the public Worker URL and public site key belong there; none of the three secrets does.
9. Open [NOW](https://raspos.github.io/databrew/now/) on mobile and desktop. Click `댓글` on a WATCH/STORY/PROJECT, enter a nickname and comment, complete Turnstile, and check that the form says the comment is awaiting moderation. On the same card, `공유` should still offer Threads, X, Facebook, link copy, and device sharing when supported.

Cloudflare's [D1 database API](https://developers.cloudflare.com/d1/worker-api/), [D1 execute commands](https://developers.cloudflare.com/workers/wrangler/commands/d1/), and [Turnstile verification](https://developers.cloudflare.com/turnstile/get-started/server-side-validation/) document the underlying features.

### Moderate submitted comments

All newly submitted comments have status `pending`; **nothing appears publicly until an administrator approves it**. Use the Worker URL and private `ADMIN_TOKEN` (never entered into a public NOW browser window):

```sh
# List unpublished comments.
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
  "https://YOUR-WORKER-URL/api/admin/comments?status=pending"

# Approve a single comment.
curl -X POST -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"action":"approve"}' \
  "https://YOUR-WORKER-URL/api/admin/comments/COMMENT-ID"

# Reject or delete: action = reject or delete.
```

After approval a reader opening or refreshing the same NOW comment panel can see the newly published comment.

### Abuse controls and privacy

- Nicknames are 2–24 characters; comments are 2–1,000 characters. No password, email or account required.
- Cloudflare Turnstile is mandatory and validated **server-side**, including the expected site hostname. A hidden honeypot, rate limit (up to three submissions per 10 minutes or 12 per 24 hours per privacy-preserving IP hash), repeated-text check and owner moderation reduce spam.
- The Worker does **not store plain IP addresses**. It stores HMAC-hashed IP data for abuse throttling with a private salt. Treat even hashed metadata as privacy-relevant and define a retention/deletion policy before a large public launch. Only nickname, comment and submission date are exposed on approved public posts.
- The browser only accepts API results as text (`textContent`), never evaluates comment HTML or allows comment scripts. Worker endpoints use parameterized D1 queries and origin restrictions.
- A short-lived D1/service outage should show a normal error state; no fake local comments are created. No real user data is claimed until Cloudflare has been deployed and tested.

### Per-post sharing

The `공유` menu remains available without Cloudflare or GitHub: Threads, X, Facebook, copy link, and optional native sharing for mobile apps. The shared URL points to a specific NOW item using the stable `?filter=...&item=...` query parameters. Individual article Open Graph previews require future pre-rendered public URLs; query parameters alone share the NOW page's overall OG image/title.
