#!/usr/bin/env python3
"""WAF/접근 진단용 스크립트.

GitHub Actions(클라우드 IP)에서 대상 병원 페이지에 접속이 되는지,
- (1) requests(일반 HTTP) 와
- (2) Playwright(진짜 헤드리스 브라우저)
두 방식으로 시도해 상태/차단 여부를 출력한다.

결과 해석:
* requests 200 → 단순 수집 가능
* requests 403 / Playwright 200 → 봇/JS 검사 → 브라우저 방식 필요
* 둘 다 403/타임아웃 → IP 지오블록 가능성 → 한국 IP 경유(프록시) 필요
"""
from __future__ import annotations

TARGETS = {
    "anam_doctor": "https://anam.kumc.or.kr/kr/doctor-department/doctor.do",
    "anam_legacy": "http://anam.kumc.or.kr/guide/opdClinic02.do",
    "cmcujb_ortho": "https://www.cmcujb.or.kr/page/department/A/103/1",
}

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
    "Upgrade-Insecure-Requests": "1",
}


def snippet(text: str, n: int = 240) -> str:
    t = " ".join((text or "").split())
    return t[:n]


def probe_requests():
    import requests
    print("\n===== [1] requests =====")
    for name, url in TARGETS.items():
        try:
            r = requests.get(url, headers=HEADERS, timeout=25)
            body = r.text
            kw = [k for k in ("교수", "진료", "외래", "의료진", "정형외과", "신경외과") if k in body]
            print(f"[{name}] {r.status_code} len={len(body)} keywords={kw}")
            print(f"    snippet: {snippet(body)}")
        except Exception as e:
            print(f"[{name}] ERROR {type(e).__name__}: {e}")


def probe_playwright():
    print("\n===== [2] Playwright (headless chromium) =====")
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        print(f"playwright 미설치: {e}")
        return
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(user_agent=UA, locale="ko-KR")
        page = ctx.new_page()
        for name, url in TARGETS.items():
            try:
                resp = page.goto(url, wait_until="networkidle", timeout=30000)
                page.wait_for_timeout(1500)
                body = page.content()
                kw = [k for k in ("교수", "진료", "외래", "의료진", "정형외과", "신경외과") if k in body]
                print(f"[{name}] status={resp.status if resp else '?'} title={page.title()!r} len={len(body)} keywords={kw}")
                print(f"    snippet: {snippet(body)}")
            except Exception as e:
                print(f"[{name}] ERROR {type(e).__name__}: {e}")
        browser.close()


if __name__ == "__main__":
    probe_requests()
    probe_playwright()
    print("\n[done] probe finished")
