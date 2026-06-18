#!/usr/bin/env python3
"""혜성병원 진료시간 페이지: 렌더된 DOM(content) + 네트워크에서 시간표 구조 파악. python -u."""
from __future__ import annotations
import re
from playwright.sync_api import sync_playwright
UA=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
URL="https://www.hsmcenter.com/?idx=c65053dbe88877/c65053f1188898"  # 진료시간

def around(h,kw,n=320,m=6):
    out=[];i=0
    for _ in range(m):
        j=h.find(kw,i)
        if j<0: break
        out.append(" ".join(h[max(0,j-n):j+n].split())); i=j+len(kw)
    return out

def main():
    with sync_playwright() as p:
        b=p.chromium.launch(); ctx=b.new_context(user_agent=UA,locale="ko-KR")
        ctx.set_default_timeout(15000)
        cap=[]
        pg=ctx.new_page()
        def on(r):
            try:
                u=r.url; ct=r.headers.get("content-type","")
                if r.status<300 and (("json" in ct) or any(k in u.lower() for k in ("ajax","json","list","schedule","time","proc","doctor","idx"))) and "hsmcenter" in u:
                    body=""
                    try: body=r.text()
                    except: body=""
                    cap.append((r.request.method,r.status,ct.split(';')[0],u,body))
            except: pass
        pg.on("response",on)
        print("[load]",URL)
        try: pg.goto(URL,wait_until="networkidle",timeout=45000)
        except Exception as e: print("[goto]",type(e).__name__)
        pg.wait_for_timeout(2000)
        try: h=pg.content()
        except Exception as e: h=""; print("[content]",e)
        print("title:",pg.title(),"| content len",len(h),"| table",h.count("<table"),"tr",h.count("<tr"))
        print("\n-- 네트워크(데이터 후보) --")
        for m,st,ct,u,body in cap[:25]:
            kw=[k for k in ("오전","오후","진료","정형","신경","월","화") if k in (body or "")]
            print("  [%s %s] %s len=%d%s"%(m,st,u[:110],len(body)," KW "+",".join(kw) if kw else ""))
        print("\n-- '오전' 부근 --")
        for s in around(h,"오전",300,5): print("   ",s)
        print("\n-- '정형외과'/'신경외과' 부근 --")
        for s in around(h,"정형외과",240,3): print("   ",s)
        for s in around(h,"신경외과",240,2): print("   ",s)
        print("\n-- table[0..3] --")
        for m in re.findall(r'<table[\s\S]{0,1400}?</table>',h)[:4]:
            print("  T:"," ".join(m.split())[:1300])
        b.close()
    print("\n[done]")

if __name__=="__main__": main()
