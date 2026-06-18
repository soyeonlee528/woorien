#!/usr/bin/env python3
"""정밀 탐색: 진료과 코드 매핑 + 시간표 표 HTML 구조 확인 (파서 작성용)."""
from __future__ import annotations
from playwright.sync_api import sync_playwright
UA=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

def go(ctx,url,wait="domcontentloaded"):
    pg=ctx.new_page()
    try: pg.goto(url,wait_until=wait,timeout=40000)
    except Exception as e: print("[goto]",type(e).__name__)
    pg.wait_for_timeout(2000); return pg

def deptlinks(pg,substr):
    return pg.eval_on_selector_all("a[href]","els=>els.map(function(e){return (e.textContent||'').trim().replace(/\\s+/g,' ')+' || '+e.getAttribute('href');}).filter(function(x){return (x.indexOf('정형')>=0||x.indexOf('신경')>=0)&&x.indexOf('"+substr+"')>=0;})")

def tableHTML(pg,n=0,lim=3500):
    return pg.eval_on_selector_all("table","els=>els.map(function(t){return t.outerHTML;})").__getitem__(n) if pg.query_selector("table") else "(no table)"

def main():
    with sync_playwright() as p:
        b=p.chromium.launch(); ctx=b.new_context(user_agent=UA,locale="ko-KR")
        # 1) 을지 진료과 코드 매핑(의정부)
        print("\n#### 을지 진료과 코드(의정부) ####")
        pg=go(ctx,"https://www.uemc.ac.kr/clinic/clinic_pg04.jsp?dept=ABFDAA")
        for x in deptlinks(pg,"clinic_pg04"): print("  ",x)
        # 2) 을지 정형외과 표 HTML
        print("\n#### 을지 정형외과 표 HTML ####")
        ts=pg.eval_on_selector_all("table","els=>els.map(function(t){return t.outerHTML;})")
        print((ts[0] if ts else "(no table)")[:4000])
        # 3) 경희대 진료과 코드
        print("\n\n#### 경희대 진료과 list ####")
        pg2=go(ctx,"https://med.khmc.or.kr/kr/treatment/department/list.do")
        for x in pg2.eval_on_selector_all("a[href]","els=>els.map(function(e){return (e.textContent||'').trim().replace(/\\s+/g,' ')+' || '+e.getAttribute('href');}).filter(function(x){return x.indexOf('정형')>=0||x.indexOf('신경외과')>=0;}).slice(0,20)"): print("  ",x)
        # 4) 경희대 정형외과 timetable 표 (코드 2210000000 정형외과 추정 시도 여러개)
        for code in ["2210000000","2200000000","2230000000"]:
            pg3=go(ctx,"https://med.khmc.or.kr/kr/treatment/department/%s/timetable.do"%code)
            ts=pg3.eval_on_selector_all("table","els=>els.map(function(t){return (t.innerText||'').slice(0,160);})")
            print("  [khmc %s] title=%s tables=%d t0=%s"%(code,pg3.title()[:30],len(ts),(ts[0] if ts else "")[:140]))
        # 5) 강동성심
        print("\n\n#### 강동성심 정형외과 ####")
        pg4=go(ctx,"https://www.kdh.or.kr/sub201.php?dept=111240")
        print("title:",pg4.title())
        ts=pg4.eval_on_selector_all("table","els=>els.map(function(t){return t.outerHTML;})")
        print("tables=%d"%len(ts)); print((ts[0] if ts else "(no table)")[:3500])
        b.close()
    print("\n[done]")

if __name__=="__main__": main()
