#!/usr/bin/env python3
"""경찰병원 + 경희의료원 RAW HTML 파싱 설계용. ctx.request 로 원문 HTML 직접 수신. python -u."""
from __future__ import annotations
import re
from playwright.sync_api import sync_playwright
UA=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

def around(html, kw, n=240, maxhits=6):
    out=[]; i=0
    for _ in range(maxhits):
        j=html.find(kw,i)
        if j<0: break
        seg=html[max(0,j-n):j+n]
        out.append(" ".join(seg.split()))
        i=j+len(kw)
    return out

def main():
    with sync_playwright() as p:
        b=p.chromium.launch(); ctx=b.new_context(user_agent=UA,locale="ko-KR")
        req=ctx.request

        print("\n\n########## 경찰병원 ScheduleList RAW ##########")
        r=req.get("https://www.nph.go.kr/nph/med/schedule/ScheduleList.do?menuNo=200022",timeout=30000)
        h=r.text(); print("status",r.status,"len",len(h))
        # 진료과 탭이 가리키는 콘텐츠 영역 + 의사/요일 구조
        print("-- table 태그 개수:", h.count("<table"), " / 'schedule' id/class 부근 --")
        for s in around(h,"정형외과",260,8): print("   [정형]",s)
        print("   ...")
        for s in around(h,"신경외과",200,3): print("   [신경]",s)
        print("-- '오전' 부근(진료표 행) --")
        for s in around(h,"오전",200,4): print("   ",s)

        print("\n\n########## 경희의료원 list.do RAW ##########")
        r2=req.get("https://med.khmc.or.kr/kr/treatment/department/list.do",timeout=30000)
        h2=r2.text(); print("status",r2.status,"len",len(h2))
        print("-- 'timetable' 링크 패턴 --")
        for m in re.findall(r'href="[^"]*timetable[^"]*"', h2)[:10]: print("   ",m)
        print("-- 'department/<코드>' 패턴 --")
        for m in sorted(set(re.findall(r'/treatment/department/(\d{6,})', h2)))[:20]: print("   code",m)
        print("-- '정형외과' 부근 --")
        for s in around(h2,"정형외과",220,6): print("   ",s)
        print("-- '신경외과' 부근 --")
        for s in around(h2,"신경외과",220,4): print("   ",s)
        b.close()
    print("\n[done]")

if __name__=="__main__": main()
