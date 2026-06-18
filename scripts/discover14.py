#!/usr/bin/env python3
"""경희 timetable.do(정형 2050000000): 의사명 + 시간표 묶음 구조 정밀 덤프. python -u."""
from __future__ import annotations
import re
from playwright.sync_api import sync_playwright
UA=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

def main():
    with sync_playwright() as p:
        b=p.chromium.launch(); ctx=b.new_context(user_agent=UA,locale="ko-KR")
        ctx.set_default_timeout(20000)
        bodies={}
        pg=ctx.new_page()
        pg.on("response",lambda r:bodies.__setitem__(r.url,r.text()) if "timetable.do" in r.url and "html" in r.headers.get("content-type","") else None)
        try: pg.goto("https://med.khmc.or.kr/kr/treatment/department/2050000000/timetable.do",wait_until="commit",timeout=20000)
        except Exception as e: print("[goto]",type(e).__name__)
        pg.wait_for_timeout(5000); pg.close()
        h=""
        for u,bd in bodies.items():
            if "timetable.do" in u: h=bd; break
        print("len",len(h),"진료일정 횟수",h.count("진료일정"))
        # 본문 영역만: '진료일정' 첫 등장 ~ 그 앞 1800자
        i=h.find("진료일정")
        if i>0:
            print("\n== 첫 '진료일정' 앞 1800자 ==\n"," ".join(h[max(0,i-1800):i+60].split()))
        # 의사명 추정: <strong>/<dt>/<h3>/<h4>/<a ...doctor>/class*=doc
        print("\n== 이름 후보 태그 ==")
        for pat in [r'<strong[^>]*>[\s\S]{0,40}?</strong>', r'<dt[^>]*>[\s\S]{0,40}?</dt>',
                    r'<h[34][^>]*>[\s\S]{0,40}?</h[34]>', r'<a[^>]*doctor[^>]*>[\s\S]{0,40}?</a>',
                    r'class="[^"]*(?:doc|prof|name|tit)[^"]*"[^>]*>[\s\S]{0,40}?<']:
            ms=re.findall(pat,h,re.I)[:6]
            if ms:
                print(" 패턴",pat[:25])
                for m in ms: print("   ", " ".join(m.split())[:110])
        # 두번째 timetable 표 직전 600자 (각 의사 묶음 경계 확인)
        idxs=[m.start() for m in re.finditer("진료일정",h)][:4]
        for k,ix in enumerate(idxs):
            print("\n== 진료일정[%d] 앞 400자 =="%k," ".join(h[max(0,ix-400):ix+20].split()))
        b.close()
    print("\n[done]")

if __name__=="__main__": main()
