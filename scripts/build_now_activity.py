#!/usr/bin/env python3
"""Publish databrew NOW from existing public project releases, not scraped guesses.

Sources: GitHub Pages/Cloudflare public JSON. No AI text generation, API keys,
X scraping or made-up values. Source observation dates are kept separately from
the date the NOW build runs.
"""
from __future__ import annotations

import datetime as dt
import gzip
import html
import json
import pathlib
import re
import sys
import urllib.error
import urllib.request
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "now" / "activity.json"
INDEX = ROOT / "index.html"
PROJECT_STORIES = ROOT / "now" / "project-stories.json"
KST = dt.timezone(dt.timedelta(hours=9))
BASE = {
    "bok": "https://bokwatch.pages.dev/",
    "fx": "https://raspos.github.io/fx-odds/",
    "apt": "https://raspos.github.io/apt-watch/",
    "records": "https://raspos.github.io/seoul-apartment-tracker/",
}
SOURCE_LIMIT = 32 * 1024 * 1024


def read_url(url: str, *, compressed: bool = False) -> Any:
    req = urllib.request.Request(
        url, headers={"User-Agent": "databrew-now/2.0 (+public data sync)", "Accept": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        raw = response.read(SOURCE_LIMIT + 1)
        if len(raw) > SOURCE_LIMIT:
            raise ValueError("source response exceeds size limit")
    if compressed:
        raw = gzip.decompress(raw)
    return json.loads(raw.decode("utf-8"))


def day_of(value: Any) -> str:
    match = re.match(r"^\d{4}-\d{2}-\d{2}", str(value or ""))
    if not match:
        raise ValueError("no source observation date")
    day = match.group(0)
    dt.date.fromisoformat(day)
    return day


def number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and abs(float(value)) < 1e12:
        return float(value)
    return None


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]*>", "", value))).strip()


def parse_projects() -> list[dict]:
    source = INDEX.read_text(encoding="utf-8")
    editorial = json.loads(PROJECT_STORIES.read_text(encoding="utf-8"))
    if not isinstance(editorial, dict):
        raise ValueError("project-stories.json must be an object")
    cards = re.findall(r'<article\b[^>]*class="[^"]*\bcard\b[^"]*"[^>]*>.*?</article>', source, re.S)
    projects = []
    seen = set()
    for card in cards:
        route = re.search(r'href="projects/([a-z0-9-]+)/"', card)
        heading = re.search(r"<h3(?:\s[^>]*)?>(.*?)</h3>", card, re.S)
        if not route or not heading:
            continue
        slug = route.group(1)
        if slug in seen:
            continue
        seen.add(slug)
        q = re.search(r'<p\s+class="q"[^>]*>(.*?)</p>', card, re.S)
        desc = re.search(r'<p\s+class="desc(?:\s[^"]*)?"[^>]*>(.*?)</p>', card, re.S)
        service = re.search(r'<a\s+class="btn-service"\s+href="(https?[^"]+)"', card)
        art = re.search(r'<img\s+src="([^"]+)"', card)
        series = re.search(r'data-series="([a-z-]+)"', card)
        name = clean(heading.group(1))
        projects.append({
            "id": slug,
            "name": name,
            "description": (clean(q.group(1)) if q else clean(desc.group(1)) if desc else "")[:260],
            "series": series.group(1) if series else "archive",
            "project_url": "https://raspos.github.io/databrew/projects/" + slug + "/",
            "url": html.unescape(service.group(1)) if service else "https://raspos.github.io/databrew/projects/" + slug + "/",
            "thumbnail": ("../" + html.unescape(art.group(1))) if art else "",
            "paused": slug == "lee-jae-myung-x" or name == "이재명 X 트래커",
            "story": editorial.get(slug, ""),
        })
    if len(projects) < 10:
        raise ValueError("project card parsing failed; refusing to erase project history")
    for project in projects:
        if project["id"] in editorial:
            story = project["story"]
            if not isinstance(story, str) or not 400 <= len(story) <= 500:
                raise ValueError("400–500 character story requirement failed: " + project["id"])
    # New projects can appear automatically with a card-length introduction;
    # they will receive a reviewed 400–500 character story before the next editorial release.

    return projects


def _bok_meeting(snapshot: dict, meeting_date: str | None = None) -> dict:
    """Read the model's *primary* published scenario, never the CD sensitivity.

    The BOK memo summary can say "CD 91일" even when the top-line model
    actually uses KOFR OIS. Snapshot scenario 0 is the source of truth.
    """
    matches = (snapshot.get("scenarios") or {}).get("0", {}).get("meetings") or []
    reference_date = day_of(snapshot["asof"])
    for meeting in matches:
        meeting_day = meeting.get("date")
        if not meeting_day or meeting_day <= reference_date:
            continue
        if meeting_date and meeting_day != meeting_date:
            continue
        probability = number(meeting.get("p_hike"))
        if probability is None or not 0 <= probability <= 1:
            continue
        if meeting.get("in_range") is False:
            continue
        if not meeting.get("source") or not meeting.get("method"):
            continue
        return meeting
    raise ValueError("No published, in-range next-meeting market probability")


def _bok_comparison(day: str, date: str, current_method: str,
                    current_meeting: str) -> float | None:
    """Fetch a dated archived snapshot; ignore changed model methodologies."""
    if not date or date >= day:
        return None
    try:
        prior = read_url(BASE["bok"] + "data/snapshots/" + date + ".json")
        if day_of(prior.get("asof")) != date:
            return None
        meeting = _bok_meeting(prior, current_meeting)
        if meeting.get("method") != current_method:
            return None
        return number(meeting.get("p_hike"))
    except (KeyError, ValueError, TypeError, urllib.error.URLError, TimeoutError,
            json.JSONDecodeError):
        return None


def bok_update() -> dict:
    # Read the public BOK WATCH *model snapshot*. memo.json is an internal
    # briefing and its headline/methodology must not be copied into a feed.
    meta = read_url(BASE["bok"] + "data/meta.json")
    day = day_of(meta["latest"])
    snapshot = read_url(BASE["bok"] + "data/snapshots/" + day + ".json")
    if day_of(snapshot["asof"]) != day:
        raise ValueError("BOK WATCH meta/snapshot date mismatch")
    meeting = _bok_meeting(snapshot)
    prob = number(meeting["p_hike"])
    meeting_day = day_of(meeting["date"])
    method = meeting["method"]
    origin = meeting["source"]
    if method == "kofr_ois":
        origin = "KOFR OIS(" + str(meeting.get("ois_source") or "자체 산출") + "·자체 산출)"
    elif not origin:
        raise ValueError("BOK WATCH primary source missing")

    # Previous observation and exact week-ago comparison are optional: omit
    # changes if the source archive is missing or used a different method.
    dates = sorted(d for d in meta.get("snapshots", []) if isinstance(d, str) and d < day)
    previous_day = dates[-1] if dates else None
    week_day = (dt.date.fromisoformat(day) - dt.timedelta(days=7)).isoformat()
    week_snapshot = week_day if week_day in dates else None
    previous = _bok_comparison(day, previous_day, method, meeting_day) if previous_day else None
    weekly = _bok_comparison(day, week_snapshot, method, meeting_day) if week_snapshot else None

    value = f"{prob * 100:.1f}%"
    meeting_label = f"{int(meeting_day[5:7])}월 {int(meeting_day[8:10])}일"
    title = f"BOK워치 | {meeting_label} 금통위 인상확률 {value}"
    if weekly is not None:
        change = round((prob - weekly) * 100, 1)
        if change < 0:
            title += f"…1주 새 {abs(change):.1f}%p 하락"
        elif change > 0:
            title += f"…1주 새 {change:.1f}%p 상승"
        else:
            title += "…1주 전과 동일"
    elif previous is not None:
        change = round((prob - previous) * 100, 1)
        title += (f"…직전 관측일보다 {abs(change):.1f}%p "
                  + ("상승" if change > 0 else "하락")) if change else "…직전 관측일과 동일"

    pieces = [f"{day[5:7].lstrip('0')}월 {day[8:10].lstrip('0')}일 관측 기준. "
              f"{origin}를 반영했습니다."]
    if previous is not None:
        previous_change = round((prob - previous) * 100, 1)
        previous_label = f"{int(previous_day[5:7])}월 {int(previous_day[8:10])}일"
        pieces.append(f"직전 관측일({previous_label}) 대비 "
                      + (f"{previous_change:+.1f}%p." if previous_change else "변동이 없습니다."))
    if weekly is not None:
        weekly_label = f"{int(week_day[5:7])}월 {int(week_day[8:10])}일"
        weekly_change = round((prob - weekly) * 100, 1)
        pieces.append(f"1주 전({weekly_label}, {weekly * 100:.1f}%) 대비 {weekly_change:+.1f}%p.")
    hold = number(meeting.get("p_hold"))
    if hold is not None:
        pieces.append(f"동결 확률은 {hold * 100:.1f}%입니다.")
    expected = number(meeting.get("expected"))
    if expected is not None:
        pieces.append(f"회의 후 기대 기준금리는 {expected:.2f}%입니다.")
    text = " ".join(pieces)
    return {
        "id": "watch:bok:" + day, "service": "bok", "day": day,
        "source_at": str(meta.get("built") or day),
        "title": title, "text": text,
        "source": "BOK워치 · " + origin,
        "url": BASE["bok"],
        "note": "시장금리에 기반한 모형 추정치이며 실제 금통위 결정과 다를 수 있습니다.",
    }


def fx_update() -> dict:
    j = read_url(BASE["fx"] + "data/latest.json")
    day = day_of(j["base_date"])
    spot = number(j.get("spot"))
    if spot is None or spot <= 0:
        raise ValueError("FX spot missing")
    change = number(j.get("change"))
    title = "FX워치 | 달러당 원화값 {:,.2f}원".format(spot)
    chunks = []
    if change is not None:
        chunks.append("전 거래일 대비 {:+.2f}원.".format(change))
    for period in ("7", "30"):
        horizon = (j.get("horizons") or {}).get(period) or {}
        selected = horizon.get("selected")
        model = (horizon.get("models") or {}).get(selected) or {}
        rng = model.get("pi80")
        if isinstance(rng, list) and len(rng) == 2 and all(number(v) is not None for v in rng):
            chunks.append("{}일 뒤 80% 예상 구간 {:,.1f}~{:,.1f}원.".format(
                period, float(rng[0]), float(rng[1])
            ))
    return {
        "id": "watch:fx:" + day, "service": "fx", "day": day,
        "source_at": day, "title": title,
        "text": " ".join(chunks) or "최신 공개 환율 관측 자료.",
        "source": "FX워치 · 한국은행 ECOS 매매기준율",
        "url": BASE["fx"],
        "note": "예상 구간은 통계 모형에 따른 확률 범위이며 방향 예측이 아닙니다.",
    }


def apt_update() -> dict:
    j = read_url(BASE["apt"] + "data.json")
    n = j.get("negoIndex") or {}
    market = j.get("market") or {}
    day = day_of(n.get("asOf") or (j.get("asking") or {}).get("lastSuccess") or market.get("day"))
    status = n.get("status")
    title = "APT워치 | 서울 아파트 호가·실거래 관측"
    text = ""
    if status == "HELD_VERIFICATION":
        title += " · 검증 중"
        text = "자료 품질 검증으로 해당 관측일 지수 공표를 유예했습니다."
    else:
        value = number(n.get("currentNegoLevel"))
        if value is None:
            value = number(n.get("currentNegoPressurePct"))
        if value is None:
            value = number((((market.get("regions") or {}).get("all") or {}).get("spread") or {}).get("percent"))
        if value is None:
            raise ValueError("APT index is not currently publishable")
        title += " · 네고 압력 {:+.2f}%".format(value)
        change = (n.get("changes") or {}).get("1d") or {}
        delta = number(change.get("deltaPctPoint"))
        if delta is not None:
            text = "공통 비교 그룹의 전일 대비 변화 {:+.2f}%p.".format(delta)
        text += " 관측 표본의 호가와 최근 유사 실거래를 비교합니다."
    return {
        "id": "watch:apt:" + day, "service": "apt", "day": day,
        "source_at": str(n.get("asOf") or (j.get("asking") or {}).get("lastSuccess") or day),
        "title": title, "text": text.strip(),
        "source": "APT워치 · 표본 아파트",
        "url": BASE["apt"],
        "note": "서울 전체 아파트의 대표값이 아니라 관측 표본 기준입니다.",
    }


def records_update() -> dict:
    meta = read_url(BASE["records"] + "data/meta.json")
    day = day_of(meta["snapshotDate"])
    records = read_url(BASE["records"] + "data/daily.json.gz", compressed=True)
    end = dt.date.fromisoformat(day)
    start = end - dt.timedelta(days=29)
    count = 0
    for i in range(30):
        date = (start + dt.timedelta(days=i)).isoformat()
        item = records.get(date, {})
        x = item.get("records", 0)
        if not isinstance(x, int) or x < 0:
            raise ValueError("unexpected Seoul record-count data")
        count += x
    # "asOf" is the snapshot update time; "day" is the public snapshot date.
    return {
        "id": "watch:records:" + day, "service": "records", "day": day,
        "source_at": str(meta.get("asOf") or day),
        "title": "서울 아파트 신고가 | 최근 30일 계약 {:,}건".format(count),
        "text": "{}~{} 계약일 기준, 2019년 이후 동일 단지·면적 그룹의 신고가 거래를 집계했습니다.".format(
            start.isoformat(), day),
        "source": "서울 아파트 신고가 트래커 · 국토교통부 실거래 자료",
        "url": BASE["records"],
        "note": "계약일 기준 집계이며 신고 지연·해제·추후 자료 반영으로 달라질 수 있습니다.",
    }


SOURCES = [
    ("bok", bok_update),
    ("fx", fx_update),
    ("apt", apt_update),
    ("records", records_update),
]


def main() -> int:
    old = {}
    if OUTPUT.exists():
        old = json.loads(OUTPUT.read_text(encoding="utf-8"))
    if not isinstance(old, dict):
        raise ValueError("NOW state is not an object")
    when = dt.datetime.now(KST).isoformat(timespec="seconds")
    projects = parse_projects()
    previous = {p["id"]: p for p in old.get("projects", []) if isinstance(p, dict) and p.get("id")}
    # Seed pre-existing projects without inventing launch dates.
    for project in projects:
        prior = previous.get(project["id"])
        project["first_seen"] = prior.get("first_seen") if prior else (when if previous else None)
        project["is_new"] = bool(project["first_seen"])
    prior_posts = {p["id"]: p for p in old.get("watch", []) if isinstance(p, dict) and p.get("id")}
    error_names = []
    for service, getter in SOURCES:
        try:
            item = getter()
            if item["service"] != service or day_of(item["day"]) != item["day"]:
                raise ValueError("date and service mismatch")
            # Do not reissue old data as today's reading. Identical source-day = one card.
            prior_posts[item["id"]] = item
            print(service, item["day"], item["title"])
        except (ValueError, KeyError, TypeError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            print("source unavailable:", service, type(exc).__name__, str(exc)[:160], file=sys.stderr)
            error_names.append(service)
    posts = sorted(prior_posts.values(), key=lambda p: (p.get("day", ""), p.get("service", "")), reverse=True)[:180]
    out = {"schema_version": 2, "projects": projects, "watch": posts}
    old_content = {k: old.get(k) for k in out}
    if old_content == out:
        print("No new public data or projects. Leaving activity.json unchanged.")
        return 0
    # Only updated on a genuine public-data or project change.
    out["updated_at"] = when
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Updated NOW activity. Unavailable sources:", ",".join(error_names) or "none")
    return 0


if __name__ == "__main__":
    sys.exit(main())
