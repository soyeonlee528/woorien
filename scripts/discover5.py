#!/usr/bin/env python3
"""강동성심·서울현대·강남새로운(PHP) + 경희대 진료과코드 탐색. python -u 로 실행."""
from __future__ import annotations
from playwright.sync_api import sync_playwright
UA=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

def go(ctx,url,wait="networkidle",t=40000):
    pg=ctx.new_page(); print("  [load]",url)
    try: pg.goto(url,wait_until=wait,timeout=t)
    except Exception as e: print("  [goto]",type(e).__name__)
    pg.wait_for_timeout(1200); print("  [loaded] title:",pg.title()); return pg

def dump_tables(pg,n=4,lim=2200):
    ts=pg.eval_on_selector_all("table","els=>els.map(function(t){return t.outerHTML;})")
    print("  표 %d개"%len(ts))
    for i,t in enumerate(ts[:n]):
        print("\n  === table[%d] ===\n%s\n"%(i," ".join(t.split())[:lim]))

def dump_selects(pg):
    s=pg.eval_on_selector_all("select","els=>els.map(function(sel){return (sel.getAttribute('name')||sel.getAttribute('id')||'?')+': '+Array.from(sel.options).slice(0,30).map(function(o){return (o.textContent||'').trim()+'='+o.value;}).join(' | ');}).slice(0,6)")
    print("  selects(%d):"%len(s))
    for x in s: print("    ",x[:400])

def dump_dept_links(pg,sub):
    for x in pg.eval_on_selector_all("a[href]","els=>els.map(function(e){return (e.textContent||'').trim().replace(/\\s+/g,' ').slice(0,18)+' || '+(e.getAttribute('href')||'');}).filter(function(s){return s.indexOf('"+sub+"')>=0;}).slice(0,40)"):
        print("    ",x)

def main():
    with sync_playwright() as p:
        b=p.chromium.launch(); ctx=b.new_context(user_agent=UA,locale="ko-KR")
        ctx.set_default_timeout(15000)

        print("\n\n########## 강동성심 sub201.php 정형(111240) ##########")
        pg=go(ctx,"https://www.kdh.or.kr/sub201.php?dept=111240")
        dump_selects(pg); dump_tables(pg);
        print("  dept/doctor 링크:"); dump_dept_links(pg,"sub201")

        print("\n\n########## 서울현대 sub0103.php ##########")
        pg2=go(ctx,"https://www.seoulhyundai.co.kr/page/sub0103.php")
        dump_selects(pg2); dump_tables(pg2)
        print("  관련 링크:");
        for x in pg2.eval_on_selector_all("a[href]","els=>els.map(function(e){return (e.textContent||'').trim().replace(/\\s+/g,' ').slice(0,18)+' || '+(e.getAttribute('href')||'');}).filter(function(s){return s.indexOf('sub01')>=0||s.indexOf('doctor')>=0||s.indexOf('dept')>=0;}).slice(0,30)"): print("    ",x)

        print("\n\n########## 강남새로운 sub0103.php ##########")
        pg3=go(ctx,"https://saerounhospital.com/view/sub0103.php?menu1=open")
        dump_selects(pg3); dump_tables(pg3)
        print("  관련 링크:")
        for x in pg3.eval_on_selector_all("a[href]","els=>els.map(function(e){return (e.textContent||'').trim().replace(/\\s+/g,' ').slice(0,18)+' || '+(e.getAttribute('href')||'');}).filter(function(s){return s.indexOf('sub01')>=0||s.indexOf('doctor')>=0||s.indexOf('dept')>=0;}).slice(0,30)"): print("    ",x)

        print("\n\n########## 경희대 list.do 진료과코드 ##########")
        pg4=go(ctx,"https://med.khmc.or.kr/kr/treatment/department/list.do")
        codes=pg4.evaluate("""() => {
          const out=[];
          document.querySelectorAll('a,button,li,div,span').forEach(el=>{
            const t=(el.textContent||'').trim();
            if((t==='정형외과'||t==='신경외과')){
              const h=el.getAttribute('href')||''; const oc=el.getAttribute('onclick')||'';
              const da=Array.from(el.attributes).map(a=>a.name+'='+a.value).join(',');
              out.push(t+' :: href='+h+' :: onclick='+oc.slice(0,80)+' :: attrs='+da.slice(0,160));
            }
          });
          return out.slice(0,12);
        }""")
        print("  매칭(%d):"%len(codes))
        for c in codes: print("    ",c)
        b.close()
    print("\n[done]")

if __name__=="__main__": main()
