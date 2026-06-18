#!/usr/bin/env python3
"""혜성병원 진료시간/의료진 페이지 구조 파악(응답 캡처). python -u."""
from __future__ import annotations
import re
from playwright.sync_api import sync_playwright
UA=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

PAGES={
 "진료시간": "https://www.hsmcenter.com/?idx=c65053dbe88877/c65053f1188898",
 "의료진소개": "https://www.hsmcenter.com/?idx=c65053dbd88873/c65053e1388882",
}

def grab(ctx,url,tries=4):
    best=""
    for a in range(tries):
        bodies=[]
        pg=ctx.new_page()
        pg.on("response",lambda r:(bodies.append(r.text()) if "hsmcenter.com" in r.url and "html" in r.headers.get("content-type","") else None) if True else None)
        try: pg.goto(url,wait_until="commit",timeout=20000)
        except Exception as e: print("  [goto%d]"%a,type(e).__name__)
        pg.wait_for_timeout(4000)
        for bd in bodies:
            if len(bd)>len(best): best=bd
        pg.close()
        if len(best)>3000: break
    return best

def around(h,kw,n=300,m=6):
    out=[];i=0
    for _ in range(m):
        j=h.find(kw,i)
        if j<0: break
        out.append(" ".join(h[max(0,j-n):j+n].split())); i=j+len(kw)
    return out

def main():
    with sync_playwright() as p:
        b=p.chromium.launch(); ctx=b.new_context(user_agent=UA,locale="ko-KR")
        ctx.set_default_timeout(12000)
        for name,url in PAGES.items():
            print("\n\n########## %s ##########\n%s"%(name,url))
            h=grab(ctx,url)
            print("len",len(h),"table",h.count("<table"),"tr",h.count("<tr"))
            print("-- '오전' 부근 --")
            for s in around(h,"오전",260,4): print("   ",s)
            print("-- '정형외과' 부근 --")
            for s in around(h,"정형외과",220,4): print("   ",s)
            print("-- table[0..2] outerHTML --")
            for m in re.findall(r'<table[\s\S]{0,1500}?</table>',h)[:3]:
                print("   T:"," ".join(m.split())[:1300])
        b.close()
    print("\n[done]")

if __name__=="__main__": main()
