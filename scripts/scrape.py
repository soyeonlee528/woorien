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
adapter(ctx, src) -> list[professor]; professor = {name, department, specialty, title, schedule}
schedule = {"mon":["AM","PM"], ...}  (월~일)
ctx 는 Playwright BrowserContext. JSON API 는 ctx.request, HTML 렌더링 페이지는
ctx.new_page() 로 처리한다.
"""
from __future__ import annotations

import json
import re
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
def adapter_anam_kumc(ctx, src):
    req = ctx.request
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
            spec = (d.get("special") or d.get("emrSpecial") or "").strip()
            if not spec:
                belong = (d.get("belong") or "").strip()
                parts = [b.strip() for b in belong.split(",") if b.strip()]
                if parts and parts[0] == dnm:
                    parts = parts[1:]
                spec = ", ".join(parts)
            profs.append({
                "name": (d.get("drName") or "").strip(),
                "department": dnm,
                "specialty": spec,
                "title": (d.get("hptlJobTitle") or "").strip(),
                "schedule": order_slots(sched),
            })
        print(f"  [anam] {dnm}: {len(docs)}명")
    return profs


# ---------------------------------------------------------------------------
# 어댑터: 가톨릭대학교 의정부성모병원 (CMC)
# ---------------------------------------------------------------------------
def adapter_cmc(ctx, src):
    req = ctx.request
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


# ---------------------------------------------------------------------------
# 어댑터: 을지대학교병원 계열 (노원을지 eulji.or.kr / 의정부을지 uemc.ac.kr)
# 두 사이트 구조 동일: /clinic/clinic_pg04.jsp?dept=<6자리코드>
# 표(table[0]) tbody 는 의료진마다 2개 <tr>(오전/오후). 요일 셀(td.d_info)에
# <img> 또는 텍스트(초진/재진)가 있으면 진료, 빈 칸이면 공석.
# ---------------------------------------------------------------------------
_EULJI_JS = r"""
() => {
  const tbl = document.querySelector('table');
  if (!tbl) return [];
  const trs = Array.from(tbl.querySelectorAll('tbody tr'));
  const has = (c) => !!(c.querySelector('img') || (c.textContent || '').trim().length);
  const out = [];
  let i = 0;
  while (i < trs.length) {
    const tr = trs[i];
    const nameCell = tr.querySelector('td.line_r');
    if (!nameCell) { i++; continue; }
    const name = (nameCell.textContent || '').trim();
    const specCell = tr.querySelector('td.td_al');
    const specialty = specCell
      ? (specCell.textContent || '').replace(/\s+/g, ' ').trim() : '';
    const am = Array.from(tr.querySelectorAll('td.d_info')).slice(0, 6).map(has);
    let pm = [false, false, false, false, false, false];
    const tr2 = trs[i + 1];
    if (tr2 && !tr2.querySelector('td.line_r')) {
      pm = Array.from(tr2.querySelectorAll('td.d_info')).slice(0, 6).map(has);
      i += 2;
    } else {
      i += 1;
    }
    if (name) out.push({ name, specialty, am, pm });
  }
  return out;
}
"""


def adapter_eulji(ctx, src):
    base = src["base"].rstrip("/")
    codes = src.get("deptCodes") or {}
    profs = []
    page = ctx.new_page()
    try:
        for dnm in src["departments"]:
            cd = codes.get(dnm)
            if not cd:
                print(f"  [eulji] 진료과 코드 없음: {dnm}")
                continue
            url = f"{base}/clinic/clinic_pg04.jsp?dept={cd}"
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=40000)
                page.wait_for_timeout(800)
                rows = page.evaluate(_EULJI_JS)
            except Exception as e:
                print(f"  [eulji] {dnm} 로드 실패: {type(e).__name__}: {e}")
                continue
            for r in rows:
                sched = empty_sched()
                for i in range(6):
                    if r["am"][i]:
                        sched[DAYS[i]].append("AM")
                    if r["pm"][i]:
                        sched[DAYS[i]].append("PM")
                profs.append({
                    "name": (r.get("name") or "").strip(),
                    "department": dnm,
                    "specialty": (r.get("specialty") or "").strip(),
                    "title": "",
                    "schedule": order_slots(sched),
                })
            print(f"  [eulji] {dnm}: {len(rows)}명")
    finally:
        page.close()
    return profs


# ---------------------------------------------------------------------------
# 어댑터: 강남새로운병원 (saerounhospital.com) — 척추/관절 전문병원
# 한 페이지에 모든 의사. div.name(센터+이름) 과 <table>(시간표) 가 문서 순서대로 1:1.
# 시간표: 행 오전/오후, 월~금 셀에 '수술' 또는 '진료' 텍스트면 진료(=공석 아님), 빈칸이면 공석.
# 토요일은 격주/휴진/날짜로 표기되어 정규 슬롯에서 제외.
# 진료과 라벨이 없어 센터명으로 정형/신경 추정, 마취·영상·내과 등은 제외.
# ---------------------------------------------------------------------------
_SAEROUN_JS = r"""
() => {
  const names = Array.from(document.querySelectorAll('div.name'))
    .map(e => (e.textContent || '').replace(/\s+/g, ' ').trim());
  const tables = Array.from(document.querySelectorAll('table'));
  const n = Math.min(names.length, tables.length);
  const out = [];
  for (let i = 0; i < n; i++) {
    const rows = Array.from(tables[i].querySelectorAll('tbody tr'));
    const am = [false, false, false, false, false];
    const pm = [false, false, false, false, false];
    rows.forEach(r => {
      const tds = Array.from(r.children);
      const label = (tds[0] ? tds[0].textContent : '') || '';
      const isAm = label.indexOf('오전') >= 0;
      const isPm = label.indexOf('오후') >= 0;
      if (!isAm && !isPm) return;
      for (let d = 0; d < 5; d++) {            // 월~금 (토는 rowspan 별도 셀)
        const cell = tds[1 + d];
        if (!cell) continue;
        const on = (cell.textContent || '').trim().length > 0;  // 수술/진료
        if (isAm) am[d] = am[d] || on; else pm[d] = pm[d] || on;
      }
    });
    out.push({ raw: names[i], am, pm });
  }
  return out;
}
"""

_EXCLUDE_KW = ("마취", "통증", "영상", "내과", "비만", "성인병", "가정의학", "재활", "한방", "치과")


def _saeroun_dept(text):
    """센터/직함 텍스트로 진료과 추정. 제외 대상이면 None."""
    if any(k in text for k in _EXCLUDE_KW):
        return None
    if "신경" in text or "척추" in text:
        return "신경외과"
    if any(k in text for k in ("정형", "관절", "스포츠", "하지", "상지", "족부", "수족", "외상")):
        return "정형외과"
    return None


def _split_name(raw):
    """'척추내시경센터 하주경원장' -> ('하주경', '척추내시경센터')."""
    m = re.search(r"([가-힣]{2,4})\s*(원장|교수|과장|부장|소장|센터장)", raw)
    if m:
        name = m.group(1)
        spec = raw[:m.start()].strip(" ·,-")
        return name, spec
    return raw.strip(), ""


def adapter_saeroun(ctx, src):
    base = src["base"].rstrip("/")
    url = src.get("listUrl") or (base + "/view/sub0103.php?menu1=open")
    profs = []
    page = ctx.new_page()
    rows = []
    try:
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=40000)
        except Exception:
            pass
        # ckattempt 안티봇 챌린지가 재로딩될 수 있으므로 실제 의사 카드(div.name) 가 뜰 때까지 대기
        try:
            page.wait_for_selector("div.name", timeout=25000)
        except Exception:
            page.wait_for_timeout(3000)
            try:
                page.wait_for_selector("div.name", timeout=15000)
            except Exception:
                print("  [saeroun] div.name 미발견 — 페이지 로딩 실패 가능")
        page.wait_for_timeout(500)
        rows = page.evaluate(_SAEROUN_JS)
    finally:
        page.close()
    for r in rows:
        name, spec = _split_name(r.get("raw", ""))
        dept = _saeroun_dept(r.get("raw", ""))
        if not dept or not name:
            continue
        sched = empty_sched()
        for i in range(5):
            if r["am"][i]:
                sched[DAYS[i]].append("AM")
            if r["pm"][i]:
                sched[DAYS[i]].append("PM")
        profs.append({
            "name": name,
            "department": dept,
            "specialty": spec,
            "title": "원장",
            "schedule": order_slots(sched),
        })
    print(f"  [saeroun] 정형·신경 {len(profs)}명")
    return profs


# ---------------------------------------------------------------------------
# 어댑터: 서울현대병원 (seoulhyundai.co.kr) — 척추/관절 전문병원
# 의사 카드 div.right = <article><h1>이름</h1><h3>직함 / 진료과</h3></article> + table.box-shadow
# 표: 오전/오후 행, 월~금 셀에 <span class="surgery|treat"> 있으면 진료(=공석 아님). 토는 순환(문의)→제외.
# h3 에 '정형외과'/'신경외과' 가 명시되어 그대로 분류. (목록+상세 중복 → 이름 기준 중복 제거)
# ---------------------------------------------------------------------------
_SEOULHYUNDAI_JS = r"""
() => {
  const cards = Array.from(document.querySelectorAll('div.right'))
    .filter(c => c.querySelector('table.box-shadow') && c.querySelector('h1'));
  return cards.map(c => {
    const name = (c.querySelector('h1').textContent || '').replace(/\s+/g, '');
    const h3 = (c.querySelector('h3') ? c.querySelector('h3').textContent : '')
      .replace(/\s+/g, ' ').trim();
    const rows = Array.from(c.querySelector('table.box-shadow').querySelectorAll('tbody tr'));
    const am = [false, false, false, false, false];
    const pm = [false, false, false, false, false];
    rows.forEach(r => {
      const tds = Array.from(r.children);
      const label = (tds[0] ? tds[0].textContent : '') || '';
      const isAm = label.indexOf('오전') >= 0;
      const isPm = label.indexOf('오후') >= 0;
      if (!isAm && !isPm) return;
      for (let d = 0; d < 5; d++) {           // 월~금
        const cell = tds[1 + d];
        const on = !!(cell && cell.querySelector('span'));
        if (isAm) am[d] = am[d] || on; else pm[d] = pm[d] || on;
      }
    });
    return { name, h3, am, pm };
  });
}
"""


def adapter_seoulhyundai(ctx, src):
    base = src["base"].rstrip("/")
    url = src.get("listUrl") or (base + "/page/sub0103.php")
    page = ctx.new_page()
    rows = []
    try:
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=40000)
        except Exception:
            pass
        try:
            page.wait_for_selector("div.right table.box-shadow", timeout=25000)
        except Exception:
            page.wait_for_timeout(2500)
        page.wait_for_timeout(400)
        rows = page.evaluate(_SEOULHYUNDAI_JS)
    finally:
        page.close()
    profs = []
    seen = set()
    for r in rows:
        name = (r.get("name") or "").strip()
        h3 = r.get("h3", "")
        if "신경외과" in h3:
            dept = "신경외과"
        elif "정형외과" in h3:
            dept = "정형외과"
        else:
            continue
        if not name or name in seen:
            continue
        seen.add(name)
        sched = empty_sched()
        for i in range(5):
            if r["am"][i]:
                sched[DAYS[i]].append("AM")
            if r["pm"][i]:
                sched[DAYS[i]].append("PM")
        profs.append({
            "name": name,
            "department": dept,
            "specialty": h3,
            "title": "",
            "schedule": order_slots(sched),
        })
    print(f"  [seoulhyundai] 정형·신경 {len(profs)}명")
    return profs


# ---------------------------------------------------------------------------
# 어댑터: 강동성심병원 (kdh.or.kr)
# sub201.php?dept=<코드> 에 의사 카드(.sub201_02_doc_name: 이름/진료과)와
# openDocPop('<doctid>') 버튼. openDocPop 은 /proc/doctor_info.php(POST id) 로 시간표를
# 받아 공용 표(.pop_monam ... .pop_satpm)를 채운다. ● 있으면 진료, 빈칸이면 공석.
# ---------------------------------------------------------------------------
_KDH_LIST_JS = r"""
() => {
  const names = Array.from(document.querySelectorAll('.sub201_02_doc_name')).map(d => ({
    name: ((d.querySelector('.doct_name_bold') || {}).textContent || '')
      .replace('교수', '').replace(/\s+/g, ' ').trim(),
    dept: ((d.querySelector('.sub201_dept') || {}).textContent || '').trim()
  }));
  const ids = [];
  document.querySelectorAll('[onclick]').forEach(e => {
    const m = (e.getAttribute('onclick') || '').match(/openDocPop\('?(\d+)'?\)/);
    if (m && ids.indexOf(m[1]) < 0) ids.push(m[1]);
  });
  const n = Math.min(names.length, ids.length);
  const out = [];
  for (let i = 0; i < n; i++) out.push({ name: names[i].name, dept: names[i].dept, id: ids[i] });
  return out;
}
"""

_KDH_POP_JS = r"""
() => {
  const g = (c) => {
    const el = document.querySelector('.' + c);
    return el ? ((el.textContent || '').trim().length > 0) : false;
  };
  return {
    am: ['pop_monam','pop_tueam','pop_wedam','pop_thuam','pop_friam','pop_satam'].map(g),
    pm: ['pop_monpm','pop_tuepm','pop_wedpm','pop_thupm','pop_fripm','pop_satpm'].map(g)
  };
}
"""


def adapter_kdh(ctx, src):
    base = src["base"].rstrip("/")
    codes = src.get("deptCodes") or {}
    profs = []
    page = ctx.new_page()
    try:
        for dnm, code in codes.items():
            try:
                page.goto(f"{base}/sub201.php?dept={code}", wait_until="networkidle", timeout=40000)
            except Exception:
                page.wait_for_timeout(1500)
            try:
                page.wait_for_selector(".sub201_02_doc_name", timeout=15000)
            except Exception:
                print(f"  [kdh] {dnm}: 의사 목록 없음")
                continue
            docs = page.evaluate(_KDH_LIST_JS)
            cnt = 0
            for d in docs:
                dept = (d.get("dept") or "").strip() or dnm
                if dept not in ("정형외과", "신경외과"):
                    continue
                try:
                    page.evaluate("(id) => openDocPop(id)", d["id"])
                    page.wait_for_timeout(900)
                    sc = page.evaluate(_KDH_POP_JS)
                except Exception:
                    continue
                sched = empty_sched()
                for i in range(6):
                    if sc["am"][i]:
                        sched[DAYS[i]].append("AM")
                    if sc["pm"][i]:
                        sched[DAYS[i]].append("PM")
                profs.append({
                    "name": (d.get("name") or "").strip(),
                    "department": dept,
                    "specialty": "",
                    "title": "교수",
                    "schedule": order_slots(sched),
                })
                cnt += 1
            print(f"  [kdh] {dnm}({code}): {cnt}명")
    finally:
        page.close()
    # 이름 기준 중복 제거(여러 진료과 코드에 동일인 노출 대비)
    uniq = {}
    for pr in profs:
        uniq.setdefault((pr["name"], pr["department"]), pr)
    return list(uniq.values())


# ---------------------------------------------------------------------------
# 어댑터: 경희대학교병원 (med.khmc.or.kr)
# timetable.do 가 anti-bot/JS 로딩이라 page.goto/content 가 막히지만, 메인 문서
# '응답 body' 는 캡처 가능(완전한 HTML). 의사별 <li class="profile_outer"> 안에
# 이름(.doctor_name) 과 진료일정 표(오전/오후 행, 요일 셀에 <em>=진료)가 들어있다.
# 진료과 코드: 정형외과 2050000000, 신경외과 2060000000. 표는 가끔 빈 응답 → 재시도.
# ---------------------------------------------------------------------------
def _khmc_fetch(ctx, url, tries=4):
    for _ in range(tries):
        bodies = {}
        page = ctx.new_page()

        def on(r):
            try:
                if "timetable.do" in r.url and "html" in r.headers.get("content-type", ""):
                    bodies[r.url] = r.text()
            except Exception:
                pass
        page.on("response", on)
        try:
            page.goto(url, wait_until="commit", timeout=25000)
        except Exception:
            pass
        page.wait_for_timeout(5000)
        page.close()
        for u, bd in bodies.items():
            if "timetable.do" in u and len(bd) > 5000:
                return bd
    return ""


def _khmc_parse(html):
    profs = []
    chunks = re.split(r'<li class="[^"]*profile_outer', html)
    for ch in chunks[1:]:
        m = re.search(r'doctor_name[^>]*>\s*<span>\s*([가-힣]{2,4})\s*</span>', ch)
        if not m:
            continue
        name = m.group(1)
        sched = empty_sched()
        for label, slot in (("오전", "AM"), ("오후", "PM")):
            rm = re.search(r'<td[^>]*>\s*' + label + r'\s*</td>(.*?)</tr>', ch, re.S)
            if not rm:
                continue
            cells = re.findall(r'<td[^>]*>(.*?)</td>', rm.group(1), re.S)
            for d, cell in enumerate(cells[:6]):
                if "<em" in cell and DAYS[d] not in (None,):
                    sched[DAYS[d]].append(slot)
        profs.append({"name": name, "schedule": order_slots(sched)})
    return profs


def adapter_khmc(ctx, src):
    base = src["base"].rstrip("/")
    codes = src.get("deptCodes") or {}
    out = []
    for dnm, code in codes.items():
        url = f"{base}/kr/treatment/department/{code}/timetable.do"
        html = _khmc_fetch(ctx, url)
        if not html:
            print(f"  [khmc] {dnm}({code}): 응답 캡처 실패")
            continue
        got = _khmc_parse(html)
        for g in got:
            out.append({
                "name": g["name"],
                "department": dnm,
                "specialty": "",
                "title": "교수",
                "schedule": g["schedule"],
            })
        print(f"  [khmc] {dnm}({code}): {len(got)}명")
    return out


# ---------------------------------------------------------------------------
# 어댑터: 혜성병원 (hsmcenter.com) — 남양주 척추/관절 전문병원
# 진료시간 페이지에 의사별 표 table.type-1, 표 바로 앞 <h4> = "<센터> <이름> <직함>".
# 표는 월~토 × 오전/오후, 셀에 ● 또는 'N주 진료' 텍스트면 진료, 빈칸이면 공석.
# 관절센터→정형외과, 척추센터→신경외과로 분류(추정). 그 외 진료과는 제외.
# ---------------------------------------------------------------------------
_HYESUNG_JS = r"""
() => {
  const out = [];
  document.querySelectorAll('table.type-1').forEach(t => {
    const prev = t.previousElementSibling;
    const head = prev ? (prev.textContent || '').replace(/\s+/g, ' ').trim() : '';
    const parse = (r) => Array.from(r.querySelectorAll('td')).slice(0, 6).map(td => {
      const tx = (td.textContent || '').trim();
      return tx.indexOf('●') >= 0 || tx.indexOf('진료') >= 0 || /\d주/.test(tx);
    });
    let am = [false,false,false,false,false,false];
    let pm = [false,false,false,false,false,false];
    t.querySelectorAll('tbody tr').forEach(r => {
      const lab = (r.querySelector('th') ? r.querySelector('th').textContent : '') || '';
      if (lab.indexOf('오전') >= 0) am = parse(r);
      else if (lab.indexOf('오후') >= 0) pm = parse(r);
    });
    if (head) out.push({ head, am, pm });
  });
  return out;
}
"""


def adapter_hyesung(ctx, src):
    url = src.get("listUrl") or src["base"]
    page = ctx.new_page()
    rows = []
    try:
        try:
            page.goto(url, wait_until="networkidle", timeout=45000)
        except Exception:
            page.wait_for_timeout(2000)
        try:
            page.wait_for_selector("table.type-1", timeout=15000)
        except Exception:
            pass
        rows = page.evaluate(_HYESUNG_JS)
    finally:
        page.close()
    profs = []
    seen = set()
    for r in rows:
        head = r.get("head", "")
        if "관절" in head:
            dept = "정형외과"
        elif "척추" in head:
            dept = "신경외과"
        else:
            continue  # 내과·신경과·영상·마취·건강검진·응급 등 제외
        m = re.search(r"([가-힣]{2,4})\s*(병원장|원장|과장|부장|소장|센터장|교수|전문의)", head)
        name = m.group(1) if m else ""
        if not name or (name, dept) in seen:
            continue
        seen.add((name, dept))
        sched = empty_sched()
        for i in range(6):
            if r["am"][i]:
                sched[DAYS[i]].append("AM")
            if r["pm"][i]:
                sched[DAYS[i]].append("PM")
        spec = head  # 센터명 등 원문 보존
        profs.append({
            "name": name,
            "department": dept,
            "specialty": spec,
            "title": "",
            "schedule": order_slots(sched),
        })
    print(f"  [hyesung] 정형·신경 {len(profs)}명")
    return profs


ADAPTERS = {
    "anam_kumc": adapter_anam_kumc,
    "cmc": adapter_cmc,
    "eulji": adapter_eulji,
    "saeroun": adapter_saeroun,
    "seoulhyundai": adapter_seoulhyundai,
    "kdh": adapter_kdh,
    "khmc": adapter_khmc,
    "hyesung": adapter_hyesung,
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

            adapter_name = src.get("adapter")
            if adapter_name == "manual":
                # 수동 입력 병원: 크롤링하지 않고 data/schedules.json 의 기존 값을 그대로 보존
                professors = prev.get("professors", [])
                source_tag = "manual"
                print(f"[manual] {hid}: 수동 데이터 {len(professors)}명 유지")
            else:
                adapter = ADAPTERS.get(adapter_name)
                if adapter is None:
                    print(f"[warn] {hid}: adapter '{adapter_name}' 없음 — 기존 유지")
                else:
                    ctx = browser.new_context(user_agent=UA, locale="ko-KR",
                                              extra_http_headers={"Referer": src["base"]})
                    try:
                        ctx.request.get(src["base"], timeout=30000)  # 쿠키 워밍업
                    except Exception:
                        pass
                    try:
                        got = adapter(ctx, src)
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
        "note": "정형외과·신경외과 외래 진료 시간표. 매주 목요일 자동 갱신.",
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
