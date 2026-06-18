#!/usr/bin/env python3
"""강동성심: openDocPop(doctid) 가 호출하는 시간표 AJAX 엔드포인트 파악. python -u."""
from __future__ import annotations
from playwright.sync_api import sync_playwright
UA=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

def main():
    with sync_playwright() as p:
        b=p.chromium.launch(); ctx=b.new_context(user_agent=UA,locale="ko-KR")
        ctx.set_default_timeout(15000)
        cap=[]
        pg=ctx.new_page()
        pg.on("response", lambda r: cap.append((r.request.method,r.status,r.url,r.request.post_data or "")))
        url="https://www.kdh.or.kr/sub201.php?dept=111240"
        print("[load]",url)
        try: pg.goto(url,wait_until="networkidle",timeout=40000)
        except Exception as e: print("[goto]",type(e).__name__)
        pg.wait_for_timeout(1000); print("[loaded]",pg.title())

        # openDocPop 함수 소스
        src=pg.evaluate("() => { try { return openDocPop.toString().slice(0,800); } catch(e){ return 'NO_FN:'+e.message; } }")
        print("\n-- openDocPop 소스 --\n",src)

        # 의사 doctid 목록(예약 버튼 onclick)
        docts=pg.evaluate(r"""() => {
          const out=[]; document.querySelectorAll('[onclick]').forEach(e=>{
            const oc=e.getAttribute('onclick')||'';
            const m=oc.match(/openDocPop\('?(\d+)'?\)/);
            if(m) out.push(m[1]);
          }); return Array.from(new Set(out)).slice(0,5);
        }""")
        print("\n-- doctid 샘플 --", docts)

        # 첫 doctid 로 팝업 트리거 후 네트워크 확인
        cap.clear()
        if docts:
            did=docts[0]
            print("\n-- openDocPop(%s) 호출 --"%did)
            try: pg.evaluate("(d)=>openDocPop(d)", did)
            except Exception as e: print("  호출 오류:",e)
            pg.wait_for_timeout(3000)
            for m,st,u,pd in cap:
                if any(k in u.lower() for k in ("ajax","doc","sub2","schedule","time","php")) and "css" not in u and ".js" not in u:
                    print("  [%s %s] %s  post=%s"%(m,st,u[:120],(pd or '')[:80]))
            # 팝업 표 내용 확인
            txt=pg.evaluate(r"""() => {
              const t=document.querySelector('table.doc_pop');
              return t ? (t.innerText||'').replace(/\s+/g,' ').slice(0,300) : '(no doc_pop table)';
            }""")
            print("\n-- doc_pop 표 텍스트 --\n ",txt)
        b.close()
    print("\n[done]")

if __name__=="__main__": main()
