from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass

import requests
from bs4 import BeautifulSoup


USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36 "
    "SPbU-Exam-Monitor/1.0"
)


@dataclass
class Exam:
    id: str
    group: str
    date: str = ""
    time: str = ""
    subject: str = ""
    type: str = ""
    teacher: str = ""
    room: str = ""
    extra: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


def normalize(text: str) -> str:
    text = text.replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def stable_id(group: str, fields: list[str]) -> str:
    raw = "|".join([group, *fields]).lower()
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def fetch_html(url: str) -> str:
    r = requests.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    r.raise_for_status()
    return r.text


def fetch_rendered_html(url: str) -> str:
    # The timetable can be partially rendered by JavaScript. Playwright is
    # used only as a fallback so ordinary HTTP requests remain the fast path.
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=USER_AGENT)
        page.goto(url, wait_until="networkidle", timeout=60_000)
        page.wait_for_timeout(1500)
        html = page.content()
        browser.close()
        return html


def _date_matches(text: str) -> list[str]:
    patterns = [
        r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b",
        r"\b\d{1,2}[./-]\d{1,2}\b",
    ]
    result = []
    for pattern in patterns:
        result.extend(re.findall(pattern, text))
    return list(dict.fromkeys(result))


def _time_matches(text: str) -> list[str]:
    return re.findall(r"\b(?:[01]?\d|2[0-3]):[0-5]\d\b", text)


def _looks_like_exam(text: str) -> bool:
    t = text.lower()
    keywords = (
        "экзамен",
        "зачет",
        "зачёт",
        "аттеста",
        "exam",
        "credit",
        "test",
    )
    return any(k in t for k in keywords)


def _extract_record(group: str, text: str, element_index: int) -> Exam | None:
    text = normalize(text)
    dates = _date_matches(text)
    times = _time_matches(text)

    if not dates and not times and not _looks_like_exam(text):
        return None

    # Conservative extraction. We retain the full original row text in extra
    # so that no information is silently lost if SPbU changes column names.
    subject = ""
    type_ = ""
    teacher = ""
    room = ""

    lower = text.lower()
    for marker in ("экзамен", "exam", "зачет", "зачёт"):
        if marker in lower:
            type_ = marker
            break

    # A subject is often the largest text fragment that is not a date/time.
    fragments = [normalize(x) for x in re.split(r"\s{2,}|\|", text) if normalize(x)]
    if fragments:
        candidates = [
            x for x in fragments
            if not _date_matches(x)
            and not _time_matches(x)
            and x.lower() not in {type_.lower(), group.lower()}
        ]
        if candidates:
            subject = max(candidates, key=len)

    fields_for_id = [
        group,
        dates[0] if dates else "",
        times[0] if times else "",
        subject,
        type_,
    ]
    return Exam(
        id=stable_id(group, fields_for_id),
        group=group,
        date=dates[0] if dates else "",
        time=times[0] if times else "",
        subject=subject,
        type=type_,
        teacher=teacher,
        room=room,
        extra=text,
    )


def parse_html(html: str, groups: tuple[str, ...]) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")

    # Restrict ourselves to the previous-year attestation section whenever
    # possible. The exact DOM has changed historically, so this is deliberately
    # based on visible heading text rather than brittle CSS class names.
    heading = None
    for tag in soup.find_all(["h1", "h2", "h3", "h4", "h5", "div", "span"]):
        txt = normalize(tag.get_text(" ", strip=True))
        if "Intermediary attestation for the previous academic year 2025-2026" in txt:
            heading = tag
            break

    root = heading.parent if heading else soup

    records: list[dict] = []

    # First pass: table rows / list items / cards containing a target group.
    candidates = root.find_all(["tr", "li", "article", "div", "section"])
    seen = set()

    for node in candidates:
        text = normalize(node.get_text(" ", strip=True))
        if not text or len(text) > 2500:
            continue
        matched_group = next((g for g in groups if g in text), None)
        if not matched_group:
            continue
        if not (_date_matches(text) or _time_matches(text) or _looks_like_exam(text)):
            continue

        key = (matched_group, text)
        if key in seen:
            continue
        seen.add(key)

        record = _extract_record(matched_group, text, len(records))
        if record:
            records.append(record.as_dict())

    # Second pass: if the group labels are rendered separately from the
    # schedule cells, look at nearby sibling/ancestor text.
    if not records:
        for group in groups:
            for node in root.find_all(string=re.compile(re.escape(group))):
                parent = node.parent
                for ancestor in list(parent.parents)[:6]:
                    text = normalize(ancestor.get_text(" ", strip=True))
                    if len(text) > 5000:
                        continue
                    if _date_matches(text) or _time_matches(text):
                        record = _extract_record(group, text, len(records))
                        if record:
                            records.append(record.as_dict())
                            break

    # Deduplicate by content.
    unique = {}
    for record in records:
        unique[(record["group"], record["id"])] = record

    return sorted(
        unique.values(),
        key=lambda x: (x["group"], x["date"], x["time"], x["subject"]),
    )


def scrape(url: str, groups: tuple[str, ...]) -> dict:
    html = fetch_html(url)
    exams = parse_html(html, groups)

    if not exams:
        try:
            rendered = fetch_rendered_html(url)
            exams = parse_html(rendered, groups)
        except Exception as exc:
            # Keep the original HTTP result if browser fallback is unavailable.
            print(f"Playwright fallback failed: {exc}")

    return {
        "source_url": url,
        "groups": list(groups),
        "exams": exams,
    }
