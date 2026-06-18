#!/usr/bin/env python3
"""한양대서울/구리 + 혜성병원: 응답 본문 가로채기(재시도)로 실제 HTML 확보 가능한지 확인. python -u."""
from __future__ import annotations
import re
from playwright.sync_api import sync_playwright
UA=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

SITES={
 "한양서울": "https://seoul.hyumc.com/seoul/main.do",
 "한양구리": "https://guri.hyumc.com/guri/main.do",
 "혜성병원": "https://www.hsmcenter.com/",
}

def grab(ctx,url,match,tries=4):
    best=""
    for a in range(tries):
        bodies={}
        pg=ctx.new_page()
        def on(r):
            try:
                if match in r.url and "html" in r.headers.get("content-type",""):
                    bodies[r.url]=r.text()
            except: pass
        pg.on("response",on)
        try: pg.goto(url,wait_until="commit",timeout=20000)
        except Exception as e: print("   [goto%d]"%a,type(e).__name__)
        pg.wait_for_timeout(4000)
        for u,bd in bodies.items():
            if len(bd)>len(best): best=bd
        pg.close()
        if len(best)>3000 and ("정형외과" in best or "진료" in best): break
    return best

def main():
    with sync_playwright() as p:
        b=p.chromium.launch(); ctx=b.new_context(user_agent=UA,locale="ko-KR")
        ctx.set_default_timeout(12000)
        for name,url in SITES.items():
            match=url.split("//",1)[1].split("/",1)[0]  # host as match (catch any html from that host)
            host=match
            print("\n\n########## %s (%s) ##########"%(name,url))
            h=grab(ctx,url,host)
            isload = "Loading" in h[:200] or "잠시" in h or "robot" in h.lower()
            print("len",len(h),"| 정형외과:", "정형외과" in h, "| 진료:", "진료" in h, "| Loading셸:", isload)
            if len(h)>3000:
                # dept/의료진/timetable 힌트
                for kw in ["정형외과","신경외과","timetable","schedule","mediteam","의료진","진료시간"]:
                    i=h.find(kw)
                    if i>0:
                        print("  [%s] ..."%kw," ".join(h[max(0,i-60):i+90].split()))
                for m in sorted(set(re.findall(r'(?:href|action)="([^"]*(?:mediteam|timetable|schedule|doctor|depart)[^"]*)"',h)))[:10]:
                    print("   link",m[:120])
        b.close()
    print("\n[done]")

if __name__=="__main__": main()
