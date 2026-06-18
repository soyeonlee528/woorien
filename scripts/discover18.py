#!/usr/bin/env python3
"""한양대서울(정형외과/의료진) + 혜성병원 구조 탐색. python -u."""
from __future__ import annotations
from playwright.sync_api import sync_playwright
UA=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
INT=("json","/api/","ajax",".do","list","schedule","timetable","dept","doctor","mediteam","treat")
KW=("오전","오후","진료","교수","정형","신경","월","화","수","목","금","휴진")

TARGETS={
 "한양서울_정형외과": "https://seoul.hyumc.com/seoul/mediteam/mediofCent.do?action=detailList&searchCondition1=seqMediteam&searchCommonSeq=29&searchCommonCd2=OS&searchKeyword=%EC%A0%95%ED%98%95%EC%99%B8%EA%B3%BC&userTab1=intro",
 "한양서울_의료진찾기": "https://seoul.hyumc.com/seoul/mediteam/mditeam.do",
 "혜성병원": "https://www.hsmcenter.com/",
}

def run(p,name,url):
    print("\n\n########## %s ##########\n%s"%(name,url))
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
    for m,st,ct,u,body in cap[:30]:
        kw=[k for k in KW if k in (body or "")]
        print("  [%s %s] %s %s len=%d%s"%(m,st,ct,u[:120],len(body)," <<<KW "+",".join(kw[:6]) if kw else ""))
        if kw and "json" in ct: print("     body:"," ".join((body or "").split())[:400])
    try:
        ts=pg.eval_on_selector_all("table","els=>els.slice(0,4).map(function(t){return (t.innerText||'').slice(0,300);})")
        print("--- 표 %d개 ---"%len(ts))
        for i,t in enumerate(ts): print("  [t%d]"%i," ".join((t or '').split())[:300])
    except Exception as e: print("[table]",e)
    print("--- 관련 링크 ---")
    try:
        for x in pg.eval_on_selector_all("a[href]","els=>els.map(function(e){return (e.textContent||'').trim().replace(/\\s+/g,' ').slice(0,16)+' || '+(e.getAttribute('href')||'');}).filter(function(s){return s.indexOf('정형')>=0||s.indexOf('신경')>=0||s.indexOf('의료진')>=0||s.indexOf('진료')>=0||s.indexOf('시간표')>=0||s.indexOf('예약')>=0||s.indexOf('mediteam')>=0||s.indexOf('doctor')>=0;}).slice(0,25)"):
            print("   ",x)
    except Exception as e: print("[link]",e)
    b.close()

def main():
    with sync_playwright() as p:
        for n,u in TARGETS.items():
            try: run(p,n,u)
            except Exception as e: print("[run err]",n,type(e).__name__,e)
    print("\n[done]")

if __name__=="__main__": main()
