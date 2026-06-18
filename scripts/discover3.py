#!/usr/bin/env python3
"""을지(노원/의정부) 시간표 표 구조 + 진료과 코드 매핑만 빠르게 덤프 (파서 작성용)."""
from __future__ import annotations
from playwright.sync_api import sync_playwright
UA=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

SITES={
    "의정부을지": "https://www.uemc.ac.kr/clinic/clinic_pg04.jsp?dept=ABFDAA",
    "노원을지":   "https://www.eulji.or.kr/clinic/clinic_pg04.jsp?dept=ABFDAA",
}

def main():
    with sync_playwright() as p:
        b=p.chromium.launch(); ctx=b.new_context(user_agent=UA,locale="ko-KR")
        for nm,url in SITES.items():
            print("\n\n########## %s  %s ##########"%(nm,url))
            pg=ctx.new_page()
            try: pg.goto(url,wait_until="domcontentloaded",timeout=40000)
            except Exception as e: print("[goto]",type(e).__name__)
            pg.wait_for_timeout(1500)
            # 사이드바 진료과 코드 매핑(정형/신경만)
            print("--- 진료과 코드(정형/신경) ---")
            for x in pg.eval_on_selector_all("a[href*='dept=']",
                "els=>els.map(function(e){var t=(e.textContent||'').trim().replace(/\\s+/g,' ');var h=e.getAttribute('href')||'';var m=h.match(/dept=([A-Z0-9]+)/);return t+' || '+(m?m[1]:'?');}).filter(function(s){return s.indexOf('정형')>=0||s.indexOf('신경')>=0;})"):
                print("   ",x)
            # 메인 표 outerHTML
            ts=pg.eval_on_selector_all("table","els=>els.map(function(t){return t.outerHTML;})")
            print("--- 표 %d개. table[0] outerHTML ---"%len(ts))
            print((ts[0] if ts else "(no table)")[:6000])
            pg.close()
        b.close()
    print("\n[done]")

if __name__=="__main__": main()
