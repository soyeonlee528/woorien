#!/usr/bin/env python3
"""구조 탐색용: SPA가 호출하는 내부 API/JSON 응답과 주요 링크를 덤프한다.

목표: 고대안암(doctor.do), 의정부성모(정형외과/신경외과) 페이지가
교수 목록과 진료시간표를 어떤 엔드포인트/구조로 받는지 파악해
정확한 수집 adapter 를 작성하기 위한 정보 수집.
"""
from __future__ import annotations

from playwright.sync_api import sync_playwright

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

TARGETS = {
    "anam_doctor": "https://anam.kumc.or.kr/kr/doctor-department/doctor.do",
    "cmcujb_ortho": "https://www.cmcujb.or.kr/page/department/A/103/1",
    "cmcujb_dept_list": "https://www.cmcujb.or.kr/page/department/A/160/2",
}

KEYWORDS = ("교수", "진료", "외래", "의료진", "정형외과", "신경외과", "schedule", "dept", "doctor")
INTEREST = ("api", "json", "doctor", "staff", "dept", "depart", "schedule",
            "member", "medical", "list", "search", ".do", "ajax")


def snippet(s, n=500):
    return " ".join((s or "").split())[:n]


def run_target(p, name, url):
    print(f"\n\n########## {name}  {url} ##########")
    captured = []

    browser = p.chromium.launch()
    ctx = browser.new_context(user_agent=UA, locale="ko-KR")
    page = ctx.new_page()

    def on_response(resp):
        try:
            u = resp.url
            ctype = resp.headers.get("content-type", "")
            if ("json" in ctype) or any(k in u.lower() for k in INTEREST):
                body = ""
                if "json" in ctype or "text" in ctype:
                    try:
                        body = resp.text()
                    except Exception:
                        body = ""
                captured.append((resp.request.method, resp.status, ctype.split(";")[0], u, body))
        except Exception:
            pass

    page.on("response", on_response)
    try:
        page.goto(url, wait_until="networkidle", timeout=45000)
        page.wait_for_timeout(2500)
    except Exception as e:
        print(f"[goto error] {type(e).__name__}: {e}")

    print(f"--- 캡처된 네트워크 응답 {len(captured)}건 (관심 필터) ---")
    for method, status, ctype, u, body in captured:
        has_kw = [k for k in KEYWORDS if k in (body or "")]
        flag = " <<<KW" if has_kw else ""
        print(f"  [{method} {status}] {ctype} {u}  bodylen={len(body)}{flag}")
        if has_kw and body:
            print(f"      body: {snippet(body, 700)}")

    # 주요 링크(진료과/의료진 상세로 가는 경로) 덤프
    try:
        links = page.eval_on_selector_all(
            "a[href]",
            "els => els.map(e => e.getAttribute('href')).filter(h => h && (h.includes('doctor')||h.includes('dept')||h.includes('depart')||h.includes('staff')||h.includes('medical'))).slice(0,40)")
        print(f"--- 관련 링크 {len(links)}개 ---")
        for h in sorted(set(links)):
            print(f"    {h}")
    except Exception as e:
        print(f"[link error] {e}")

    browser.close()


if __name__ == "__main__":
    with sync_playwright() as p:
        for name, url in TARGETS.items():
            run_target(p, name, url)
    print("\n[done] discover finished")
