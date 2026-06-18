#!/usr/bin/env python3
"""서울현대·강남새로운: 각 시간표 표와 의사 이름/진료과의 DOM 연결 구조 파악. python -u."""
from __future__ import annotations
from playwright.sync_api import sync_playwright
UA=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

def go(ctx,url,t=40000):
    pg=ctx.new_page(); print("  [load]",url)
    try: pg.goto(url,wait_until="networkidle",timeout=t)
    except Exception as e: print("  [goto]",type(e).__name__)
    pg.wait_for_timeout(1200); print("  [loaded] title:",pg.title()); return pg

# 각 표의 '컨테이너'(의사 카드) 단위 구조를 보기 위해, 시간표 표를 포함한 가장 가까운 조상(블록)의
# 텍스트와 클래스를 덤프한다.
JS=r"""(sel) => {
  const tables = Array.from(document.querySelectorAll(sel));
  const out = [];
  tables.slice(0,8).forEach((t,i)=>{
    // 시간표 표를 감싸는 카드: 위로 올라가며 의사이름으로 보이는 텍스트가 들어간 블록 탐색
    let card = t;
    for(let k=0;k<4 && card.parentElement;k++){ card = card.parentElement; }
    const prev = t.previousElementSibling;
    out.push(
      'TABLE#'+i+
      '\n  prevSibling: '+(prev?('<'+prev.tagName+' class='+prev.className+'> '+(prev.textContent||'').trim().replace(/\s+/g,' ').slice(0,120)):'(none)')+
      '\n  card<'+card.tagName+' class='+card.className+'> text: '+(card.textContent||'').trim().replace(/\s+/g,' ').slice(0,260)
    );
  });
  return out;
}"""

def main():
    with sync_playwright() as p:
        b=p.chromium.launch(); ctx=b.new_context(user_agent=UA,locale="ko-KR")
        ctx.set_default_timeout(15000)

        print("\n\n########## 서울현대 구조 ##########")
        pg=go(ctx,"https://www.seoulhyundai.co.kr/page/sub0103.php")
        for x in pg.evaluate(JS,"table.box-shadow"): print("  "+x)
        # 의사 이름 후보 요소(클래스에 doc/name/title 등) 덤프
        print("  -- 이름후보 --")
        for x in pg.eval_on_selector_all("[class*=doc],[class*=name],[class*=title],h3,h4,strong,.tit","els=>els.map(function(e){return '<'+e.tagName+' class='+e.className+'> '+(e.textContent||'').trim().replace(/\\s+/g,' ').slice(0,40);}).filter(function(s){return s.length>10;}).slice(0,40)"): print("    ",x)

        print("\n\n########## 강남새로운 구조 ##########")
        pg2=go(ctx,"https://saerounhospital.com/view/sub0103.php?menu1=open")
        for x in pg2.evaluate(JS,"table"): print("  "+x)
        print("  -- 이름후보 --")
        for x in pg2.eval_on_selector_all("[class*=doc],[class*=name],[class*=title],h3,h4,strong,.tit","els=>els.map(function(e){return '<'+e.tagName+' class='+e.className+'> '+(e.textContent||'').trim().replace(/\\s+/g,' ').slice(0,40);}).filter(function(s){return s.length>6;}).slice(0,50)"): print("    ",x)
        b.close()
    print("\n[done]")

if __name__=="__main__": main()
