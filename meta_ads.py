"""경쟁사 메타(페이스북·인스타) 광고 수집 → meta_ads.json (index.html 이 읽음, GitHub Pages)

메타 광고 라이브러리(로그인 불필요) 브랜드 공식 페이지를 브랜드당 2번 연다:
  ① 기본 화면(최신·관련도순 30개)  ② 시작일 60일 이전 필터(=오래 켜둔 광고 30개)
첫 화면 HTML 에 박혀 오는 JSON 만 읽는다. 스크롤(GraphQL 페이징)은 비로그인이면 곧 rate limit 이라 안 씀.
# ponytail: 브랜드당 최대 ~60개만 봄. 쿠쿠처럼 수백 개 켜둔 곳은 일부만 보임 — 필요하면 media_type/기간 필터로 쪼개 더 열기.

실행: python meta_ads.py      (GitHub Actions collect.yml 이 10/14/18시 KST 실행)
"""
import json
import re
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

KST = timezone(timedelta(hours=9))
OUT = Path(__file__).parent / "meta_ads.json"
LONG_DAYS = 60

# 브랜드 → 메타 페이지 ID (광고 라이브러리 page_id). 없으면 q(검색어)+match(페이지명 포함) 로 찾음.
BRANDS = [
    {"name": "쿠쿠", "page": "113317456009593"},
    {"name": "한일", "page": "228923510482856"},
    {"name": "스마트카라", "page": "958751864267955"},
    {"name": "캐리어", "q": "캐리어", "match": ["캐리어", "carrier"]},   # 공식 페이지 광고 미집행 확인(2026-11) — 검색으로 감시
    {"name": "쿠첸", "page": "102400861994912"},
    # ↓ 추천 추가: 음식물처리기/미니 김치냉장고 메타 광고를 실제로 돌리는 곳
    {"name": "린클", "page": "106787961038597", "pick": True},
    {"name": "휴렉", "page": "144751899404910", "pick": True},
    {"name": "아이닉", "page": "438248680056557", "pick": True},
    {"name": "신일전자", "page": "270623022791405", "pick": True},
    {"name": "더함", "page": "102365958559583", "pick": True},
    {"name": "미닉스", "page": "100739869635859"},
]

# 소구점 — 광고 문구(본문·제목·설명)에 이 말이 있으면 태그. 위에서부터 우선 표시.
APPEALS = {
    "할인·특가": r"할인|특가|세일|최저가|쿠폰|타임딜|블프|블랙\s?프라이데이|\d+\s?%|반값|가격\s?인하|핫딜",
    "사은품·증정": r"증정|사은품|선착순|기프트|1\+1|덤으로|추가\s?구성",
    "위생·냄새": r"냄새|악취|위생|세균|살균|초파리|벌레|청결|깨끗",
    "간편·자동": r"간편|편리|편하|자동|버튼\s?하나|손쉽|귀찮|한\s?번에|원터치",
    "처리방식": r"건조|분쇄|미생물|발효|분해|감량|바이오",
    "용량·사이즈": r"용량|\d+\s?L\b|리터|컴팩트|미니|소형|슬림|1인|자취",
    "저소음·전기료": r"소음|조용|저소음|전기료|전기세|에너지|효율|저전력",
    "디자인": r"디자인|인테리어|감성|컬러|색상|예쁜|모던",
    "후기·판매량": r"후기|리뷰|만족|누적|판매\s?\d|\d+\s?만\s?대|1위|베스트|완판|재구매",
    "기술·인증": r"특허|인증|기술력|검증|연구|AI|스마트|IoT",
    "지원금·보조금": r"지원금|보조금|환급|지자체",
    "렌탈·구독": r"렌탈|구독|월\s?[\d,]+\s?원|케어\s?서비스",
    "신제품": r"신제품|출시|NEW|런칭|최초|신상|첫\s?선",
    "신선·보관": r"신선|숙성|보관|아삭|김치\s?맛|저장",
    "선물·시즌": r"선물|명절|추석|설날|크리스마스|연말|혼수|이사",
}
CATS = {"음식물처리기": r"음식물|음쓰|처리기", "김치냉장고": r"김치\s?냉장고|김치냉장|김냉"}


def nodes_of(html: str) -> list[dict]:
    dec, out = json.JSONDecoder(), []
    for m in re.finditer(r'"collated_results":', html):
        try:
            arr, _ = dec.raw_decode(html, m.end())
            out += arr
        except ValueError:
            pass
    return out


def flatten(n: dict, brand: str, today: date) -> dict:
    s = n["snapshot"]
    cards = s.get("cards") or []
    vids = s.get("videos") or []
    imgs = s.get("images") or []
    first = cards[0] if cards else {}
    img = (first.get("resized_image_url") or first.get("video_preview_image_url")
           or (imgs[0].get("resized_image_url") if imgs else None)
           or (vids[0].get("video_preview_image_url") if vids else None))
    body = ((s.get("body") or {}).get("text") if isinstance(s.get("body"), dict) else s.get("body")) or first.get("body") or ""
    if "{{product." in body:
        body = ""   # 카탈로그 광고 템플릿 문구
    title = s.get("title") or first.get("title") or ""
    if "{{product." in title:
        title = ""
    desc = s.get("link_description") or first.get("link_description") or ""
    fmt = (s.get("display_format") or "").upper()
    fmt = {"IMAGE": "이미지", "VIDEO": "영상", "CAROUSEL": "캐러셀", "DPA": "카탈로그", "DCO": "다이나믹"}.get(fmt, fmt.lower() or "기타")
    if fmt == "다이나믹" and (vids or first.get("video_sd_url")):
        fmt = "영상"
    text = " ".join([body, title, desc])
    start = datetime.fromtimestamp(n["start_date"], KST).date()
    return {
        "id": n["ad_archive_id"], "brand": brand, "page": s.get("page_name") or n.get("page_name"),
        "start": start.isoformat(), "days": (today - start).days + 1,
        "format": fmt, "cards": len(cards), "body": body[:600], "title": title[:120], "desc": desc[:160],
        "cta": s.get("cta_text") or first.get("cta_text") or "",
        "img": img, "video": (vids[0].get("video_sd_url") if vids else None) or first.get("video_sd_url"),
        "platforms": n.get("publisher_platform") or [],
        "variants": n.get("collation_count") or 1,
        "appeals": [k for k, rx in APPEALS.items() if re.search(rx, text, re.I)],
        "cats": [k for k, rx in CATS.items() if re.search(rx, text)],
    }


def lib_url(b: dict, extra: str = "") -> str:
    base = "https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=KR&media_type=all"
    if "page" in b:
        return f"{base}&search_type=page&view_all_page_id={b['page']}{extra}"
    return f"{base}&search_type=keyword_unordered&q={b['q']}{extra}"


def collect(pg, b: dict, today: date) -> tuple[list[dict], int | None]:
    """브랜드 1곳 수집. 화면 자체가 안 열리면(차단·캡차) 예외 → 이전 데이터 유지."""
    old = (today - timedelta(days=LONG_DAYS)).isoformat()
    ads, total = {}, None
    for extra in ("", f"&start_date[min]=2015-01-01&start_date[max]={old}"):
        pg.goto(lib_url(b, extra), wait_until="domcontentloaded", timeout=60000)
        pg.wait_for_timeout(4000)
        html = pg.content()
        m = re.search(r'"search_results_connection":\{"count":(\d+)', html)
        if not m:
            raise RuntimeError("광고 라이브러리 응답 없음(차단/로그인벽 가능)")
        if not extra:
            total = int(m.group(1))
        for n in nodes_of(html):
            name = (n["snapshot"].get("page_name") or "").lower()
            if "match" in b and not any(k.lower() in name for k in b["match"]):
                continue
            ads[n["ad_archive_id"]] = flatten(n, b["name"], today)
        time.sleep(3)
    if "match" in b:
        total = len(ads)
    return list(ads.values()), total


def main():
    from playwright.sync_api import sync_playwright

    today = datetime.now(KST).date()
    prev = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {"ads": [], "brands": []}
    all_ads, brands, fails = [], [], 0
    with sync_playwright() as p:
        br = p.chromium.launch(headless=True)
        pg = br.new_page(locale="ko-KR", viewport={"width": 1280, "height": 900})
        for b in BRANDS:
            info = {"name": b["name"], "url": lib_url(b), "ours": b.get("ours", False), "pick": b.get("pick", False)}
            try:
                ads, total = collect(pg, b, today)
                info.update(total=total, ok=True)
                print(f"{b['name']}: 집행중 {total} · 수집 {len(ads)}")
            except Exception as e:  # 실패한 브랜드는 직전 데이터를 그대로 보여준다
                fails += 1
                ads = [a for a in prev["ads"] if a["brand"] == b["name"]]
                old = next((x for x in prev["brands"] if x["name"] == b["name"]), {})
                info.update(total=old.get("total"), ok=False, error=str(e)[:200])
                print(f"{b['name']}: 실패 — {e} (이전 {len(ads)}건 유지)")
            all_ads += ads
            brands.append(info)
        br.close()

    OUT.write_text(json.dumps({"updated": datetime.now(KST).strftime("%Y-%m-%d %H:%M"), "long_days": LONG_DAYS,
                               "brands": brands, "ads": all_ads}, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"저장 {OUT} — 광고 {len(all_ads)}건, 실패 {fails}/{len(BRANDS)}")
    if fails == len(BRANDS):
        sys.exit(1)   # 전부 막혔으면 Actions 를 빨갛게


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if sys.argv[1:] == ["test"]:   # 태깅 자체검사
        n = {"ad_archive_id": "1", "start_date": int(datetime(2026, 1, 1, tzinfo=KST).timestamp()), "publisher_platform": ["FACEBOOK"],
             "snapshot": {"page_name": "x", "display_format": "IMAGE", "body": {"text": "음식물 냄새 걱정 끝! 30% 할인 + 사은품 증정"}, "cards": [], "images": [], "videos": []}}
        a = flatten(n, "x", date(2026, 3, 1))
        assert a["appeals"][:3] == ["할인·특가", "사은품·증정", "위생·냄새"], a["appeals"]
        assert a["cats"] == ["음식물처리기"] and a["days"] == 60 and a["format"] == "이미지", a
        print("ok")
    else:
        main()
