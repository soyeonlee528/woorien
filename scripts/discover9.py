#!/usr/bin/env python3
"""경찰병원 + 경희의료원: SPA/JS가 호출하는 데이터 엔드포인트 + 시간표 DOM 캡처. python -u."""
from __future__ import annotations
from playwright.sync_api import sync_playwright
UA=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
INT=("json","/api/","ajax","getlist","timetable","schedule","dept","doctor",".do",".json","list","proc")
KW=("오전","오후","진료","교수","정형","신경","월","화","수","목","금","휴진")

def cap_page(ctx,url,wait_ms=9000):
    cap=[]
    pg=ctx.new_page()
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
    print("[load]",url)
    try: pg.goto(url,wait_until="domcontentloaded",timeout=30000)
    except Exception as e: print("  [goto]",type(e).__name__)
    pg.wait_for_timeout(wait_ms)
    print("  title:",pg.title())
    print("  -- 네트워크 %d건 --"%len(cap))
    for m,st,ct,u,body in cap[:30]:
        kw=[k for k in KW if k in (body or "")]
        flag=" <<<KW "+",".join(kw[:6]) if kw else ""
        print("    [%s %s] %s %s len=%d%s"%(m,st,ct,u[:130],len(body),flag))
        if kw and "json" in ct:
            print("       body:"," ".join((body or "").split())[:500])
    return pg

def main():
    with sync_playwright() as p:
        b=p.chromium.launch(); ctx=b.new_context(user_agent=UA,locale="ko-KR")
        ctx.set_default_timeout(15000)

        print("\n\n########## 경찰병원 ScheduleList ##########")
        pg=cap_page(ctx,"https://www.nph.go.kr/nph/med/schedule/ScheduleList.do?menuNo=200022")
        # 시간표가 들어있을 컨테이너 후보: 정형/신경 텍스트 부근 블록
        blk=pg.evaluate(r"""() => {
          const out=[];
          document.querySelectorAll('div,ul,table,section').forEach(e=>{
            const t=(e.textContent||'').replace(/\s+/g,' ').trim();
            if(t.length>40 && t.length<400 && /(정형외과|신경외과)/.test(t) && /(오전|오후|진료)/.test(t))
              out.push('<'+e.tagName+' class='+e.className+'> '+t.slice(0,260));
          });
          return Array.from(new Set(out)).slice(0,8);
        }""")
        print("  -- 시간표 블록 후보 --")
        for x in blk: print("    ",x)
        print("  -- 진료과 탭/링크(onclick 포함) --")
        for x in pg.evaluate(r"""()=>Array.from(document.querySelectorAll('a,button,li')).map(e=>((e.textContent||'').trim().slice(0,12))+' | href='+(e.getAttribute('href')||'')+' | oc='+((e.getAttribute('onclick')||'').slice(0,60))).filter(s=>s.indexOf('정형')>=0||s.indexOf('신경외과')>=0).slice(0,12)"""): print("    ",x)

        print("\n\n########## 경희의료원 list.do ##########")
        pg2=cap_page(ctx,"https://med.khmc.or.kr/kr/treatment/department/list.do",wait_ms=12000)
        deps=pg2.evaluate(r"""()=>Array.from(document.querySelectorAll('a,li,button')).map(e=>{const t=(e.textContent||'').replace(/\s+/g,' ').trim();const h=e.getAttribute('href')||'';const oc=e.getAttribute('onclick')||'';return t.slice(0,14)+' | '+h+' | '+oc.slice(0,70);}).filter(s=>s.indexOf('정형외과')>=0||s.indexOf('신경외과')>=0).slice(0,16)""")
        print("  -- 경희 정형/신경 항목 --")
        for x in deps: print("    ",x)
        b.close()
    print("\n[done]")

if __name__=="__main__": main()
