#!/usr/bin/env python3
"""경찰병원 + 경희의료원: 메인 문서 응답 body를 캡처해서 파싱 설계. python -u."""
from __future__ import annotations
import re
from playwright.sync_api import sync_playwright
UA=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

def grab(ctx,url,match,t=12000):
    bodies={}
    pg=ctx.new_page()
    def on(r):
        try:
            if match in r.url and "text/html" in r.headers.get("content-type",""):
                bodies[r.url]=r.text()
        except: pass
    pg.on("response",on)
    try: pg.goto(url,wait_until="commit",timeout=t)
    except Exception as e: print("  [goto]",type(e).__name__)
    pg.wait_for_timeout(5000)
    pg.close()
    for u,b in bodies.items():
        if match in u: return b
    return ""

def around(html, kw, n=260, maxhits=6):
    out=[]; i=0
    for _ in range(maxhits):
        j=html.find(kw,i)
        if j<0: break
        out.append(" ".join(html[max(0,j-n):j+n].split())); i=j+len(kw)
    return out

def main():
    with sync_playwright() as p:
        b=p.chromium.launch(); ctx=b.new_context(user_agent=UA,locale="ko-KR")
        ctx.set_default_timeout(12000)

        print("\n\n########## 경찰병원 ScheduleList ##########")
        h=grab(ctx,"https://www.nph.go.kr/nph/med/schedule/ScheduleList.do?menuNo=200022","ScheduleList.do")
        print("len",len(h),"table태그",h.count("<table"),"tr",h.count("<tr"))
        for s in around(h,"정형외과",340,5): print("   [정형]",s)
        for s in around(h,"오전",240,5): print("   [오전]",s)

        print("\n\n########## 경희의료원 list.do ##########")
        h2=grab(ctx,"https://med.khmc.or.kr/kr/treatment/department/list.do","department/list.do")
        print("len",len(h2))
        print("-- timetable 링크 --")
        for m in re.findall(r'[^"\']*timetable[^"\']*', h2)[:8]: print("   ",m[:120])
        print("-- department/<코드> 패턴 --")
        for m in sorted(set(re.findall(r'department/(\d{6,})', h2)))[:25]: print("   code",m)
        print("-- '정형외과' 부근 --")
        for s in around(h2,"정형외과",300,6): print("   ",s)
        print("-- '신경외과' 부근 --")
        for s in around(h2,"신경외과",300,4): print("   ",s)
        b.close()
    print("\n[done]")

if __name__=="__main__": main()
