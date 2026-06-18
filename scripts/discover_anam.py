#!/usr/bin/env python3
"""고대안암 전용 탐색: 정형외과/신경외과 deptCd 확인 + 교수 진료시간표 위치 파악."""
from __future__ import annotations
import json
from playwright.sync_api import sync_playwright

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
BASE = "https://anam.kumc.or.kr"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(user_agent=UA, locale="ko-KR")
        req = ctx.request

        # 1) 진료과 목록 → 정형외과/신경외과 deptCd
        dep = req.get(f"{BASE}/api/department.do?instNo=1&langType=kr&deptClsf=A").json()
        targets = {}
        for d in dep.get("deptList", []):
            if d.get("deptNm") in ("정형외과", "신경외과"):
                targets[d["deptNm"]] = d["deptCd"]
                print(f"[dept] {d['deptNm']} deptCd={d['deptCd']} emrDeptCd={d.get('emrDeptCd')}")
        print(f"targets={targets}")

        # 2) 각 과 의료진 목록 + 첫 의사 전체 JSON
        first_drno = None
        for nm, cd in targets.items():
            url = (f"{BASE}/api/doctorApi.do?startIndex=1&pageRow=100&drName="
                   f"&langType=kr&instNo=1&deptClsf=A&deptCd={cd}&chosung=")
            data = req.get(url).json()
            docs = data.get("doctorList", [])
            print(f"\n[{nm}] 의료진 {len(docs)}명")
            if docs:
                print(f"  키 목록: {list(docs[0].keys())}")
                print(f"  첫 의사 전체 JSON:\n{json.dumps(docs[0], ensure_ascii=False)[:2500]}")
                if first_drno is None:
                    first_drno = docs[0].get("drNo")

        # 3) 의사 상세 페이지 방문 → 시간표 API 캡처
        print(f"\n=== 의사 상세({first_drno}) 네트워크 캡처 ===")
        captured = []
        page = ctx.new_page()
        def on_resp(r):
            u = r.url
            if any(k in u.lower() for k in ("schedule","treat","hours","time","timetable","outp","drinfo","doctor")) and "displayfile" not in u.lower():
                ct = r.headers.get("content-type","")
                if "json" in ct or "text" in ct:
                    try: b = r.text()
                    except: b = ""
                    captured.append((r.status, u, b))
        page.on("response", on_resp)
        page.goto(f"{BASE}/kr/doctor-department/doctor/view.do?drNo={first_drno}", wait_until="networkidle", timeout=45000)
        page.wait_for_timeout(2500)
        for status, u, b in captured:
            kw = any(k in b for k in ("오전","오후","월","schedule","hours","진료"))
            print(f"  [{status}] {u} len={len(b)}{'  <<<KW' if kw else ''}")
            if kw:
                print(f"     body: {json.dumps(json.loads(b), ensure_ascii=False)[:1500] if b.strip().startswith(('{','[')) else b[:1500]}")
        browser.close()
    print("\n[done]")


if __name__ == "__main__":
    main()
