#!/usr/bin/env python3
"""한양대병원(서울/구리) 구조 탐색: 진료과/의료진/시간표 링크 + 네트워크 JSON. python -u."""
from __future__ import annotations
from playwright.sync_api import sync_playwright
UA=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
INT=("json","/api/","ajax",".do","list","schedule","timetable","dept","doctor","medical")
KW=("오전","오후","진료","교수","정형","신경","월","화","수","목","금","휴진")

TARGETS={
 "한양대서울": "https://seoul.hyumc.com",
 "한양대구리": "https://guri.hyumc.com",
}

def snip(s,n=500): return " ".join((s or "").split())[:n]

def run(p,name,url):
    print("\n\n########## %s  %s ##########"%(name,url))
    cap=[]
    b=p.chromium.launch(); ctx=b.new_context(user_agent=UA,locale="ko-KR"); pg=ctx.new_page()
    def on(r):
        try:
            u=r.url; ct=r.headers.get("content-type","")
            if ("json" in ct) or any(k in u.lower() for k in INT):
                body=""
                if "json" in ct or "text" in ct:
                    try: body=r.text()
                    except: body=""
                cap.append((r.request.method,r.status,ct.split(";")[0],u,body))
        except: pass
    pg.on("response",on)
    try: pg.goto(url,wait_until="domcontentloaded",timeout=40000)
    except Exception as e: print("[goto]",type(e).__name__)
    pg.wait_for_timeout(3500)
    print("title:",pg.title())
    print("--- 네트워크 %d건 ---"%len(cap))
    for m,st,ct,u,body in cap[:25]:
        kw=[k for k in KW if k in (body or "")]
        print("  [%s %s] %s %s len=%d%s"%(m,st,ct,u[:120],len(body)," <<<KW "+",".join(kw[:6]) if kw else ""))
    # 정형/신경/의료진/시간표 링크
    print("--- 관련 링크 ---")
    try:
        for x in pg.eval_on_selector_all("a[href]","els=>els.map(function(e){return (e.textContent||'').trim().replace(/\\s+/g,' ').slice(0,16)+' || '+(e.getAttribute('href')||'');}).filter(function(s){return s.indexOf('정형')>=0||s.indexOf('신경')>=0||s.indexOf('의료진')>=0||s.indexOf('진료과')>=0||s.indexOf('시간표')>=0||s.indexOf('depart')>=0||s.indexOf('doctor')>=0||s.indexOf('medical')>=0;}).slice(0,30)"):
            print("   ",x)
    except Exception as e: print("[link]",e)
    b.close()

def main():
    with sync_playwright() as p:
        for n,u in TARGETS.items():
            try: run(p,n,u)
            except Exception as e: print("[run err]",n,e)
    print("\n[done]")

if __name__=="__main__": main()
