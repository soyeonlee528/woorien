#!/usr/bin/env python3
"""경희 timetable: profile_outer(의사 한 명 묶음) 블록 구조 + 이름 위치. python -u."""
from __future__ import annotations
import re
from playwright.sync_api import sync_playwright
UA=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

def fetch(ctx,url):
    h=""
    for a in range(5):
        bodies={}
        pg=ctx.new_page()
        def on(r):
            try:
                if "timetable.do" in r.url and "html" in r.headers.get("content-type",""):
                    bodies[r.url]=r.text()
            except: pass
        pg.on("response",on)
        try: pg.goto(url,wait_until="commit",timeout=25000)
        except Exception as e: print("[goto%d]"%a,type(e).__name__)
        pg.wait_for_timeout(5000)
        for u,bd in bodies.items():
            if "timetable.do" in u and len(bd)>5000: h=bd
        pg.close()
        if len(h)>5000: break
    return h

def main():
    with sync_playwright() as p:
        b=p.chromium.launch(); ctx=b.new_context(user_agent=UA,locale="ko-KR")
        ctx.set_default_timeout(20000)
        h=fetch(ctx,"https://med.khmc.or.kr/kr/treatment/department/2050000000/timetable.do")
        print("len",len(h))
        # profile_outer 블록(첫 2개) 통째로
        for m in re.findall(r'<div class="clearfix profile_outer">[\s\S]{0,2600}?</table>', h)[:2]:
            print("\n=== profile_outer ===\n"," ".join(m.split())[:2600])
        # doctor_profile_list 블록(이름 들어있을 영역) 앞부분
        for m in re.findall(r'doctor_profile_list[\s\S]{0,500}', h)[:2]:
            print("\n=== doctor_profile_list ===\n"," ".join(m.split())[:500])
        # profile.do 링크 앞 400자(이름 위치 확인)
        for m in re.finditer(r'/kr/treatment/doctor/(\d+)/profile\.do', h):
            j=m.start()
            print("\n[doc %s 앞 400자]"%m.group(1)," ".join(h[max(0,j-400):j].split())[-300:])
        b.close()
    print("\n[done]")

if __name__=="__main__": main()
