#!/usr/bin/env python3
"""Sync *owned* Meta Threads posts into databrew NOW without publishing a token.
Runs in GitHub Actions; never use a Graph access token in frontend JavaScript.
"""
import datetime as dt
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEST = ROOT / "now" / "threads.json"
BASE = "https://graph.threads.net/v1.0/"
TOKEN = os.environ.get("THREADS_ACCESS_TOKEN", "").strip()


def graph(path, fields=None, limit=None):
    query = {"access_token": TOKEN}
    if fields:
        query["fields"] = fields
    if limit:
        query["limit"] = str(limit)
    url = BASE + path + "?" + urllib.parse.urlencode(query)
    # A failed request must never print the credential-bearing URL.
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "databrew-now/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            return json.load(resp)
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        raise RuntimeError("Threads API request failed (credentials omitted)") from None


def sync():
    if not TOKEN:
        print("THREADS_ACCESS_TOKEN is not configured; no changes made.")
        return 0
    identity = graph("me", fields="id,username")
    username = identity.get("username", "")
    if not re.fullmatch(r"[A-Za-z0-9_.]{1,30}", username):
        raise RuntimeError("Threads username missing or invalid")
    response = graph("me/threads", fields="id,text,media_type,media_url,thumbnail_url,permalink,timestamp", limit=50)
    if "data" not in response or not isinstance(response["data"], list):
        raise RuntimeError("Threads API did not return a posts list")
    posts = []
    for item in response["data"]:
        permalink = str(item.get("permalink") or "")
        parsed = urllib.parse.urlparse(permalink)
        if parsed.scheme != "https" or parsed.hostname not in ("www.threads.com", "threads.com", "www.threads.net", "threads.net"):
            continue
        if not item.get("id") or not item.get("timestamp"):
            continue
        posts.append({
            "id": str(item["id"]),
            "text": str(item.get("text") or ""),
            "timestamp": str(item["timestamp"]),
            "permalink": permalink,
            "media_type": str(item.get("media_type") or ""),
            "media_url": str(item.get("media_url") or ""),
            "thumbnail_url": str(item.get("thumbnail_url") or ""),
        })
    posts.sort(key=lambda p: p["timestamp"], reverse=True)
    old = {}
    if DEST.exists():
        old = json.loads(DEST.read_text(encoding="utf-8"))
    profile = "https://www.threads.com/@" + username
    if old.get("posts") == posts and old.get("profile_url") == profile:
        print("Threads content unchanged; no repository commit needed.")
        return 0
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    payload = {"updated_at": now, "profile_url": profile, "posts": posts}
    DEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Synced", len(posts), "Threads posts (text and public permalinks only).")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(sync())
    except Exception as exc:
        print("Threads sync failed:", str(exc), file=sys.stderr)
        sys.exit(1)
