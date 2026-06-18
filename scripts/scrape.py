#!/usr/bin/env python3
"""대학병원 교수 외래 진료 시간표 수집기 (Playwright 기반).

대상: 고대안암병원, 의정부성모병원 / 정형외과·신경외과
GitHub Actions(주간 cron)에서 실행되어 data/schedules.json 을 갱신한다.

설계
----
* 두 병원 모두 내부 JSON API 를 호출해 의료진과 요일별 오전/오후 진료 여부를 수집.
* 사이트가 봇/비브라우저 요청·일부 TLS 를 거르므로, Playwright(headless chromium)의
  request 컨텍스트로 호출한다(브라우저와 동일한 네트워크 스택).
* 한 병원 수집 실패 시 기존 data/schedules.json 값을 보존한다.

새 병원 추가: sources.json 에 항목 추가 + 아래 ADAPTERS 에 adapter 함수 등록.
adapter(req, src) -> list[professor]; professor = {name, department, specialty, title, schedule}
schedule = {"mon":["AM","PM"], ...}  (월~일)
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "schedules.json"
SOURCES_FILE = ROOT / "scripts" / "sources.json"

KST = timezone(timedelta(hours=9))
DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def empty_sched():
    return {d: [] for d in DAYS}


def order_slots(sched):
    for k in sched:
        sched[k] = [s for s in ("AM", "PM") if s in sched[k]]
    return sched


# ---------------------------------------------------------------------------
# 어댑터: 고려대학교 안암병원
# ---------------------------------------------------------------------------
def adapter_anam_kumc(req, src):
    base = src["base"].rstrip("/")
    hp = src.get("hpCd", "AA")
    inst = src.get("instNo", 1)

    dep = req.get(f"{base}/api/department.do?instNo={inst}&langType=kr&deptClsf=A").json()
    name2code = {d["deptNm"]: (d["deptCd"], d.get("emrDeptCd"))
                 for d in dep.get("deptList", [])}

    today = datetime.now(KST)
    start = today.strftime("%Y%m%d")
    end = (today + timedelta(weeks=8)).strftime("%Y%m%d")

    profs = []
    for dnm in src["departments"]:
        if dnm not in name2code:
            print(f"  [anam] 진료과 매칭 실패: {dnm}")
            continue
        dept_cd, emr_cd = name2code[dnm]
        url = (f"{base}/api/doctorApi.do?startIndex=1&pageRow=300&drName="
               f"&langType=kr&instNo={inst}&deptClsf=A&deptCd={dept_cd}&chosung=")
        docs = req.get(url).json().get("doctorList", [])
        for d in docs:
            emp = d.get("empId")
            sched = empty_sched()
            if emp and emr_cd:
                surl = (f"{base}/api/getDoctorSchedule.do?hpCd={hp}&empId={emp}"
                        f"&inqrStrtYmd={start}&inqrFnshYmd={end}&mcdpCd={emr_cd}")
                try:
                    rows = req.get(surl).json()
                except Exception:
                    rows = []
                for e in rows or []:
                    ymd = e.get("mdcrYmd")
                    if not ymd:
                        continue
                    try:
                        wd = datetime.strptime(ymd, "%Y%m%d").weekday()  # 0=월
                    except ValueError:
                        continue
                    key = DAYS[wd]
                    if e.get("amSttsDvsnCd") and "AM" not in sched[key]:
                        sched[key].append("AM")
                    if e.get("pmSttsDvsnCd") and "PM" not in sched[key]:
                        sched[key].append("PM")
            profs.append({
                "name": (d.get("drName") or "").strip(),
                "department": dnm,
                "specialty": (d.get("special") or d.get("emrSpecial") or "").strip(),
                "title": (d.get("hptlJobTitle") or "").strip(),
                "schedule": order_slots(sched),
            })
        print(f"  [anam] {dnm}: {len(docs)}명")
    return profs


# ---------------------------------------------------------------------------
# 어댑터: 가톨릭대학교 의정부성모병원 (CMC)
# ---------------------------------------------------------------------------
def adapter_cmc(req, src):
    base = src["base"].rstrip("/")
    profs = []
    for dnm in src["departments"]:
        cd = (src.get("deptCodes") or {}).get(dnm)
        if not cd:
            print(f"  [cmc] 진료과 코드 없음: {dnm}")
            continue
        arr = req.get(f"{base}/api/doctor?deptCd={cd}&orderType=dept&fsexamflag=A").json()
        for d in arr or []:
            tr = d.get("doctorTreatment") or {}
            sched = empty_sched()
            for i, slot in enumerate(tr.get("hoursAm") or []):
                if i < 6 and slot:
                    sched[DAYS[i]].append("AM")
            for i, slot in enumerate(tr.get("hoursPm") or []):
                if i < 6 and slot:
                    sched[DAYS[i]].append("PM")
            dept = (d.get("doctorDept") or {}).get("deptNm") or dnm
            profs.append({
                "name": (d.get("drName") or "").strip(),
                "department": dept,
                "specialty": (tr.get("special")
                              or (d.get("doctorDept") or {}).get("nuSpecial") or "").strip(),
                "title": (d.get("nuHptlJobTitle") or "").strip(),
                "schedule": order_slots(sched),
            })
        print(f"  [cmc] {dnm}: {len(arr or [])}명")
    return profs


ADAPTERS = {
    "anam_kumc": adapter_anam_kumc,
    "cmc": adapter_cmc,
}


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------
def load_json(path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def main():
    from playwright.sync_api import sync_playwright

    sources = load_json(SOURCES_FILE, {"hospitals": []})
    existing = load_json(DATA_FILE, {"hospitals": []})
    prev_by_id = {h["id"]: h for h in existing.get("hospitals", [])}

    UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

    out = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for src in sources.get("hospitals", []):
            if not src.get("enabled", True):
                continue
            hid = src["id"]
            prev = prev_by_id.get(hid, {})
            professors = prev.get("professors", [])
            source_tag = prev.get("source", "pending")

            adapter = ADAPTERS.get(src.get("adapter"))
            if adapter is None:
                print(f"[warn] {hid}: adapter '{src.get('adapter')}' 없음 — 기존 유지")
            else:
                ctx = browser.new_context(user_agent=UA, locale="ko-KR",
                                          extra_http_headers={"Referer": src["base"]})
                try:
                    ctx.request.get(src["base"], timeout=30000)  # 쿠키 워밍업
                except Exception:
                    pass
                try:
                    got = adapter(ctx.request, src)
                    got = [pr for pr in got if pr.get("name")]
                    if got:
                        professors = got
                        source_tag = "live"
                        print(f"[ok]   {hid}: 총 {len(got)}명 수집")
                    else:
                        print(f"[skip] {hid}: 0명 — 기존 데이터 유지")
                except Exception as e:
                    print(f"[fail] {hid}: {type(e).__name__}: {e} — 기존 데이터 유지")
                finally:
                    ctx.close()

            out.append({
                "id": hid,
                "name": src.get("name", prev.get("name", hid)),
                "url": src.get("url", prev.get("url", "")),
                "departments": src.get("departments", prev.get("departments", [])),
                "source": source_tag,
                "professors": professors,
            })
        browser.close()

    result = {
        "updatedAt": datetime.now(KST).isoformat(timespec="seconds"),
        "note": "고대안암·의정부성모 정형외과·신경외과 외래 진료 시간표. 매주 자동 갱신.",
        "hospitals": out,
    }
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")
    total = sum(len(h["professors"]) for h in out)
    print(f"[done] {DATA_FILE} 갱신 — 병원 {len(out)}곳, 교수 {total}명")
    return 0


if __name__ == "__main__":
    sys.exit(main())
