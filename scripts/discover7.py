#!/usr/bin/env python3
"""서울현대: box-shadow 시간표 표와 의사 이름/진료과 연결 구조 상세 파악. python -u."""
from __future__ import annotations
from playwright.sync_api import sync_playwright
UA=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

def main():
    with sync_playwright() as p:
        b=p.chromium.launch(); ctx=b.new_context(user_agent=UA,locale="ko-KR")
        ctx.set_default_timeout(15000)
        pg=ctx.new_page(); url="https://www.seoulhyundai.co.kr/page/sub0103.php"
        print("[load]",url)
        try: pg.goto(url,wait_until="networkidle",timeout=40000)
        except Exception as e: print("[goto]",type(e).__name__)
        pg.wait_for_timeout(1200); print("[loaded]",pg.title())

        # 각 시간표 표(box-shadow)를 감싸는 카드 컨테이너의 outerHTML 앞부분(이름/진료과 포함 추정)
        cards=pg.evaluate(r"""() => {
          const ts=Array.from(document.querySelectorAll('table.box-shadow'));
          return ts.slice(0,6).map((t,i)=>{
            // 의사 카드: 위로 올라가며 이름이 들어간 블록 찾기
            let c=t;
            for(let k=0;k<5 && c.parentElement;k++){
              c=c.parentElement;
              const txt=(c.textContent||'').replace(/\s+/g,' ').trim();
              if(/(원장|과장|교수|전문의)/.test(txt) && txt.length<400) break;
            }
            return 'CARD#'+i+' <'+c.tagName+' class='+c.className+'>\n   '+(c.outerHTML||'').replace(/\s+/g,' ').slice(0,700);
          });
        }""")
        for c in cards: print("\n"+c)

        # 이름 후보 요소 전부
        print("\n-- 이름 후보 --")
        for x in pg.eval_on_selector_all("h2,h3,h4,strong,b,.name,[class*=name],[class*=doc],[class*=tit],dt,th",
            "els=>els.map(function(e){return '<'+e.tagName+' class='+e.className+'> '+(e.textContent||'').replace(/\\s+/g,' ').trim().slice(0,40);}).filter(function(s){return /[가-힣]{2,4}(원장|과장|교수|전문의)/.test(s)||s.indexOf('정형')>=0||s.indexOf('신경')>=0;}).slice(0,50)"):
            print("   ",x)
        b.close()
    print("\n[done]")

if __name__=="__main__": main()
