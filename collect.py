# -*- coding: utf-8 -*-
"""
뉴스를 수집하고 분류해서 data/YYYY-MM-DD.json 으로 저장합니다.

실행:
    python collect.py           # 실제 수집
    python collect.py --demo    # 네트워크 없이 샘플 데이터 생성 (미리보기용)

설계 원칙: 피드 하나가 실패해도 전체 실행은 계속됩니다.
"""

import json
import os
import re
import sys
import time
import html
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser

import config

KST = timezone(timedelta(hours=9))
DATA_DIR = Path(__file__).parent / "data"
GOOGLE_NEWS = "https://news.google.com/rss/search"


# ---------------------------------------------------------------------------
# 유틸
# ---------------------------------------------------------------------------

def now_kst():
    return datetime.now(KST)


def strip_html(text):
    """RSS 설명에 섞인 태그를 제거합니다."""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def split_source(title):
    """구글 뉴스 제목은 '기사 제목 - 언론사' 형태입니다."""
    if " - " in title:
        head, _, tail = title.rpartition(" - ")
        if head and len(tail) <= 20:
            return head.strip(), tail.strip()
    return title.strip(), ""


def normalize(title):
    """중복 판정용 키. 공백·기호·조사 차이를 무시합니다."""
    return re.sub(r"[^0-9a-z가-힣]", "", title.lower())


def to_kst(entry):
    """RSS의 시각을 KST로 변환합니다. 없으면 현재 시각."""
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if not parsed:
        return now_kst()
    return datetime.fromtimestamp(time.mktime(parsed), tz=timezone.utc).astimezone(KST)


# ---------------------------------------------------------------------------
# 수집
# ---------------------------------------------------------------------------

def build_feed_urls():
    """설정의 검색어를 구글 뉴스 RSS 주소로 바꿉니다."""
    urls = []
    for query in config.SEARCH_QUERIES:
        # when:1d = 최근 하루치만. 오래된 기사가 섞이는 것을 막습니다.
        q = urllib.parse.quote(f"{query} when:1d")
        urls.append((query, f"{GOOGLE_NEWS}?q={q}&hl=ko&gl=KR&ceid=KR:ko"))
    for url in config.EXTRA_RSS_FEEDS:
        urls.append((url, url))
    return urls


def fetch_all():
    """모든 피드를 돌면서 기사를 모읍니다. 실패한 피드는 건너뜁니다."""
    articles = []
    failures = []

    for label, url in build_feed_urls():
        try:
            parsed = feedparser.parse(url)
            if parsed.bozo and not parsed.entries:
                raise ValueError(parsed.get("bozo_exception", "피드 파싱 실패"))

            for entry in parsed.entries:
                raw_title = entry.get("title", "").strip()
                if not raw_title:
                    continue

                title, source = split_source(raw_title)

                # 구글 뉴스는 source 필드에 언론사명을 따로 넣어줍니다.
                if not source:
                    source = (entry.get("source", {}) or {}).get("title", "")

                articles.append({
                    "title": title,
                    "source": source or "출처 미상",
                    "url": entry.get("link", ""),
                    "published": to_kst(entry).isoformat(),
                    "snippet": strip_html(entry.get("summary", ""))[:200],
                    "query": label,
                })

            print(f"  OK   {label} — {len(parsed.entries)}건")

        except Exception as exc:  # 어떤 오류든 전체 실행을 멈추지 않습니다
            failures.append(label)
            print(f"  SKIP {label} — {type(exc).__name__}: {exc}")

        time.sleep(1)  # 연속 요청 간격

    return articles, failures


# ---------------------------------------------------------------------------
# 필터 · 중복 제거 · 분류
# ---------------------------------------------------------------------------

def is_excluded(title):
    return any(word in title for word in config.EXCLUDE_KEYWORDS)


def dedupe(articles):
    """제목이 사실상 같은 기사를 하나로 합칩니다."""
    seen = {}
    for art in articles:
        key = normalize(art["title"])
        if not key:
            continue
        if key in seen:
            # 같은 기사가 여러 매체에 실렸으면 매체 수를 세어 둡니다.
            seen[key]["duplicates"] += 1
        else:
            art["duplicates"] = 0
            seen[key] = art
    return list(seen.values())


def classify(article):
    """제목과 요약을 키워드와 대조해 점수가 가장 높은 카테고리로 보냅니다."""
    text = f"{article['title']} {article['snippet']}"
    best_name, best_score = config.FALLBACK_CATEGORY, 0

    for name, spec in config.CATEGORIES.items():
        score = sum(2 if kw in article["title"] else 1
                    for kw in spec["keywords"] if kw in text)
        if score > best_score:
            best_name, best_score = name, score

    return best_name, best_score


def tag_companies(article):
    text = f"{article['title']} {article['snippet']}"
    return [name for name in config.COMPANY_TAGS if name in text]


def enrich(articles):
    result = []
    for art in articles:
        if is_excluded(art["title"]):
            continue
        category, score = classify(art)
        art["category"] = category
        art["relevance"] = score + art.get("duplicates", 0)
        art["companies"] = tag_companies(art)
        result.append(art)

    # 관련도 높은 순, 같으면 최신 순
    result.sort(key=lambda a: (a["relevance"], a["published"]), reverse=True)
    return result[:config.MAX_ARTICLES_PER_DAY]


# ---------------------------------------------------------------------------
# AI 브리핑 (선택)
# ---------------------------------------------------------------------------

def build_briefing(articles):
    """
    하루 1회 API를 호출해 '오늘의 흐름'을 만듭니다.
    키가 없거나 호출이 실패하면 None을 돌려주고 대시보드는 요약 없이 나갑니다.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not config.ENABLE_AI_BRIEFING or not api_key or not articles:
        return None

    try:
        import requests
    except ImportError:
        print("  requests 미설치 — AI 요약 생략")
        return None

    lines = []
    for art in articles[:50]:
        tags = f" [{', '.join(art['companies'])}]" if art["companies"] else ""
        lines.append(f"- ({art['category']}) {art['title']} / {art['source']}{tags}")
    headlines = "\n".join(lines)

    prompt = (
        "아래는 오늘 수집된 K-뷰티 산업 뉴스 헤드라인입니다.\n"
        "이것만 근거로 브리핑을 작성하세요. 헤드라인에 없는 내용은 쓰지 마세요.\n\n"
        f"{headlines}\n\n"
        "아래 JSON 형식으로만 답하세요. 다른 말은 붙이지 마세요.\n"
        '{"headline": "오늘 K-뷰티 산업을 한 문장으로", '
        '"points": ["핵심 흐름 1", "핵심 흐름 2", "핵심 흐름 3"], '
        '"watch": "확인이 필요한 지점 한 문장"}\n\n'
        "points는 3~4개, 각 40자 내외. 여러 기사에 걸친 흐름을 짚고, "
        "단일 기사 요약은 피하세요. 수치는 헤드라인에 있는 것만 쓰세요."
    )

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": config.AI_MODEL,
                "max_tokens": 1000,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=90,
        )
        response.raise_for_status()

        text = "".join(
            block.get("text", "")
            for block in response.json().get("content", [])
            if block.get("type") == "text"
        )
        text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
        briefing = json.loads(text)

        print("  AI 브리핑 생성 완료")
        return briefing

    except Exception as exc:
        print(f"  AI 브리핑 생략 — {type(exc).__name__}: {exc}")
        return None


# ---------------------------------------------------------------------------
# 저장
# ---------------------------------------------------------------------------

def cleanup_old_files():
    cutoff = (now_kst() - timedelta(days=config.KEEP_DAYS)).strftime("%Y-%m-%d")
    for path in DATA_DIR.glob("*.json"):
        if path.stem < cutoff:
            path.unlink()
            print(f"  보관기간 경과로 삭제: {path.name}")


def save(articles, briefing, failures):
    DATA_DIR.mkdir(exist_ok=True)
    today = now_kst().strftime("%Y-%m-%d")

    counts = {}
    for art in articles:
        counts[art["category"]] = counts.get(art["category"], 0) + 1

    payload = {
        "date": today,
        "generated_at": now_kst().isoformat(),
        "total": len(articles),
        "counts": counts,
        "briefing": briefing,
        "failed_feeds": failures,
        "articles": articles,
    }

    path = DATA_DIR / f"{today}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n저장 완료: {path} ({len(articles)}건)")
    return path


# ---------------------------------------------------------------------------
# 데모 데이터
# ---------------------------------------------------------------------------

def demo_articles():
    """네트워크 없이 대시보드를 미리 보기 위한 가짜 데이터입니다."""
    samples = [
        ("아모레퍼시픽 3분기 영업이익 시장 기대치 상회", "머니투데이", "브랜드"),
        ("코스맥스 미국 2공장 증설 완료, 수주 확대 기대", "한국경제", "ODM·OEM"),
        ("실리콘투 북미 역직구 매출 분기 최대", "이데일리", "수출·해외"),
        ("올리브영, 인디 브랜드 입점 기준 개편", "뉴시스", "유통·채널"),
        ("식약처, 기능성화장품 표시광고 가이드라인 개정 예고", "약사공론", "규제·정책"),
        ("펌텍코리아 신규 용기 라인 가동", "서울경제", "원료·부자재"),
        ("한국콜마 목표주가 상향, 증권가 실적 눈높이 조정", "인포스탁데일리", "자본시장"),
        ("에이피알 일본 법인 설립 검토", "매일경제", "브랜드"),
        ("화장품 수출액 전년 대비 증가세 지속", "연합뉴스", "수출·해외"),
        ("조선미녀, 아마존 뷰티 카테고리 상위권 유지", "전자신문", "브랜드"),
    ]
    base = now_kst().replace(hour=8, minute=0, second=0, microsecond=0)
    articles = []
    for i, (title, source, category) in enumerate(samples):
        art = {
            "title": title,
            "source": source,
            "url": "https://news.google.com/",
            "published": (base - timedelta(hours=i)).isoformat(),
            "snippet": "샘플 데이터입니다. 실제 수집 시 기사 요약이 들어갑니다.",
            "query": "demo",
            "duplicates": 0,
            "category": category,
            "relevance": 10 - i,
            "companies": tag_companies({"title": title, "snippet": ""}),
        }
        articles.append(art)
    return articles


# ---------------------------------------------------------------------------

def main():
    demo = "--demo" in sys.argv

    if demo:
        print("데모 모드 — 네트워크를 쓰지 않습니다.")
        articles = demo_articles()
        briefing = {
            "headline": "브랜드사 실적과 북미 수출 지표가 동시에 개선되는 흐름",
            "points": [
                "브랜드사 3분기 실적이 시장 기대치를 웃돌았다는 보도가 다수",
                "ODM 진영은 미국 현지 생산능력 확충 소식에 집중",
                "북미 역직구·아마존 채널 성과가 수출 지표를 견인",
                "식약처 표시광고 가이드라인 개정으로 규제 부담 점검 필요",
            ],
            "watch": "실적 기사 수치는 원문 공시로 교차 확인이 필요합니다.",
        }
        failures = []
    else:
        print(f"수집 시작 — {now_kst():%Y-%m-%d %H:%M} KST\n")
        raw, failures = fetch_all()
        print(f"\n원본 {len(raw)}건 수집")
        articles = enrich(dedupe(raw))
        print(f"중복·제외 처리 후 {len(articles)}건")
        briefing = build_briefing(articles)
        cleanup_old_files()

    save(articles, briefing, failures)


if __name__ == "__main__":
    main()
