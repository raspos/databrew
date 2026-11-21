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
STORY_SUMMARIES = ROOT / "now" / "story-summaries.json"
ARTICLES = ROOT / "articles.json"
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


def prose(fragments: list[str]) -> str:
    """Five or more short Korean news fragments, without formal verb endings."""
    clean_fragments = [str(f).strip().rstrip(". ") for f in fragments if f]
    if len(clean_fragments) < 5:
        raise ValueError("NOW WATCH requires five or more fact-backed clauses")
    return ". ".join(clean_fragments) + "."


def _bok_meeting(snapshot: dict) -> dict:
    """The published primary next-meeting KOFR OIS result, not CD 91d."""
    today = day_of(snapshot["asof"])
    meetings = ((snapshot.get("scenarios") or {}).get("0") or {}).get("meetings") or []
    for item in meetings:
        p = number(item.get("p_hike"))
        if (item.get("date") and item["date"] > today and item.get("in_range")
                and item.get("method") == "kofr_ois" and p is not None and 0 <= p <= 1):
            return item
    raise ValueError("Published KOFR OIS next-meeting scenario unavailable")


def _msb91_model(asof: str, rate: float, spread: float, r0: float,
                 meeting_days: list[str]) -> tuple[float, float]:
    """Reproduce bokwatch/model.py's *min_hike* first-meeting 91-day inversion.

    The 91-day bond spans multiple decisions; this model assigns the
    unobserved changes to later meetings first, testing 25bp, 50bp...
    ceilings. No simplistic rate/25bp conversion or silent single-meeting
    assumption is allowed.
    """
    day = dt.date.fromisoformat(asof)
    start = day + dt.timedelta(days=1)
    end = start + dt.timedelta(days=91)
    meetings = sorted({dt.date.fromisoformat(x) for x in meeting_days
                       if day < dt.date.fromisoformat(x) < end})
    if not meetings:
        raise ValueError("No policy meeting within 91-day bond tenor")
    widths = [(meetings[i + 1] if i + 1 < len(meetings) else end) - m
              for i, m in enumerate(meetings)]
    widths = [x.days for x in widths]
    target = 91 * (rate - spread - r0)
    sign = 1 if target >= 0 else -1
    changes = None
    for k in range(1, 42):
        cap, remain = 0.25 * k, abs(target)
        values = [0.0] * len(meetings)
        for i in range(len(meetings) - 1, -1, -1):
            values[i] = min(cap, remain / widths[i])
            remain -= values[i] * widths[i]
            if remain <= 1e-9:
                break
        if remain <= 1e-9:
            changes = values
            break
    if changes is None:
        raise ValueError("91-day bond min_hike solution unavailable")
    delta = sign * changes[0]
    if delta > 0:
        probability = min(1.0, delta / 0.25)
    else:
        probability = 0.0
    return probability, r0 + delta


def bok_update() -> dict:
    meta = read_url(BASE["bok"] + "data/meta.json")
    day = day_of(meta["latest"])
    snapshot = read_url(BASE["bok"] + "data/snapshots/" + day + ".json")
    if day_of(snapshot.get("asof")) != day:
        raise ValueError("BOK meta/snapshot mismatch")
    next_meeting = _bok_meeting(snapshot)
    meeting_day = day_of(next_meeting["date"])
    ois = number(next_meeting["p_hike"])
    if ois is None:
        raise ValueError("Missing OIS probability")
    r0 = number(snapshot.get("r0"))
    if r0 is None:
        raise ValueError("Missing current base rate")
    inp = {r.get("id"): r for r in snapshot.get("inputs") or []}
    msb = inp.get("msb91")
    cd = inp.get("cd91")
    if not msb or not cd or day_of(msb.get("date")) != day:
        raise ValueError("Same-date 91-day MSB/CD source unavailable")
    upcoming = meta.get("upcoming") or []
    msb_p, msb_expected = _msb91_model(
        day, float(msb["rate"]), float(msb["spread"]), r0, upcoming)
    # Reproduce the site's known 91-day CD model as a unit-level control
    # before trusting the analogous MSB calculation.
    control, _ = _msb91_model(
        day, float(cd["rate"]), float(cd["spread"]), r0, upcoming)
    cd_reference = number((next_meeting.get("cd91") or {}).get("p_hike"))
    if cd_reference is None or abs(control - cd_reference) > 0.005:
        raise ValueError("91-day inference changed relative to original BOK model")
    blend = 0.5 * ois + 0.5 * msb_p
    ois_hold = number(next_meeting.get("p_hold"))
    if ois_hold is None:
        raise ValueError("OIS hold probability missing")
    msb_hold = (1 - msb_p) if msb_expected >= r0 else max(
        0.0, 1 - min(1.0, abs(msb_expected - r0) / 0.25))
    blend_hold = 0.5 * ois_hold + 0.5 * msb_hold
    direction = ("인상 기대가 동결 기대보다 큰 구간" if blend > blend_hold
                 else "동결 기대가 인상 기대와 같거나 더 큰 구간")
    expected_ois = number(next_meeting.get("expected"))
    title = (f"BOK워치 | {int(meeting_day[5:7])}월 {int(meeting_day[8:10])}일 "
             f"인상확률 {blend * 100:.1f}% · KOFR OIS·통안채 91일 50:50")
    pieces = [
        f"{day} 기준 다음 금통위 인상확률 {blend * 100:.1f}%, 두 시장모형에 각각 50% 가중치를 부여한 혼합 추정",
        f"1개월 KOFR OIS의 단독 인상확률 {ois * 100:.1f}%",
        f"통안증권 91일물의 금리경로 역산 인상확률 {msb_p * 100:.1f}%",
        f"통안채 91일 수익률 {float(msb['rate']):.3f}%, 정상 스프레드 {float(msb['spread']) * 100:+.1f}bp 적용",
        f"두 모형을 혼합한 동결확률 {blend_hold * 100:.1f}%, {direction}",
    ]
    if expected_ois is not None:
        pieces.append(f"KOFR OIS 단독 기대 기준금리 {expected_ois:.2f}%, 통안채 모형 기대 기준금리 {msb_expected:.2f}%")
    bond = inp.get("ktb3y") or {}
    if number(bond.get("rate")) is not None and number(bond.get("chg_bp")) is not None:
        pieces.append(f"같은 날 국고채 3년 금리 {float(bond['rate']):.3f}%, 전일 대비 {float(bond['chg_bp']):+.1f}bp")
    pieces.append("통안채 91일물에는 복수 금통위 기대가 섞여 있어 근월 회의 확률이 금리경로 배분 가정에 민감한 구조")
    return {
        "id": "watch:bok:" + day, "service": "bok", "day": day,
        "source_at": str(meta.get("built") or day),
        "title": title, "text": prose(pieces), "sentence_count": len(pieces),
        "source": "BOK워치 · KOFR OIS(50%) + 통안증권 91일(50%)",
        "url": BASE["bok"],
        "note": "NOW 혼합 추정. 통안채 91일물에는 여러 회의의 금리 기대가 포함되며, 실제 정책 결정과 다를 수 있음.",
        "components": {"kofr_ois": round(ois, 5), "msb91": round(msb_p, 5),
                       "weights": [0.5, 0.5], "bond_model": "min_hike"},
    }


def fx_update() -> dict:
    j = read_url(BASE["fx"] + "data/latest.json")
    day = day_of(j["base_date"])
    spot, change = number(j.get("spot")), number(j.get("change"))
    if spot is None or spot <= 0:
        raise ValueError("FX reference rate missing")
    projections = {}
    for period in ("7", "30"):
        horizon = (j.get("horizons") or {}).get(period) or {}
        model = (horizon.get("models") or {}).get(horizon.get("selected")) or {}
        interval = model.get("pi80")
        if (not isinstance(interval, list) or len(interval) != 2
                or any(number(v) is None for v in interval)):
            raise ValueError("FX forecast interval missing for " + period)
        projections[period] = [float(v) for v in interval]
    w7 = projections["7"][1] - projections["7"][0]
    w30 = projections["30"][1] - projections["30"][0]
    if w7 <= 0 or w30 <= 0:
        raise ValueError("FX interval width invalid")
    pieces = [
        f"{day} 기준 달러당 원화값 {spot:,.2f}원, 한국은행 ECOS 매매기준율",
        f"직전 관측 대비 {change:+.2f}원, {'원화 강세' if change < 0 else '원화 약세' if change > 0 else '동일 수준'}" if change is not None else "직전 비교 수치는 원본 자료에서 미확인",
        f"7일 뒤 80% 예상 구간 {projections['7'][0]:,.1f}~{projections['7'][1]:,.1f}원",
        f"30일 뒤 80% 예상 구간 {projections['30'][0]:,.1f}~{projections['30'][1]:,.1f}원",
        f"30일 예상 범위 폭 {w30:.1f}원, 7일 범위 {w7:.1f}원보다 {w30 / w7:.1f}배 넓은 모습",
        "예상 구간의 하단과 상단은 변동성 모형이 계산한 범위이며 실제 방향을 예언하는 수치가 아닌 특성",
    ]
    if projections["30"][0] < 1300 < projections["30"][1]:
        pieces.insert(5, "30일 예상 구간 안에 1300원 아래와 위가 모두 포함된 상황")
    return {
        "id": "watch:fx:" + day, "service": "fx", "day": day,
        "source_at": day,
        "title": f"FX워치 | 달러당 원화값 {spot:,.2f}원 · 30일 예상범위 {projections['30'][0]:,.0f}~{projections['30'][1]:,.0f}원",
        "text": prose(pieces), "sentence_count": len(pieces),
        "source": "FX워치 · 한국은행 ECOS 매매기준율",
        "url": BASE["fx"],
        "note": "매매기준율을 사용하며 서울외환시장 15:30 종가와 다를 수 있음. 구간은 예측치.",
    }


def apt_update() -> dict:
    j = read_url(BASE["apt"] + "data.json")
    n, market = j.get("negoIndex") or {}, j.get("market") or {}
    asking = j.get("asking") or {}
    day = day_of(n.get("asOf") or asking.get("lastSuccess") or market.get("day"))
    so = ((market.get("spreadDynamics") or {}).get("seoulOverall") or {})
    changes = (n.get("changes") or so.get("changes") or {})
    status = n.get("status")
    pieces = [
        f"{day} 기준 서울 25개 구 고정 표본 아파트 매도 호가 관측",
        "같은 단지·면적·층 구간의 최근 90일 유사 실거래가와 현재 호가를 비교하는 네고 압력지수",
    ]
    title = "APT워치 | 서울 아파트 호가·실거래 관측"
    if status == "HELD_VERIFICATION":
        title += " · 검증 중"
        pieces += [
            "원본 서비스가 표본 품질 검증 문제로 당일 지수 공표를 유예한 상태",
            "검증되지 않은 지수 수준과 변화폭은 NOW에서도 게시하지 않는 원칙",
            "모형의 공백을 0 또는 전일 값으로 채우지 않고 원본 공표 재개까지 유보하는 처리",
        ]
    else:
        value = number(n.get("currentNegoLevel"))
        if value is None:
            value = number(n.get("currentNegoPressurePct"))
        if value is None:
            value = number(((((market.get("regions") or {}).get("all") or {}).get("spread") or {}).get("percent")))
        if value is None:
            raise ValueError("APT WATCH published level unavailable")
        title += f" · 네고 압력 {value:+.2f}%"
        pieces.append(f"실거래가 대비 호가 괴리 {value:+.2f}%, {'매도 호가가 최근 유사 실거래보다 높은 구간' if value > 0 else '매도 호가가 최근 유사 실거래보다 높지 않은 구간'}")
        for label,key in (("전일","1d"),("최근 7일","7d"),("최근 28일","28d")):
            ch = changes.get(key) or so.get("changes", {}).get(key) or {}
            delta = number(ch.get("deltaPctPoint"))
            if delta is not None:
                count = number(ch.get("matchedStrataCount"))
                qualifier = f", 공통 비교 그룹 {int(count)}개" if count is not None else ""
                pieces.append(f"{label} 대비 같은 비교 그룹의 괴리 변화 {delta:+.2f}%p{qualifier}")
        if len(pieces) < 5:
            pieces.append("전일 변화는 두 날짜에 공통으로 잡힌 비교 그룹만을 반영한 값으로 당일 지수 수준 자체의 단순 차이와 구분")
    valid = number(asking.get("successes"))
    listings = number(asking.get("listings"))
    if valid is not None and listings is not None:
        pieces.append(f"정상 수집 표본 {int(valid)}개 단지, 매도 매물 {int(listings):,}건")
    pieces.append("관측 단지의 희망가격을 추적하는 표본 지표로 서울 전체 주택시장의 공식 평균과는 다른 성격")
    return {
        "id": "watch:apt:" + day, "service": "apt", "day": day,
        "source_at": str(n.get("asOf") or asking.get("lastSuccess") or day),
        "title": title, "text": prose(pieces), "sentence_count": len(pieces),
        "source": "APT워치 · 서울 표본 아파트",
        "url": BASE["apt"],
        "note": "NEGO INDEX는 희망 호가와 실거래가의 차이이며 실제 협상할인율이 아님.",
    }


def records_update() -> dict:
    meta = read_url(BASE["records"] + "data/meta.json")
    day = day_of(meta["snapshotDate"])
    rows = read_url(BASE["records"] + "data/daily.json.gz", compressed=True)
    end = dt.date.fromisoformat(day)
    start = end - dt.timedelta(days=29)

    def total(begin: dt.date, finish: dt.date) -> int:
        count = 0
        for i in range((finish - begin).days + 1):
            date = (begin + dt.timedelta(days=i)).isoformat()
            item = rows.get(date) or {}
            value = item.get("records", 0)
            if not isinstance(value, int) or value < 0:
                raise ValueError("Invalid Seoul record-count data")
            count += value
        return count

    n = total(start, end)
    previous_start = start - dt.timedelta(days=30)
    previous_end = start - dt.timedelta(days=1)
    prev = total(previous_start, previous_end)
    if prev:
        diff = n - prev
        comparator = (f"직전 30일 계약 신고가 {prev:,}건 대비 {diff:+,}건"
                      + f"({diff / prev * 100:+.1f}%)의 장부상 차이, "
                      + "최근 계약의 신고 지연을 고려하면 실제 시장 변화로 단정하기 어려운 비교")
    else:
        comparator = "직전 30일 계약 신고가와 비교할 기록이 부족한 상태"
    covered = len({x.get("district") for x in meta.get("coverage", [])
                   if x.get("month") == day[:7].replace("-", "")})
    pieces = [
        f"{day} 공개 자료 기준 최근 30일 계약 신고가 {n:,}건",
        f"집계 계약 기간 {start.isoformat()}~{day}, 계약일 기준 지난 30일의 신고가 기록",
        comparator,
        "같은 단지·전용면적 그룹의 2019년 이후 과거 가격을 넘긴 매매를 신고가로 판정",
        f"국토교통부 서울 {covered if covered else 25}개 구 공개 실거래자료를 수집한 자료",
        "실거래 신고 지연으로 최근 계약일의 건수는 시간이 지나면서 추가될 수 있는 잠정 집계",
        "해제 거래와 과거 비교자료가 불충분한 경우의 처리 기준은 원본 서비스에서 확인 가능",
    ]
    return {
        "id": "watch:records:" + day, "service": "records", "day": day,
        "source_at": str(meta.get("asOf") or day),
        "title": f"서울 아파트 신고가 | 최근 30일 계약 {n:,}건",
        "text": prose(pieces), "sentence_count": len(pieces),
        "source": "서울 아파트 신고가 트래커 · 국토교통부 실거래",
        "url": BASE["records"],
        "note": "계약일 기준 잠정 집계. 해당 날짜에 신규 신고된 건수와는 구별.",
    }


def _auto_story_lines(article: dict) -> list[str]:
    """Use four literal paragraphs from the published article if unedited.

    No LLM paraphrase/hallucination. Writers can override with an editorial
    four/five-line summary in now/story-summaries.json.
    """
    relative = str(article.get("url") or "").strip("/")
    if not re.fullmatch(r"articles/[a-zA-Z0-9-]+", relative):
        return []
    path = ROOT / relative / "index.html"
    if not path.is_file():
        return []
    page = path.read_text(encoding="utf-8")
    match = re.search(r'<div class="art-body">([\s\S]*?)</div>', page, re.I)
    if not match:
        return []
    text = match.group(1)
    candidates = [clean(t) for t in re.findall(r"<p(?:\s[^>]*)?>([\s\S]*?)</p>", text)]
    # Very short editorial prompts are not summaries; preserve meaningful text only.
    candidates = [p for p in candidates if len(p) >= 55 and "?" not in p[:70]]
    lines = []
    for p in candidates:
        sentence = re.split(r"(?<=[.!?])\s+", p)[0].strip()
        if len(sentence) > 180:
            continue
        if len(sentence) >= 40:
            lines.append(sentence)
        if len(lines) == 5:
            break
    return lines if len(lines) >= 4 else []


def collect_stories() -> list[dict]:
    records = json.loads(ARTICLES.read_text(encoding="utf-8"))
    curated = json.loads(STORY_SUMMARIES.read_text(encoding="utf-8"))
    if not isinstance(records, list) or not isinstance(curated, dict):
        raise ValueError("article list/summary structure invalid")
    out = []
    for article in records:
        if not isinstance(article, dict):
            continue
        ident, title = article.get("id"), article.get("title")
        if not ident or not title or not article.get("date"):
            continue
        day = day_of(article["date"])
        lines = curated.get(ident) or article.get("now_summary") or _auto_story_lines(article)
        if isinstance(lines, str):
            lines = [t.strip() for t in lines.splitlines() if t.strip()]
        if not isinstance(lines, list) or not 4 <= len(lines) <= 5 or not all(isinstance(v, str) and v.strip() for v in lines):
            # Do not replace a source article by an invented or broken summary.
            print("STORY summary missing:", ident, file=sys.stderr)
            continue
        path = str(article.get("url") or "")
        if not (re.fullmatch(r"articles/[a-zA-Z0-9-]+/", path) or path.startswith("https://")):
            continue
        out.append({
            "id": ident, "day": day, "title": title,
            "url": path if path.startswith("http") else "https://raspos.github.io/databrew/" + path,
            "project": article.get("project"), "summary_lines": lines,
            "summary_source": "editorial" if ident in curated or article.get("now_summary") else "source_extract",
        })
    return sorted(out, key=lambda x: (x["day"], x["id"]), reverse=True)[:100]


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
    out = {"schema_version": 3, "projects": projects, "watch": posts, "stories": collect_stories()}
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
