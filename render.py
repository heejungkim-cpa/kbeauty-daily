# -*- coding: utf-8 -*-
"""
data/*.json 을 읽어 docs/ 아래에 HTML 대시보드를 만듭니다.

실행:
    python render.py

수집을 다시 하지 않고 화면만 고치고 싶을 때 이 파일만 실행하면 됩니다.
"""

import html
import json
from datetime import datetime
from pathlib import Path

import config

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
DOCS_DIR = ROOT / "docs"

WEEKDAYS = ["월", "화", "수", "목", "금", "토", "일"]


def esc(text):
    return html.escape(str(text), quote=True)


def shade_of(category):
    spec = config.CATEGORIES.get(category)
    return spec["shade"] if spec else config.FALLBACK_SHADE


def code_of(category):
    spec = config.CATEGORIES.get(category)
    return spec["code"] if spec else "00"


def note_of(category):
    spec = config.CATEGORIES.get(category)
    return spec["note"] if spec else "분류되지 않은 기사"


def time_label(iso):
    try:
        return datetime.fromisoformat(iso).strftime("%H:%M")
    except (ValueError, TypeError):
        return ""


def date_label(date_str):
    d = datetime.strptime(date_str, "%Y-%m-%d")
    return f"{d:%Y.%m.%d} {WEEKDAYS[d.weekday()]}"


# ---------------------------------------------------------------------------
# 스타일
# ---------------------------------------------------------------------------

CSS = """
:root {
  --paper: #F2F0F5;
  --card: #FBFAFC;
  --ink: #17141F;
  --ink-soft: #56505F;
  --ink-faint: #8B8494;
  --rule: #DDD8E3;
  --strip-h: 60px;
}

* { box-sizing: border-box; }

body {
  margin: 0;
  background: var(--paper);
  color: var(--ink);
  font-family: "IBM Plex Sans KR", system-ui, sans-serif;
  font-size: 15px;
  line-height: 1.65;
  -webkit-font-smoothing: antialiased;
}

.wrap { max-width: 940px; margin: 0 auto; padding: 0 24px 96px; }

/* ---- 머리말 ---- */

.masthead { padding: 56px 0 28px; }

.eyebrow {
  font-family: "IBM Plex Mono", monospace;
  font-size: 11px;
  letter-spacing: 0.22em;
  text-transform: uppercase;
  color: var(--ink-faint);
  margin: 0 0 14px;
}

.masthead h1 {
  font-family: "Song Myung", serif;
  font-size: clamp(38px, 7vw, 62px);
  font-weight: 400;
  letter-spacing: -0.02em;
  line-height: 1.02;
  margin: 0 0 10px;
}

.masthead p { margin: 0; color: var(--ink-soft); font-size: 14px; }

/* ---- 색상 띠: 오늘 기사 분포 ---- */

.strip {
  display: flex;
  height: var(--strip-h);
  border-radius: 3px;
  overflow: hidden;
  margin: 8px 0 10px;
}

.strip button {
  border: 0;
  padding: 0 12px;
  flex-basis: 0;
  min-width: 0;
  cursor: pointer;
  color: #fff;
  text-align: left;
  font: inherit;
  overflow: hidden;
  white-space: nowrap;
  transition: flex-grow 0.5s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.2s;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.strip button:hover, .strip button:focus-visible { opacity: 0.82; }
.strip button:focus-visible { outline: 2px solid var(--ink); outline-offset: -4px; }

.strip .seg-code {
  font-family: "IBM Plex Mono", monospace;
  font-size: 10px;
  letter-spacing: 0.14em;
  opacity: 0.72;
  overflow: hidden;
  text-overflow: ellipsis;
}

.strip .seg-name {
  font-size: 12.5px;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 구간이 좁아지면 이름부터, 더 좁아지면 번호까지 숨깁니다.
   잘린 글자를 보여주느니 색과 폭만 남기는 편이 낫습니다.
   가려진 내용은 마우스를 올리면 말풍선으로 나옵니다. */
.strip button.tight { padding: 0 7px; }
.strip button.tight .seg-name { display: none; }
.strip button.micro { padding: 0 3px; }
.strip button.micro .seg-code { display: none; }

.strip-legend {
  font-family: "IBM Plex Mono", monospace;
  font-size: 11px;
  color: var(--ink-faint);
  letter-spacing: 0.04em;
  display: flex;
  justify-content: space-between;
  border-top: 1px solid var(--rule);
  padding-top: 8px;
}

/* ---- 오늘의 흐름 ---- */

.briefing {
  background: var(--card);
  border: 1px solid var(--rule);
  border-radius: 4px;
  padding: 28px 30px;
  margin: 34px 0 12px;
}

.briefing h2 {
  font-family: "Song Myung", serif;
  font-size: 22px;
  font-weight: 400;
  line-height: 1.45;
  margin: 10px 0 20px;
}

.briefing ul { margin: 0; padding: 0; list-style: none; }

.briefing li {
  position: relative;
  padding-left: 22px;
  margin-bottom: 9px;
  color: var(--ink-soft);
  font-size: 14.5px;
}

.briefing li::before {
  content: "";
  position: absolute;
  left: 2px;
  top: 10px;
  width: 9px;
  height: 1px;
  background: var(--ink-faint);
}

.briefing .watch {
  margin: 20px 0 0;
  padding-top: 16px;
  border-top: 1px solid var(--rule);
  font-size: 13px;
  color: var(--ink-faint);
}

/* ---- 필터 ---- */

.filters {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
  margin: 36px 0 30px;
  position: sticky;
  top: 0;
  background: var(--paper);
  padding: 14px 0;
  z-index: 5;
}

.filters button {
  font: inherit;
  font-size: 12.5px;
  padding: 5px 13px;
  border: 1px solid var(--rule);
  border-radius: 999px;
  background: transparent;
  color: var(--ink-soft);
  cursor: pointer;
}

.filters button[aria-pressed="true"] {
  background: var(--ink);
  border-color: var(--ink);
  color: var(--paper);
}

.filters button:focus-visible { outline: 2px solid var(--ink); outline-offset: 2px; }

/* ---- 기사 ---- */

.group { margin-bottom: 46px; }

.group-head {
  display: flex;
  align-items: baseline;
  gap: 12px;
  border-bottom: 1px solid var(--rule);
  padding-bottom: 9px;
  margin-bottom: 4px;
}

.group-chip { width: 11px; height: 11px; border-radius: 2px; flex: none; }

.group-head h3 { font-size: 15px; font-weight: 600; margin: 0; letter-spacing: -0.01em; }

.group-head .note { font-size: 12.5px; color: var(--ink-faint); margin-right: auto; }

.group-head .count { font-family: "IBM Plex Mono", monospace; font-size: 12px; color: var(--ink-faint); }

.item { padding: 15px 0 15px 16px; border-bottom: 1px solid var(--rule); border-left: 2px solid transparent; }

.item:hover { border-left-color: currentColor; background: rgba(255,255,255,0.5); }

.item a {
  color: var(--ink);
  text-decoration: none;
  font-size: 16px;
  font-weight: 500;
  line-height: 1.45;
  letter-spacing: -0.012em;
}

.item a:hover { text-decoration: underline; text-underline-offset: 3px; }

.meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-top: 7px;
  font-family: "IBM Plex Mono", monospace;
  font-size: 11.5px;
  color: var(--ink-faint);
}

.meta .dot { opacity: 0.5; }

.tag {
  font-family: "IBM Plex Sans KR", sans-serif;
  font-size: 11px;
  padding: 1px 7px;
  border-radius: 3px;
  background: rgba(23, 20, 31, 0.06);
  color: var(--ink-soft);
}

.dupes { font-style: normal; opacity: 0.75; }

/* ---- 꼬리말 ---- */

.foot {
  margin-top: 60px;
  padding-top: 22px;
  border-top: 1px solid var(--rule);
  font-family: "IBM Plex Mono", monospace;
  font-size: 11.5px;
  color: var(--ink-faint);
  line-height: 2;
}

.foot a { color: var(--ink-soft); }

.archive { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 6px; }

.empty { padding: 60px 0; text-align: center; color: var(--ink-faint); }

@media (max-width: 640px) {
  .wrap { padding: 0 16px 72px; }
  .masthead { padding: 36px 0 20px; }
  :root { --strip-h: 48px; }
  .strip .seg-name { display: none; }
  .briefing { padding: 22px 20px; }
  .group-head .note { display: none; }
}

@media (prefers-reduced-motion: reduce) {
  * { transition: none !important; animation: none !important; }
}
"""

JS = """
// 구간 폭을 재서 글자가 잘리기 전에 미리 숨깁니다.
// 창 크기가 바뀌어도 다시 계산합니다.
const segments = document.querySelectorAll('.strip button');

function fitSegments() {
  segments.forEach(seg => {
    const w = seg.offsetWidth;
    seg.classList.toggle('tight', w < 104);
    seg.classList.toggle('micro', w < 46);
  });
}

fitSegments();
window.addEventListener('resize', fitSegments);

// 웹폰트가 늦게 오면 글자 폭이 바뀌므로 한 번 더 계산합니다.
if (document.fonts && document.fonts.ready) {
  document.fonts.ready.then(fitSegments);
}

const buttons = document.querySelectorAll('[data-filter]');
const groups = document.querySelectorAll('[data-category]');

function apply(target) {
  buttons.forEach(b => b.setAttribute('aria-pressed', String(b.dataset.filter === target)));
  groups.forEach(g => {
    g.style.display = (target === 'all' || g.dataset.category === target) ? '' : 'none';
  });
}

buttons.forEach(b => b.addEventListener('click', () => apply(b.dataset.filter)));

document.querySelectorAll('[data-jump]').forEach(seg => {
  seg.addEventListener('click', () => {
    apply(seg.dataset.jump);
    document.getElementById('feed').scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
});
"""


# ---------------------------------------------------------------------------
# 조각별 HTML
# ---------------------------------------------------------------------------

def render_strip(counts, total):
    if not total:
        return ""

    segments = []
    ordered = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)

    for category, count in ordered:
        share = count / total * 100
        segments.append(
            f'<button data-jump="{esc(category)}" style="flex-grow:{count};background:{shade_of(category)}"'
            f' title="{esc(category)} {count}건 ({share:.0f}%)"'
            f' aria-label="{esc(category)} {count}건, 눌러서 이 분류만 보기">'
            f'<span class="seg-code">{code_of(category)}</span>'
            f'<span class="seg-name">{esc(category)} {count}</span>'
            f"</button>"
        )

    top = ordered[0]
    return (
        f'<div class="strip">{"".join(segments)}</div>'
        f'<div class="strip-legend"><span>오늘 {total}건 · {len(counts)}개 분류</span>'
        f"<span>최다 {esc(top[0])} {top[1]}건</span></div>"
    )


def render_briefing(briefing):
    if not briefing:
        return ""

    points = "".join(f"<li>{esc(p)}</li>" for p in briefing.get("points", []))
    watch = briefing.get("watch", "")
    watch_html = f'<p class="watch">확인할 지점 — {esc(watch)}</p>' if watch else ""

    return (
        '<section class="briefing">'
        '<p class="eyebrow">오늘의 흐름</p>'
        f'<h2>{esc(briefing.get("headline", ""))}</h2>'
        f"<ul>{points}</ul>{watch_html}"
        "</section>"
    )


def render_filters(counts):
    chips = ['<button data-filter="all" aria-pressed="true">전체</button>']
    for category, count in sorted(counts.items(), key=lambda kv: kv[1], reverse=True):
        chips.append(f'<button data-filter="{esc(category)}" aria-pressed="false">{esc(category)} {count}</button>')
    return f'<nav class="filters" aria-label="분류 필터">{"".join(chips)}</nav>'


def render_item(article):
    bits = [esc(article["source"])]
    stamp = time_label(article["published"])
    if stamp:
        bits.append(stamp)
    meta = '<span class="dot">·</span>'.join(f"<span>{b}</span>" for b in bits)

    if article.get("duplicates"):
        meta += f'<span class="dot">·</span><span class="dupes">{article["duplicates"] + 1}개 매체 보도</span>'

    tags = "".join(f'<span class="tag">{esc(c)}</span>' for c in article.get("companies", [])[:3])

    url = article.get("url") or "#"
    return (
        f'<article class="item" style="color:{shade_of(article["category"])}">'
        f'<a href="{esc(url)}" target="_blank" rel="noopener">{esc(article["title"])}</a>'
        f'<div class="meta">{meta}{tags}</div>'
        "</article>"
    )


def render_groups(articles, counts):
    blocks = []
    for category, count in sorted(counts.items(), key=lambda kv: kv[1], reverse=True):
        items = "".join(render_item(a) for a in articles if a["category"] == category)
        blocks.append(
            f'<section class="group" data-category="{esc(category)}">'
            '<div class="group-head">'
            f'<span class="group-chip" style="background:{shade_of(category)}"></span>'
            f"<h3>{esc(category)}</h3>"
            f'<span class="note">{esc(note_of(category))}</span>'
            f'<span class="count">{count}</span>'
            "</div>"
            f"{items}</section>"
        )
    return f'<div id="feed">{"".join(blocks)}</div>'


def render_footer(payload, archive_dates, current_date):
    generated = payload.get("generated_at", "")
    try:
        stamp = datetime.fromisoformat(generated).strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        stamp = generated

    lines = [f"갱신 {esc(stamp)} KST · 구글 뉴스 RSS 수집"]

    failed = payload.get("failed_feeds") or []
    if failed:
        lines.append(f"수집 실패한 검색어 {len(failed)}건: {esc(', '.join(failed[:5]))}")

    links = []
    for date in archive_dates[:14]:
        if date == current_date:
            links.append(f"<strong>{date[5:]}</strong>")
        else:
            links.append(f'<a href="{date}.html">{date[5:]}</a>')

    archive = f'<div class="archive">지난 기록 {"".join(links)}</div>' if len(links) > 1 else ""
    return f'<footer class="foot">{"<br>".join(lines)}{archive}</footer>'


# ---------------------------------------------------------------------------
# 페이지 조립
# ---------------------------------------------------------------------------

def render_page(payload, archive_dates):
    articles = payload.get("articles", [])
    counts = payload.get("counts", {})
    total = payload.get("total", len(articles))
    date = payload["date"]

    if articles:
        body = (
            render_strip(counts, total)
            + render_briefing(payload.get("briefing"))
            + render_filters(counts)
            + render_groups(articles, counts)
        )
    else:
        body = '<p class="empty">이 날짜에는 수집된 기사가 없습니다.</p>'

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(config.SITE_TITLE)} — {date}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Song+Myung&family=IBM+Plex+Sans+KR:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
  <header class="masthead">
    <p class="eyebrow">{esc(date_label(date))}</p>
    <h1>{esc(config.SITE_TITLE)}</h1>
    <p>{esc(config.SITE_SUBTITLE)}</p>
  </header>
  {body}
  {render_footer(payload, archive_dates, date)}
</div>
<script>{JS}</script>
</body>
</html>"""


def main():
    DOCS_DIR.mkdir(exist_ok=True)
    (DOCS_DIR / ".nojekyll").write_text("", encoding="utf-8")

    files = sorted(DATA_DIR.glob("*.json"), reverse=True)
    if not files:
        print("data/ 에 파일이 없습니다. 먼저 collect.py 를 실행하세요.")
        return

    dates = [f.stem for f in files]

    for path in files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        (DOCS_DIR / f"{payload['date']}.html").write_text(
            render_page(payload, dates), encoding="utf-8"
        )

    latest = json.loads(files[0].read_text(encoding="utf-8"))
    (DOCS_DIR / "index.html").write_text(render_page(latest, dates), encoding="utf-8")

    print(f"생성 완료: docs/index.html (기준일 {latest['date']}, {latest['total']}건)")


if __name__ == "__main__":
    main()
