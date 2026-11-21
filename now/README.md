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
