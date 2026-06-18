#!/usr/bin/env python3
"""경찰병원(nph) 우선 → 경희대(khmc) 구조 탐색. -u(unbuffered)로 실행해 nph 결과를 먼저 확보."""
from __future__ import annotations
from playwright.sync_api import sync_playwright
UA=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

def go(ctx,url,t=45000):
    pg=ctx.new_page()
    print("  [load]",url)
    # 경찰병원/경희대는 anti-bot/JS 로딩으로 domcontentloaded가 안 끝남 → networkidle 사용
    try: pg.goto(url,wait_until="networkidle",timeout=t)
    except Exception as e: print("  [goto]",type(e).__name__)
    pg.wait_for_timeout(1000); print("  [loaded] title:",pg.title()); return pg

def dump_tables(pg,n=4,lim=2600):
    ts=pg.eval_on_selector_all("table","els=>els.map(function(t){return t.outerHTML;})")
    print("  표 %d개"%len(ts))
    for i,t in enumerate(ts[:n]):
        print("\n  === table[%d] ===\n%s\n"%(i," ".join(t.split())[:lim]))

def main():
    with sync_playwright() as p:
        b=p.chromium.launch(); ctx=b.new_context(user_agent=UA,locale="ko-KR")
        ctx.set_default_timeout(15000)  # eval 등이 무한 대기하지 않도록 상한

        print("\n\n########## 경찰병원 진료시간표 ScheduleList ##########")
        pg=go(ctx,"https://www.nph.go.kr/nph/med/schedule/ScheduleList.do?menuNo=200022")
        opts=pg.eval_on_selector_all("select option","els=>els.map(function(e){return (e.textContent||'').trim()+' = '+(e.getAttribute('value')||'');}).slice(0,60)")
        print("  select options(%d):"%len(opts))
        for o in opts:
            if len(o)>2: print("     ",o)
        forms=pg.eval_on_selector_all("form","els=>els.map(function(f){return (f.getAttribute('action')||'')+' | '+Array.from(f.querySelectorAll('input,select')).map(function(i){return (i.getAttribute('name')||'')+'='+(i.getAttribute('value')||'');}).join(',');}).slice(0,8)")
        print("  forms:")
        for f in forms: print("     ",f[:300])
        dump_tables(pg)
        print("  정형/신경 링크:")
        for x in pg.eval_on_selector_all("a[href]","els=>els.map(function(e){return (e.textContent||'').trim().replace(/\\s+/g,' ')+' || '+(e.getAttribute('href')||'');}).filter(function(s){return s.indexOf('정형')>=0||s.indexOf('신경외과')>=0;}).slice(0,20)"):
            print("     ",x)

        print("\n\n########## 경희대 list.do ##########")
        pg2=go(ctx,"https://med.khmc.or.kr/kr/treatment/department/list.do")
        print("  정형/신경 진료과 링크:")
        for x in pg2.eval_on_selector_all("a[href]","els=>els.map(function(e){return (e.textContent||'').trim().replace(/\\s+/g,' ')+' || '+(e.getAttribute('href')||'');}).filter(function(s){return (s.indexOf('정형')>=0||s.indexOf('신경외과')>=0);}).slice(0,30)"):
            print("     ",x)
        b.close()
    print("\n[done]")

if __name__=="__main__": main()
