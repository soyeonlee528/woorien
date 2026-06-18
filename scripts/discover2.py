#!/usr/bin/env python3
"""신규 병원 4곳 구조 탐색: 네트워크 JSON + 표(table) 텍스트 + 관련 링크 덤프."""
from __future__ import annotations
from playwright.sync_api import sync_playwright

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

TARGETS = {
    "khmc_dept_list": "https://med.khmc.or.kr/kr/treatment/department/list.do",
    "khmc_timetable_sample": "https://med.khmc.or.kr/kr/treatment/department/2100000000/timetable.do",
    "nph_schedule": "https://www.nph.go.kr/nph/med/schedule/ScheduleList.do?menuNo=200022",
    "nph_dept_list": "https://www.nph.go.kr/nph/med/dept/list.do?menuNo=200140",
    "nowon_eulji_tt": "https://www.eulji.or.kr/clinic/clinic_pg04.jsp",
    "uijeongbu_eulji_tt": "https://www.uemc.ac.kr/clinic/clinic_pg04.jsp?dept=ABFDAA",
    "uijeongbu_eulji_deptlist": "https://www.uemc.ac.kr/clinic/clinic_pg01_01.jsp",
}
KW = ("오전","오후","진료","교수","정형","신경","월","화","수","목","금","휴진","timetable","schedule","dept")
INT = ("json","ajax","/api/","getlist","timetable","schedule","dept","doctor","list.do",".json")


def snip(s,n=600): return " ".join((s or "").split())[:n]


def run(p,name,url):
    print("\n\n########## "+name+"  "+url+" ##########")
    cap=[]
    b=p.chromium.launch(); ctx=b.new_context(user_agent=UA,locale="ko-KR"); pg=ctx.new_page()
    def on(r):
        try:
            u=r.url; ct=r.headers.get("content-type","")
            if ("json" in ct) or any(k in u.lower() for k in INT):
                body=""
                if "json" in ct or "text" in ct or "html" in ct:
                    try: body=r.text()
                    except: body=""
                cap.append((r.request.method,r.status,ct.split(";")[0],u,body))
        except: pass
    pg.on("response",on)
    try:
        pg.goto(url,wait_until="networkidle",timeout=45000); pg.wait_for_timeout(2500)
    except Exception as e:
        print("[goto err]",type(e).__name__,e)
    print("title:",pg.title())
    print("--- 네트워크 %d건 ---"%len(cap))
    for m,st,ct,u,body in cap[:25]:
        kw=[k for k in KW if k in (body or "")]
        print("  [%s %s] %s %s len=%d%s"%(m,st,ct,u,len(body)," <<<KW "+",".join(kw[:6]) if kw else ""))
        if kw and ("json" in ct):
            print("     body:",snip(body,700))
    try:
        tables=pg.eval_on_selector_all("table","els=>els.slice(0,5).map(function(t){return t.innerText.slice(0,500);})")
        print("--- 표 %d개 ---"%len(tables))
        for i,t in enumerate(tables): print("  [table %d] %s"%(i,snip(t,500)))
    except Exception as e: print("[table err]",e)
    try:
        links=pg.eval_on_selector_all("a[href]","els=>els.map(function(e){return e.getAttribute('href');}).filter(function(h){return h&&(h.indexOf('timetable')>=0||h.indexOf('dept')>=0||h.indexOf('schedule')>=0||h.indexOf('doctor')>=0);}).slice(0,30)")
        print("--- 관련 링크 ---")
        for h in sorted(set(links)): print("   ",h)
    except Exception as e: print("[link err]",e)
    b.close()


if __name__=="__main__":
    with sync_playwright() as p:
        for n,u in TARGETS.items():
            try: run(p,n,u)
            except Exception as e: print("[run err]",n,e)
    print("\n[done]")
