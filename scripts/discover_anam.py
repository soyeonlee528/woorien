#!/usr/bin/env python3
"""고대안암 주간 시간표 본문 확인: getDoctorList / getDoctorTime / getDoctorSchedule."""
from __future__ import annotations
import json
from playwright.sync_api import sync_playwright

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
BASE = "https://anam.kumc.or.kr"
EMR = "111240"  # 정형외과


def pretty(b):
    try:
        return json.dumps(json.loads(b), ensure_ascii=False)
    except Exception:
        return b


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(user_agent=UA, locale="ko-KR")
        req = ctx.request

        # 정형외과 의료진 empId 목록
        docs = req.get(f"{BASE}/api/doctorApi.do?startIndex=1&pageRow=100&drName="
                       f"&langType=kr&instNo=1&deptClsf=A&deptCd=AAOS&chosung=").json()["doctorList"]
        people = [(d["drName"], d["empId"], d["drNo"]) for d in docs]
        print("정형외과:", people)

        # getDoctorList.do: 과 전체 (주간 시간표 포함 여부 확인)
        gl = req.get(f"{BASE}/api/getDoctorList.do?hpCd=AA&mcdpCd={EMR}&instNo=1").text()
        try:
            arr = json.loads(gl)
            print(f"\n### getDoctorList.do 항목수={len(arr)}; 첫 항목 키: {list(arr[0].keys())}")
            print("첫 항목 전체:\n", pretty(json.dumps(arr[0]))[:3000])
        except Exception as e:
            print("getDoctorList parse err", e, gl[:300])

        # 각 의사별 getDoctorTime / getDoctorSchedule 본문
        for nm, emp, drno in people[:4]:
            t = req.get(f"{BASE}/api/getDoctorTime.do?hpCd=AA&mcdpCd={EMR}&mccnCd=&empId={emp}&selDt=202606").text()
            s = req.get(f"{BASE}/api/getDoctorSchedule.do?hpCd=AA&empId={emp}"
                        f"&inqrStrtYmd=20260601&inqrFnshYmd=20260831&mcdpCd={EMR}").text()
            print(f"\n===== {nm}({emp}) =====")
            print(f"  getDoctorTime.do len={len(t)}: {pretty(t)[:1200]}")
            print(f"  getDoctorSchedule.do len={len(s)}: {pretty(s)[:1200]}")

        browser.close()
    print("\n[done]")


if __name__ == "__main__":
    main()
