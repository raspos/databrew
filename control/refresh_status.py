#!/usr/bin/env python3
"""Refresh public GitHub metadata for DataBREW CONTROL.

The public dashboard does NOT access GitHub credentials. This runs in CI,
makes requests with GITHUB_TOKEN, and publishes only public repo metadata.
Private repository information is intentionally withheld.
"""
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
PROJECTS = BASE / "projects.json"
DEST = BASE / "status.json"
TOKEN = os.getenv("GITHUB_TOKEN", "")
API = "https://api.github.com/"
ALLOWED = {"raspos/" + p for p in (
    "bokwatch", "fx-odds", "pay-watch", "apt-watch",
    "personnel-craft", "hongdam-craft", "reconstruction-craft",
    "e-war", "se-young-archive", "all-time-xi", "ramen-genealogy",
    "chip-cycle", "korea-ranked", "korea-corporate-scorecard",
    "honmaek-map", "balchik-imagination", "seoul-apartment-tracker",
    "korean-newsroom-hub", "korean-newsroom-mcp",
    "bok-governor", "sahoegwabudo", "major-formula",
)}
def get(path):
    req = urllib.request.Request(API + path, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "databrew-control-monitor",
        **({"Authorization": "Bearer " + TOKEN} if TOKEN else {}),
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            return json.load(res)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError) as exc:
        print("Unavailable", path, type(exc).__name__)
        return None

def main():
    src = json.loads(PROJECTS.read_text(encoding="utf-8"))
    old = {}
    if DEST.exists():
        try:
            old = json.loads(DEST.read_text(encoding="utf-8")).get("repositories", {})
        except (ValueError, OSError):
            pass
    repos = sorted({p.get("repo") for p in src.get("projects", []) if p.get("repo") in ALLOWED})
    output = {}
    for repo in repos:
        info = get("repos/" + repo)
        if not isinstance(info, dict):
            # Fail closed: do not publish stale state as though it were fresh.
            continue
        if info.get("private") or info.get("visibility") not in (None, "public"):
            continue
        runs = get("repos/" + repo + "/actions/runs?per_page=1")
        latest = (runs.get("workflow_runs") or [None])[0] if isinstance(runs, dict) else None
        output[repo] = {
            "pushed_at": info.get("pushed_at"),
            "default_branch": info.get("default_branch"),
            "last_workflow": ({
                "name": latest.get("name"),
                "status": latest.get("status"),
                "conclusion": latest.get("conclusion"),
                "created_at": latest.get("created_at"),
                "html_url": latest.get("html_url"),
            } if latest else None),
        }
    content = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "repositories": output,
        "coverage": {"public_repositories_checked": len(repos),
                     "public_repositories_reported": len(output)},
        "disclaimer": "Last workflow status is not a data quality certification."
    }
    # Date changes daily; preserves an observable last-run timestamp.
    DEST.write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Published", len(output), "public repositories")

if __name__ == "__main__":
    main()
