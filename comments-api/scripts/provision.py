#!/usr/bin/env python3
"""One-click authenticated Cloudflare bootstrap for databrew NOW guest comments.

This runs INSIDE GitHub Actions after the repository owner explicitly adds
Cloudflare credentials. It never prints or commits any credential.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "comments-api"
PUBLIC = ROOT / "now" / "comments-config.json"
TOML = APP / "wrangler.deploy.toml"  # explicitly ignored; never committed
API = "https://api.cloudflare.com/client/v4"
WORKER = "databrew-now-comments"
D1 = "databrew-now-comments"
WIDGET_NAME = "databrew NOW comments"
HOST = "raspos.github.io"
ORIGIN = "https://" + HOST


def required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing GitHub Actions secret: {name}")
    return value


def api(method: str, path: str, token: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        API + path, data=data, method=method,
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "databrew-comments-setup/1.0",
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=35) as response:
            result = json.load(response)
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"Cloudflare API HTTP {error.code} on {method} resource request") from None
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        raise RuntimeError("Cloudflare API request failed (credentials omitted)") from None
    if not isinstance(result, dict) or result.get("success") is not True:
        # Do not print raw Cloudflare responses; they may contain credentials.
        raise RuntimeError(f"Cloudflare {method} resource request was rejected")
    return result


def d1_database(account: str, token: str) -> str:
    path = f"/accounts/{account}/d1/database"
    query = urllib.parse.urlencode({"name": D1, "per_page": 100})
    found = api("GET", path + "?" + query, token).get("result") or []
    for item in found:
        if item.get("name") == D1 and item.get("uuid"):
            print("Reusing existing D1 database.")
            return str(item["uuid"])
    created = api("POST", path, token, {"name": D1}).get("result") or {}
    database_id = created.get("uuid")
    if not database_id:
        raise RuntimeError("D1 database created without an ID")
    print("Created dedicated D1 database.")
    return str(database_id)


def turnstile(account: str, token: str) -> tuple[str, str]:
    path = f"/accounts/{account}/challenges/widgets"
    widgets = []
    # Handles accounts with many unrelated Turnstile widgets.
    page = 1
    while True:
        response = api("GET", path + "?" + urllib.parse.urlencode({"page": page, "per_page": 50}), token)
        batch = response.get("result") or []
        widgets.extend(batch)
        pages = response.get("result_info") or {}
        if not batch or page >= int(pages.get("total_pages") or 1):
            break
        page += 1
        if page > 25:
            raise RuntimeError("Turnstile widget inventory unexpectedly large")
    candidates = [item for item in widgets if item.get("name") == WIDGET_NAME]
    if len(candidates) > 1:
        raise RuntimeError("Several widgets share the databrew name; resolve duplicates in Cloudflare")
    if candidates:
        candidate = candidates[0]
        if sorted(candidate.get("domains") or []) != [HOST]:
            raise RuntimeError("Existing databrew Turnstile widget has unexpected allowed hostnames")
        sitekey = str(candidate.get("sitekey") or "")
        if not sitekey:
            raise RuntimeError("Existing Turnstile widget has no site key")
        detail = api("GET", path + "/" + urllib.parse.quote(sitekey, safe=""), token).get("result") or {}
        secret = str(detail.get("secret") or "")
        if not secret:
            raise RuntimeError("Turnstile secret not available; verify Cloudflare permissions")
        print("Reusing existing Turnstile widget.")
        return sitekey, secret
    created = api("POST", path, token, {
        "domains": [HOST], "mode": "managed", "name": WIDGET_NAME,
    }).get("result") or {}
    key = str(created.get("sitekey") or "")
    secret = str(created.get("secret") or "")
    if not key or not secret:
        raise RuntimeError("Cloudflare created a widget but omitted required keys")
    print("Created host-restricted managed Turnstile widget.")
    return key, secret


def worker_subdomain(account: str, token: str) -> str:
    result = api("GET", f"/accounts/{account}/workers/subdomain", token).get("result") or {}
    value = str(result.get("subdomain") or "")
    if not value or not value.replace("-", "").isalnum():
        raise RuntimeError("workers.dev subdomain not configured in Cloudflare account")
    return value


def config_file(db_id: str) -> None:
    import uuid
    try:
        uuid.UUID(db_id)
    except ValueError:
        raise RuntimeError("Cloudflare returned an invalid D1 database identifier") from None
    content = f'''name = "{WORKER}"
main = "src/index.js"
compatibility_date = "2026-10-01"
workers_dev = true

[[d1_databases]]
binding = "DB"
database_name = "{D1}"
database_id = "{db_id}"

[vars]
ALLOWED_ORIGIN = "{ORIGIN}"
TURNSTILE_HOSTNAME = "{HOST}"
'''
    TOML.write_text(content, encoding="utf-8")


def wrangler(*command: str, private_input: str | None = None) -> None:
    result = subprocess.run(
        ["npx", "--no-install", "wrangler", *command, "--config", TOML.name],
        cwd=APP,
        input=private_input, text=True, check=False,
        capture_output=True, timeout=180,
    )
    if result.returncode != 0:
        # Wrangler may include the request/body in stdout or stderr.
        # Fail closed without printing potentially sensitive CLI output.
        raise RuntimeError("Wrangler " + " ".join(command[:2]) + " failed; inspect Cloudflare resource setup")


def set_secret(key: str, value: str) -> None:
    wrangler("secret", "put", key, private_input=value + "\n")


def health(url: str) -> None:
    # Only expose public config when the deployed Worker can read D1 schema.
    for path in ("/health", "/api/comments?post=watch%3Asetup-check"):
        req = urllib.request.Request(url + path, headers={
            "Accept": "application/json", "Origin": ORIGIN,
        })
        try:
            with urllib.request.urlopen(req, timeout=25) as response:
                payload = json.load(response)
        except (urllib.error.URLError, ValueError, TimeoutError, OSError):
            raise RuntimeError("Deployed Worker health/D1 check failed; public config unchanged") from None
        if path == "/health" and (payload.get("status") != "ok" or payload.get("storage") is not True):
            raise RuntimeError("Deployed Worker did not report a healthy D1 binding")
        if path.startswith("/api/comments") and not isinstance(payload.get("comments"), list):
            raise RuntimeError("Deployed Worker cannot query the comments table")


def main() -> int:
    token = required("CLOUDFLARE_API_TOKEN")
    account = required("CLOUDFLARE_ACCOUNT_ID")
    admin_token = required("DATABREW_COMMENTS_ADMIN_TOKEN")
    if len(admin_token) < 32:
        raise RuntimeError("DATABREW_COMMENTS_ADMIN_TOKEN must be at least 32 characters")
    if len(account) != 32 or not all(c in "0123456789abcdefABCDEF" for c in account):
        raise RuntimeError("CLOUDFLARE_ACCOUNT_ID must be the 32-character account ID")
    # Wrangler's own authentication uses exactly the same short-lived Actions secrets.
    os.environ["CLOUDFLARE_API_TOKEN"] = token
    os.environ["CLOUDFLARE_ACCOUNT_ID"] = account

    db_id = d1_database(account, token)
    sitekey, turnstile_secret = turnstile(account, token)
    subdomain = worker_subdomain(account, token)
    url = f"https://{WORKER}.{subdomain}.workers.dev"
    config_file(db_id)

    print("Initializing remote D1 schema.")
    wrangler("d1", "execute", D1, "--remote", "--file=./schema.sql")
    print("Deploying databrew guest-comment Worker.")
    wrangler("deploy")
    # Derive a stable rate-limit salt without exposing another secret or
    # coupling plain IP hashes to a public identifier.
    salt = hashlib.sha256(("databrew-ip-rate-v1:" + admin_token).encode()).hexdigest()
    for key, value in (
        ("TURNSTILE_SECRET", turnstile_secret),
        ("COMMENT_HASH_SALT", salt),
        ("ADMIN_TOKEN", admin_token),
    ):
        set_secret(key, value)
        print("Installed protected Worker secret:", key)

    health(url)
    PUBLIC.write_text(
        json.dumps({"api_base": url, "turnstile_site_key": sitekey}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print("Worker GET/D1 health verified. Public config ready for GitHub Pages.")
    print("Public API origin:", url)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:
        print("Provisioning stopped:", error, file=sys.stderr)
        sys.exit(1)
