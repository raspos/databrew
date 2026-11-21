#!/usr/bin/env python3
"""Publish new, source-dated databrew NOW entries to Meta Threads.

Requires a user-authorized Threads long-lived token in a GitHub Actions secret,
and THREADS_PUBLISH_ENABLED=true as a separate repository variable.
No token, preview, unpublished historic posts, or inbound Threads content is
ever sent to Meta without the explicitly enabled workflow.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "now" / "activity.json"
STATE = ROOT / "now" / "threads-publication.json"
API = "https://graph.threads.net/v1.0"
NOW_URL = "https://raspos.github.io/databrew/now/"
KST = ZoneInfo("Asia/Seoul")
MAX_CHARS = 500
MAX_ITEMS = 4
MAX_PARTS = 4


def enabled(value: str | None) -> bool:
    return str(value or "").strip().lower() == "true"


def stamp() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def load_json(path: Path, default: dict) -> dict:
    if not path.exists():
        return default
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError(f"{path.name}: expected object")
    return obj


def write_state(state: dict, path: Path = STATE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def initial_state() -> dict:
    return {"version": 1, "initialized_at": None, "seen": {},
            "pending": {}, "published": []}


def now_item_link(kind: str, ident: str) -> str:
    return NOW_URL + "?" + urlencode({"filter": kind, "item": ident})


def within(day: str, days: int, today: dt.date) -> bool:
    try:
        age = (today - dt.date.fromisoformat(day[:10])).days
    except (ValueError, TypeError):
        return False
    return 0 <= age <= days


def candidates(activity: dict, today: dt.date | None = None) -> list[dict]:
    """Only fresh WATCH/STORIES and *new* projects. Never mirror inbound Threads."""
    today = today or dt.datetime.now(KST).date()
    collected = []
    for post in activity.get("watch", []):
        if not isinstance(post, dict) or not all(post.get(k) for k in ("id", "day", "title", "text", "url")):
            continue
        if not within(post["day"], 3, today):
            continue
        collected.append({"kind": "watch", "id": str(post["id"]),
                          "day": post["day"], "title": post["title"],
                          "text": post["text"]})
    for post in activity.get("stories", []):
        if not isinstance(post, dict) or not all(post.get(k) for k in ("id", "day", "title")):
            continue
        lines = post.get("summary_lines")
        if not within(post["day"], 14, today) or not isinstance(lines, list) or len(lines) < 4:
            continue
        if not all(isinstance(line, str) and line.strip() for line in lines):
            continue
        collected.append({"kind": "stories", "id": str(post["id"]), "day": post["day"],
                          "title": post["title"], "text": "\n".join(lines)})
    for post in activity.get("projects", []):
        if not isinstance(post, dict) or not all(post.get(k) for k in ("id", "name", "story", "first_seen")):
            continue
        if not within(post["first_seen"], 14, today):
            continue
        collected.append({"kind": "projects", "id": str(post["id"]),
                          "day": post["first_seen"][:10], "title": post["name"],
                          "text": post["story"]})
    collected.sort(key=lambda p: (p["day"], {"watch": 2, "stories": 1, "projects": 0}[p["kind"]], p["id"]), reverse=True)
    return collected


def source_key(post: dict) -> str:
    return post["kind"] + ":" + post["id"]


def digest(post: dict) -> str:
    body = json.dumps(post, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()[:24]


def chunks_for(post: dict) -> list[str]:
    """Keep the complete verified NOW text; split at words into a reply chain."""
    title = str(post["title"]).strip()
    body = re.sub(r"\s+", " ", str(post["text"]).strip())
    link = now_item_link(post["kind"], post["id"])
    label = {"watch": "WATCH", "stories": "STORY", "projects": "PROJECT"}[post["kind"]]
    header = label + " | " + title + "\n\n"
    suffix = "\n\nNOW 원문: " + link
    first_room = MAX_CHARS - len(header) - len(suffix) - 10
    other_room = MAX_CHARS - len("이어지는 글\n\n") - 10
    if first_room < 80:
        raise ValueError("NOW item title or URL too long for Threads: " + source_key(post))
    words = body.split(" ")
    pieces, current, limit = [], "", first_room
    for word in words:
        if len(word) > limit:
            raise ValueError("Unbroken text exceeds Threads limit: " + source_key(post))
        next_text = (current + " " + word).strip()
        if len(next_text) > limit:
            pieces.append(current)
            current, limit = word, other_room
        else:
            current = next_text
    if current:
        pieces.append(current)
    if not pieces or len(pieces) > MAX_PARTS:
        raise ValueError("NOW post requires too many Threads replies: " + source_key(post))
    result = [header + pieces[0] + suffix]
    result.extend("이어지는 글\n\n" + rest for rest in pieces[1:])
    if any(len(part) > MAX_CHARS for part in result):
        raise AssertionError("Threads length calculation failed")
    if " ".join(pieces) != body:
        raise AssertionError("NOW text would have been lost")
    return result


class GraphClient:
    def __init__(self, access_token: str, expected_username: str = ""):
        if not access_token:
            raise ValueError("Missing Threads access token")
        self.access_token = access_token
        self.expected_username = expected_username.lstrip("@").strip().casefold()

    def request(self, path: str, form: dict | None = None) -> dict:
        url = API + "/" + path.lstrip("/")
        data = urlencode(form).encode("utf-8") if form is not None else None
        req = Request(url, data=data, headers={
            "Authorization": "Bearer " + self.access_token,
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "databrew-now-threads/1.0",
        }, method="POST" if data is not None else "GET")
        try:
            with urlopen(req, timeout=30) as response:
                payload = json.load(response)
        except HTTPError as error:
            raise RuntimeError("Meta Threads API HTTP " + str(error.code) + " (body/redacted)") from None
        except (URLError, TimeoutError, OSError, ValueError):
            raise RuntimeError("Meta Threads API request failed; credentials omitted") from None
        if not isinstance(payload, dict) or payload.get("error"):
            raise RuntimeError("Meta Threads API returned an invalid response (redacted)")
        return payload

    def identity(self) -> str:
        result = self.request("me?fields=id,username")
        ident, actual = result.get("id"), str(result.get("username") or "").casefold()
        if not ident or not actual:
            raise RuntimeError("Meta Threads identity or username missing")
        if self.expected_username and actual != self.expected_username:
            raise RuntimeError("Meta Threads token belongs to a different account; publication blocked")
        return str(ident)

    def publish_text(self, text: str, reply_to_id: str | None = None) -> str:
        if not text or len(text) > MAX_CHARS:
            raise ValueError("Threads text invalid or longer than 500 characters")
        args = {"media_type": "TEXT", "text": text}
        if reply_to_id:
            args["reply_to_id"] = reply_to_id
        created = self.request("me/threads", args)
        if not created.get("id"):
            raise RuntimeError("Threads container ID missing; publication uncertain")
        published = self.request("me/threads_publish", {"creation_id": str(created["id"])})
        if not published.get("id"):
            raise RuntimeError("Threads publication ID missing; publication uncertain")
        return str(published["id"])


def mark_seen(state: dict, post: dict) -> None:
    key, signature = source_key(post), digest(post)
    signatures = state["seen"].setdefault(key, [])
    if signature not in signatures:
        signatures.append(signature)
        # Bound history per source key; editions are immutable after publishing.
        del signatures[:-8]


def publish_one(client: GraphClient, state: dict, post: dict,
                state_path: Path = STATE) -> None:
    key, signature = source_key(post), digest(post)
    pending_key = key + "@" + signature
    parts = chunks_for(post)
    pending = state["pending"].setdefault(pending_key, {"ids": [], "inflight": None})
    write_state(state, state_path)
    if pending["inflight"] is not None:
        raise RuntimeError("Previous Threads request may have succeeded; manual audit required for " + key)
    if len(pending["ids"]) > len(parts):
        raise ValueError("Pending Threads replies exceed post length")
    for index in range(len(pending["ids"]), len(parts)):
        # Persist uncertain in-flight state *before* contacting Meta to avoid
        # silent duplicate posts when Graph responds with a timeout.
        pending["inflight"] = index
        write_state(state, state_path)
        reply_to = pending["ids"][-1] if pending["ids"] else None
        media_id = client.publish_text(parts[index], reply_to)
        pending["ids"].append(media_id)
        pending["inflight"] = None
        write_state(state, state_path)
    mark_seen(state, post)
    state["published"].append({
        "key": key, "digest": signature, "thread_id": pending["ids"][0],
        "reply_ids": pending["ids"][1:], "source_day": post["day"],
        "published_at": stamp(),
    })
    del state["pending"][pending_key]
    state["published"] = state["published"][-300:]
    write_state(state, state_path)


def run(activity_path: Path = SOURCE, state_path: Path = STATE,
        client: GraphClient | None = None, today: dt.date | None = None,
        dry_run: bool = False, backfill_latest: bool = False,
        max_items: int = MAX_ITEMS) -> int:
    activity = load_json(activity_path, {})
    state = load_json(state_path, initial_state())
    if state.get("version") != 1 or not isinstance(state.get("seen"), dict) or not isinstance(state.get("pending"), dict):
        raise ValueError("Threads publication state is corrupt")
    posts = candidates(activity, today)
    new = [post for post in posts if digest(post) not in state["seen"].get(source_key(post), [])]
    if backfill_latest and state.get("initialized_at"):
        # An explicit admin backfill may recover previously checkpointed but
        # *never published* recent entries. Published digests remain immutable.
        already_sent = {(r["key"], r["digest"]) for r in state["published"]}
        for post in posts[:max_items]:
            if (source_key(post), digest(post)) not in already_sent and post not in new:
                new.append(post)
        new.sort(key=lambda p: (p["day"], {"watch": 2, "stories": 1, "projects": 0}[p["kind"]], p["id"]), reverse=True)
    print("NOW candidate count:", len(posts), "unseen editions:", len(new))
    for post in new[:max_items]:
        parts = chunks_for(post)
        print(("DRY RUN " if dry_run else "QUEUED ") + source_key(post),
              str(len(parts)) + " Threads part(s),",
              str(max(len(s) for s in parts)) + "/500 chars (longest)")
    if dry_run:
        return 0

    if client is None:
        # Only repository admins can authorize live posting via the secret +
        # repository variable. A missing token or switch means no side effect.
        if not enabled(os.environ.get("THREADS_PUBLISH_ENABLED")):
            print("Threads outbound publication disabled (repository variable).")
            return 0
        token = os.environ.get("THREADS_ACCESS_TOKEN", "").strip()
        if not token:
            print("Threads access token not configured; no publication attempted.")
            return 0
        expected = os.environ.get("THREADS_EXPECTED_USERNAME", "").strip().lstrip("@")
        if not expected:
            print("Target Threads username not configured; no publication attempted.")
            return 0
        client = GraphClient(token, expected)

    # Check the uncertain-request guard only when live publication is enabled.
    # Turning the feature off must never create failing scheduled actions.
    pending = [key for key, value in state["pending"].items() if value.get("inflight") is not None]
    if pending:
        raise RuntimeError("Publication blocked by uncertain in-flight request; audit Threads first: " + ", ".join(pending))

    if not state.get("initialized_at"):
        # Validate token BEFORE creating any durable state or posting content.
        client.identity()
        state["initialized_at"] = stamp()
        if not backfill_latest:
            for post in posts:
                mark_seen(state, post)
            write_state(state, state_path)
            print("Initialized publication checkpoint; existing NOW history not cross-posted.")
            return 0
        # Explicit one-time backfill of the latest few items; remaining historical
        # items are checkpointed, not queued for later accidental bulk posting.
        to_send = new[:max_items]
        for post in posts:
            if post not in to_send:
                mark_seen(state, post)
        write_state(state, state_path)

    client.identity()
    processed = 0
    for post in new[:max_items]:
        publish_one(client, state, post, state_path)
        processed += 1
        print("Published:", source_key(post), "source day", post["day"])
    print("Threads completed:", processed, "NOW entries")
    return 0


def main() -> int:
    try:
        return run(
            dry_run=enabled(os.environ.get("THREADS_DRY_RUN")),
            backfill_latest=enabled(os.environ.get("THREADS_BACKFILL_LATEST")),
            max_items=MAX_ITEMS,
        )
    except Exception as exc:
        print("NOW→Threads stopped:", str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
