#!/usr/bin/env python3
"""경찰병원: deptCd 클릭 핸들러/AJAX 주소 추적 + JS강제클릭으로 schedule-view 캡처. python -u."""
from __future__ import annotations
import re
from playwright.sync_api import sync_playwright
UA=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

def main():
    with sync_playwright() as p:
        b=p.chromium.launch(); ctx=b.new_context(user_agent=UA,locale="ko-KR")
        ctx.set_default_timeout(15000)
        store={}   # url -> body (html/js)
        net=[]     # 모든 응답 기록
        pg=ctx.new_page()
        def on(r):
            try:
                ct=r.headers.get("content-type","")
                net.append((r.request.method,r.status,r.url,ct.split(";")[0]))
                if "html" in ct or "javascript" in ct or "json" in ct:
                    store[r.url]=r.text()
            except: pass
        pg.on("response",on)
        try: pg.goto("https://www.nph.go.kr/nph/med/schedule/ScheduleList.do?menuNo=200022",wait_until="commit",timeout=20000)
        except Exception as e: print("[goto]",type(e).__name__)
        pg.wait_for_timeout(4000)

        # 1) 메인 HTML 인라인 스크립트에서 deptCd/schedule 핸들러 추적
        mainhtml=""
        for u,bd in store.items():
            if "ScheduleList.do" in u: mainhtml=bd
        print("main html len",len(mainhtml))
        for kw in ["deptCd","schedule","Schedule","ajax","getList","selectList",".do"]:
            for m in re.finditer(kw,mainhtml):
                seg=mainhtml[max(0,m.start()-80):m.start()+120]
                if "function" in seg or "ajax" in seg.lower() or "url" in seg.lower() or ".do" in seg:
                    print("  [html:%s]"%kw," ".join(seg.split())[:200]); break

        # 2) JS 파일들에서 deptCd 관련 ajax url
        print("\n-- JS 파일에서 deptCd/schedule 핸들러 --")
        for u,bd in store.items():
            if "javascript" not in "" and not u.endswith(".js"): pass
            if u.endswith(".js") and ("deptCd" in bd or "schedule" in bd.lower()):
                print(" JS:",u[:90])
                for kw in ["deptCd","\\.ajax","url:","\\.do","schedule"]:
                    for m in re.finditer(kw,bd):
                        seg=bd[max(0,m.start()-60):m.start()+140]
                        print("    [%s]"%kw," ".join(seg.split())[:220]); break

        # 3) JS 강제 클릭(액션 대기 우회) 후 AJAX 가로채기
        print("\n-- JS강제클릭(정형 02700) 후 --")
        net.clear()
        try:
            pg.eval_on_selector("a.deptCd[rel='02700']","e=>e.click()")
        except Exception as e:
            print("  click eval:",type(e).__name__,e)
        pg.wait_for_timeout(4000)
        for m,st,u,ct in net:
            if ".css" not in u and "google" not in u and ".png" not in u and ".jpg" not in u and ".gif" not in u:
                print("  [%s %s] %s (%s)"%(m,st,u[:110],ct))
        sv=pg.evaluate(r"""()=>{const e=document.querySelector('.schedule-view');return e?(e.innerHTML||'').replace(/\s+/g,' ').slice(0,1200):'(none)';}""")
        print("  schedule-view:",sv[:900])
        b.close()
    print("\n[done]")

if __name__=="__main__": main()
