#!/usr/bin/env python3
"""경찰병원(domcontentloaded 캡처) + 경희 timetable.do 표 구조. python -u."""
from __future__ import annotations
import re
from playwright.sync_api import sync_playwright
UA=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

def grab(ctx,url,match,wait="domcontentloaded",t=35000,after=6000):
    bodies={}
    pg=ctx.new_page()
    def on(r):
        try:
            if match in r.url and "html" in r.headers.get("content-type",""):
                bodies[r.url]=r.text()
        except: pass
    pg.on("response",on)
    try: pg.goto(url,wait_until=wait,timeout=t)
    except Exception as e: print("  [goto]",type(e).__name__)
    pg.wait_for_timeout(after)
    pg.close()
    for u,bd in bodies.items():
        if match in u: return bd
    return ""

def around(html, kw, n=300, maxhits=6):
    out=[]; i=0
    for _ in range(maxhits):
        j=html.find(kw,i)
        if j<0: break
        out.append(" ".join(html[max(0,j-n):j+n].split())); i=j+len(kw)
    return out

def main():
    with sync_playwright() as p:
        b=p.chromium.launch(); ctx=b.new_context(user_agent=UA,locale="ko-KR")
        ctx.set_default_timeout(20000)

        print("\n\n########## 경찰병원 ScheduleList (domcontentloaded) ##########")
        h=grab(ctx,"https://www.nph.go.kr/nph/med/schedule/ScheduleList.do?menuNo=200022","ScheduleList.do")
        print("len",len(h),"table",h.count("<table"),"tr",h.count("<tr"),"tbody",h.count("<tbody"))
        # 진료과별 시간표 컨테이너 추정: id/class 에 dept 코드 또는 schedule
        print("-- '정형외과' 부근 --")
        for s in around(h,"정형외과",420,4): print("   ",s)
        print("-- 첫 <table ... > ~ 두번째 --")
        for m in re.findall(r'<table[\s\S]{0,1600}?</table>', h)[:3]:
            print("   TABLE:"," ".join(m.split())[:1400])

        print("\n\n########## 경희 정형외과 timetable.do (2050000000) ##########")
        h2=grab(ctx,"https://med.khmc.or.kr/kr/treatment/department/2050000000/timetable.do","timetable.do",wait="commit",t=20000,after=5000)
        print("len",len(h2),"table",h2.count("<table"))
        for m in re.findall(r'<table[\s\S]{0,2400}?</table>', h2)[:2]:
            print("   TABLE:"," ".join(m.split())[:2200])
        print("-- '오전' 부근 --")
        for s in around(h2,"오전",260,4): print("   ",s)
        b.close()
    print("\n[done]")

if __name__=="__main__": main()
