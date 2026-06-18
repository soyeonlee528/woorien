#!/usr/bin/env python3
"""경찰병원: deptCd 클릭→schedule-view AJAX 캡처. 경희: timetable 의사명 구조. python -u."""
from __future__ import annotations
import re
from playwright.sync_api import sync_playwright
UA=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

def main():
    with sync_playwright() as p:
        b=p.chromium.launch(); ctx=b.new_context(user_agent=UA,locale="ko-KR")
        ctx.set_default_timeout(20000)

        print("\n\n########## 경찰병원: 정형외과(02700) 클릭 후 schedule-view ##########")
        cap=[]
        pg=ctx.new_page()
        pg.on("response",lambda r:cap.append((r.request.method,r.status,r.url,r.request.post_data or "")))
        try: pg.goto("https://www.nph.go.kr/nph/med/schedule/ScheduleList.do?menuNo=200022",wait_until="domcontentloaded",timeout=35000)
        except Exception as e: print("  [goto]",type(e).__name__)
        pg.wait_for_timeout(2500)
        cap.clear()
        try:
            pg.click("a.deptCd[rel='02700']",timeout=8000)
            pg.wait_for_timeout(4000)
        except Exception as e: print("  [click]",type(e).__name__,e)
        print("  -- 클릭 후 네트워크 --")
        for m,st,u,pd in cap:
            if any(k in u.lower() for k in ("schedule","dept","ajax",".do","json","list")) and ".css" not in u and ".js" not in u and "google" not in u:
                print("    [%s %s] %s post=%s"%(m,st,u[:120],(pd or '')[:90]))
        sv=pg.evaluate(r"""()=>{const e=document.querySelector('.schedule-view');return e?(e.innerHTML||'').replace(/\s+/g,' ').slice(0,1600):'(no .schedule-view)';}""")
        print("  -- schedule-view innerHTML --\n   ",sv)
        pg.close()

        print("\n\n########## 경희: timetable.do 의사명 구조 ##########")
        bodies={}
        pg2=ctx.new_page()
        pg2.on("response",lambda r:bodies.__setitem__(r.url,r.text()) if "timetable.do" in r.url and "html" in r.headers.get("content-type","") else None)
        try: pg2.goto("https://med.khmc.or.kr/kr/treatment/department/2050000000/timetable.do",wait_until="commit",timeout=20000)
        except Exception as e: print("  [goto]",type(e).__name__)
        pg2.wait_for_timeout(5000); pg2.close()
        h=""
        for u,bd in bodies.items():
            if "timetable.do" in u: h=bd; break
        print("  len",len(h))
        # '진료일정' 표 앞쪽 큰 슬라이스(의사명 헤딩 포함 추정)
        idx=h.find("진료일정")
        if idx>0:
            print("  -- '진료일정' 앞 900자 --\n   "," ".join(h[max(0,idx-900):idx+40].split()))
        # 교수/의사명 후보 태그
        for tag in ["doctor","docName","doc_name","prof","teacher","name"]:
            for m in re.findall(r'<[^>]*class="[^"]*'+tag+'[^"]*"[^>]*>[\s\S]{0,60}?<', h, re.I)[:4]:
                print("   [%s]"%tag," ".join(m.split())[:120])
        b.close()
    print("\n[done]")

if __name__=="__main__": main()
