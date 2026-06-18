#!/usr/bin/env python3
"""경찰병원 + 경희의료원 RAW HTML 파싱 설계용. page.content()로 원문 HTML 확보. python -u."""
from __future__ import annotations
import re
from playwright.sync_api import sync_playwright
UA=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

def get_html(ctx,url,wait,t):
    pg=ctx.new_page()
    try: pg.goto(url,wait_until=wait,timeout=t)
    except Exception as e: print("  [goto]",type(e).__name__)
    pg.wait_for_timeout(1500)
    try: html=pg.content()
    except Exception as e: html=""; print("  [content]",e)
    print("  title:",pg.title()); pg.close(); return html

def around(html, kw, n=240, maxhits=6):
    out=[]; i=0
    for _ in range(maxhits):
        j=html.find(kw,i)
        if j<0: break
        out.append(" ".join(html[max(0,j-n):j+n].split())); i=j+len(kw)
    return out

def main():
    with sync_playwright() as p:
        b=p.chromium.launch(); ctx=b.new_context(user_agent=UA,locale="ko-KR")
        ctx.set_default_timeout(15000)

        print("\n\n########## 경찰병원 ScheduleList ##########")
        h=get_html(ctx,"https://www.nph.go.kr/nph/med/schedule/ScheduleList.do?menuNo=200022","networkidle",40000)
        print("len",len(h),"table태그",h.count("<table"))
        print("-- '정형외과' 부근 --")
        for s in around(h,"정형외과",300,6): print("   ",s)
        print("-- '오전' 부근 --")
        for s in around(h,"오전",220,5): print("   ",s)

        print("\n\n########## 경희의료원 list.do ##########")
        h2=get_html(ctx,"https://med.khmc.or.kr/kr/treatment/department/list.do","commit",20000)
        print("len",len(h2))
        print("-- timetable 링크 --")
        for m in re.findall(r'href="[^"]*timetable[^"]*"', h2)[:10]: print("   ",m)
        print("-- department/<코드> --")
        for m in sorted(set(re.findall(r'/treatment/department/(\d{6,})', h2)))[:25]: print("   code",m)
        print("-- '정형외과' 부근 --")
        for s in around(h2,"정형외과",260,6): print("   ",s)
        print("-- '신경외과' 부근 --")
        for s in around(h2,"신경외과",260,4): print("   ",s)
        b.close()
    print("\n[done]")

if __name__=="__main__": main()
