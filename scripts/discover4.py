#!/usr/bin/env python3
"""경희대병원 + 경찰병원 구조 탐색 (정형/신경 진료과 코드 + 시간표 표)."""
from __future__ import annotations
from playwright.sync_api import sync_playwright
UA=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

def go(ctx,url,t=25000):
    pg=ctx.new_page()
    try: pg.goto(url,wait_until="domcontentloaded",timeout=t)
    except Exception as e: print("  [goto]",type(e).__name__)
    pg.wait_for_timeout(1200); return pg

def main():
    with sync_playwright() as p:
        b=p.chromium.launch(); ctx=b.new_context(user_agent=UA,locale="ko-KR")

        print("\n\n########## 경희대 진료과 목록 list.do ##########")
        pg=go(ctx,"https://med.khmc.or.kr/kr/treatment/department/list.do")
        print("title:",pg.title())
        for x in pg.eval_on_selector_all("a[href]",
            "els=>els.map(function(e){var t=(e.textContent||'').trim().replace(/\\s+/g,' ');var h=e.getAttribute('href')||'';return t+' || '+h;}).filter(function(s){return (s.indexOf('정형')>=0||s.indexOf('신경외과')>=0)&&(s.indexOf('department')>=0||s.indexOf('timetable')>=0||s.indexOf('Dept')>=0||/\\d{6,}/.test(s));}).slice(0,30)"):
            print("   ",x)

        print("\n\n########## 경찰병원 진료시간표 ScheduleList ##########")
        pg2=go(ctx,"https://www.nph.go.kr/nph/med/schedule/ScheduleList.do?menuNo=200022")
        print("title:",pg2.title())
        # select/option 으로 진료과 선택하는지 확인
        opts=pg2.eval_on_selector_all("select option","els=>els.map(function(e){return (e.textContent||'').trim()+' = '+(e.getAttribute('value')||'');}).filter(function(s){return s.length>2;}).slice(0,40)")
        print("--- select options (%d) ---"%len(opts))
        for o in opts: print("   ",o)
        # 표 구조
        ts=pg2.eval_on_selector_all("table","els=>els.map(function(t){return t.outerHTML;})")
        print("--- 표 %d개 ---"%len(ts))
        for i,t in enumerate(ts[:3]):
            print("\n  [table %d] %s\n"%(i,t[:2500]))
        # 정형/신경 관련 링크
        print("--- 정형/신경 링크 ---")
        for x in pg2.eval_on_selector_all("a[href]","els=>els.map(function(e){return (e.textContent||'').trim()+' || '+(e.getAttribute('href')||'');}).filter(function(s){return s.indexOf('정형')>=0||s.indexOf('신경외과')>=0;}).slice(0,20)"):
            print("   ",x)
        b.close()
    print("\n[done]")

if __name__=="__main__": main()
