#!/usr/bin/env python3
"""혜성병원: 각 시간표 표(table.type-1) 앞의 의사명/진료과 연결 구조. python -u."""
from __future__ import annotations
import re
from playwright.sync_api import sync_playwright
UA=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
URL="https://www.hsmcenter.com/?idx=c65053dbe88877/c65053f1188898"

def main():
    with sync_playwright() as p:
        b=p.chromium.launch(); ctx=b.new_context(user_agent=UA,locale="ko-KR")
        ctx.set_default_timeout(15000)
        pg=ctx.new_page()
        try: pg.goto(URL,wait_until="networkidle",timeout=45000)
        except Exception as e: print("[goto]",type(e).__name__)
        pg.wait_for_timeout(1500)
        # DOM에서 각 table.type-1 의 의사명/진료과를 카드/조상에서 추출
        data=pg.evaluate(r"""() => {
          const out=[];
          document.querySelectorAll('table.type-1').forEach((t,i)=>{
            // 조상으로 올라가며 의사명/진료과 후보 텍스트 수집
            let card=t;
            for(let k=0;k<4 && card.parentElement;k++) card=card.parentElement;
            // 표 앞 형제/조상 헤딩
            const prev=t.previousElementSibling;
            const heads=[];
            card.querySelectorAll('h2,h3,h4,h5,strong,.tit,[class*=name],[class*=doc],[class*=tit],dt,caption,th').forEach(e=>{
              const tx=(e.textContent||'').replace(/\s+/g,' ').trim();
              if(tx && tx.length<30 && /[가-힣]/.test(tx)) heads.push('<'+e.tagName+'.'+e.className+'>'+tx);
            });
            // 오전/오후 행 요약
            const rows=[];
            t.querySelectorAll('tbody tr').forEach(r=>{
              const lab=(r.querySelector('th')?(r.querySelector('th').textContent||''):'').replace(/\s+/g,' ').trim();
              const cells=Array.from(r.querySelectorAll('td')).map(td=>((td.textContent||'').trim()||'·'));
              rows.push(lab+': '+cells.join('|'));
            });
            out.push('TABLE#'+i+'\n  prev=<'+(prev?prev.tagName+'.'+prev.className+'>'+(prev.textContent||'').replace(/\s+/g,' ').trim().slice(0,60):'none>')+
                     '\n  heads='+heads.slice(0,6).join(' ')+
                     '\n  '+rows.join('  '));
          });
          return out.slice(0,22);
        }""")
        print("table.type-1 개수:", len(data))
        for d in data: print("\n"+d)
        b.close()
    print("\n[done]")

if __name__=="__main__": main()
