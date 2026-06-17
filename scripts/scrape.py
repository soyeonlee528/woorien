#!/usr/bin/env python3
"""대학병원 교수 외래 시간표 수집 스크립트.

GitHub Actions(주간 cron)에서 실행되어 data/schedules.json 을 갱신합니다.

설계 원칙
---------
* 병원마다 사이트 구조가 다르므로, 병원 1곳당 adapter 함수 1개를 둡니다.
* sources.json 의 각 병원 항목은 어떤 adapter 를 쓸지 'adapter' 키로 지정합니다.
* 수집에 실패하거나 adapter 가 'sample' 이면, 기존 data/schedules.json 의
  해당 병원 데이터를 그대로 유지합니다(데이터 유실 방지).

새 병원 추가 방법
-----------------
1. scripts/sources.json 의 hospitals 배열에 항목 추가
   (id, name, url, adapter, enabled)
2. 아래 ADAPTERS 에 adapter 이름과 동일한 함수를 등록
   함수 시그니처: def my_adapter(source: dict) -> list[dict]
   반환: 교수 목록. 각 교수는 아래 형태의 dict
       {
         "name": "홍길동",
         "department": "소화기내과",
         "specialty": "내시경",          # 선택
         "schedule": {                    # 요일별 진료 시간대
            "mon": ["AM", "PM"], "tue": [], ...
         }
       }
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Callable

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:  # 로컬에서 의존성 없이 sample 만 돌릴 때
    requests = None
    BeautifulSoup = None

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "schedules.json"
SOURCES_FILE = ROOT / "scripts" / "sources.json"

KST = timezone(timedelta(hours=9))
DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
SLOTS = {"AM", "PM"}

USER_AGENT = (
    "Mozilla/5.0 (compatible; WoorienScheduleBot/1.0; "
    "+https://soyeonlee528.github.io/woorien/)"
)


# ---------------------------------------------------------------------------
# 유틸
# ---------------------------------------------------------------------------
def fetch(url: str, **kwargs) -> str:
    """HTML 텍스트를 가져온다. requests 미설치 시 명확히 실패시킨다."""
    if requests is None:
        raise RuntimeError("requests 가 설치되지 않았습니다. pip install -r scripts/requirements.txt")
    headers = {"User-Agent": USER_AGENT}
    headers.update(kwargs.pop("headers", {}))
    resp = requests.get(url, headers=headers, timeout=20, **kwargs)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or resp.encoding
    return resp.text


def normalize_schedule(raw: dict) -> dict:
    """요일/시간대 표기를 표준 형태로 정리한다."""
    out = {d: [] for d in DAYS}
    for day, slots in (raw or {}).items():
        key = day.strip().lower()[:3]
        if key not in out:
            continue
        clean = []
        for s in slots or []:
            s = str(s).strip().upper()
            if s in ("오전", "AM", "A"):
                s = "AM"
            elif s in ("오후", "PM", "P"):
                s = "PM"
            if s in SLOTS and s not in clean:
                clean.append(s)
        out[key] = clean
    return out


def clean_professors(rows: list[dict]) -> list[dict]:
    result = []
    for r in rows or []:
        name = (r.get("name") or "").strip()
        if not name:
            continue
        result.append(
            {
                "name": name,
                "department": (r.get("department") or "").strip(),
                "specialty": (r.get("specialty") or "").strip(),
                "schedule": normalize_schedule(r.get("schedule")),
            }
        )
    return result


# ---------------------------------------------------------------------------
# 어댑터들
# ---------------------------------------------------------------------------
def adapter_sample(source: dict) -> list[dict]:
    """실수집 어댑터가 준비되기 전까지 기존 데이터를 그대로 유지한다."""
    raise SkipUpdate("sample adapter: 기존 데이터 유지")


def adapter_generic_table(source: dict) -> list[dict]:
    """범용 표(table) 파서 예시.

    실제 병원 페이지의 진료 시간표가 단순 <table> 로 되어 있을 때 참고용.
    대부분의 대학병원은 JS 렌더링/검색폼 기반이라 그대로는 동작하지 않으며,
    병원별로 selector 와 컬럼 매핑을 맞춰서 복사해 쓰세요.

    source 예: {"url": "...", "selector": "table.schedule", ...}
    """
    html = fetch(source["url"])
    soup = BeautifulSoup(html, "html.parser")
    table = soup.select_one(source.get("selector", "table"))
    if table is None:
        raise SkipUpdate(f"{source['id']}: 표를 찾지 못함 (selector={source.get('selector')})")

    professors: list[dict] = []
    for tr in table.select("tbody tr"):
        cells = [td.get_text(strip=True) for td in tr.select("td")]
        if len(cells) < 3:
            continue
        # 컬럼 순서: 진료과, 교수명, 월, 화, 수, 목, 금, 토  (사이트에 맞게 조정)
        department, name, *day_cells = cells
        schedule = {}
        for day, cell in zip(DAYS, day_cells):
            slots = []
            if "오전" in cell or "AM" in cell.upper():
                slots.append("AM")
            if "오후" in cell or "PM" in cell.upper():
                slots.append("PM")
            schedule[day] = slots
        professors.append(
            {"name": name, "department": department, "schedule": schedule}
        )
    if not professors:
        raise SkipUpdate(f"{source['id']}: 표에서 교수 정보를 추출하지 못함")
    return professors


class SkipUpdate(Exception):
    """이번 실행에서 해당 병원 데이터를 갱신하지 말고 기존 값을 유지하라는 신호."""


# 어댑터 이름 -> 함수
ADAPTERS: dict[str, Callable[[dict], list[dict]]] = {
    "sample": adapter_sample,
    "generic_table": adapter_generic_table,
}


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------
def load_json(path: Path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def main() -> int:
    sources = load_json(SOURCES_FILE, {"hospitals": []})
    existing = load_json(DATA_FILE, {"hospitals": []})
    existing_by_id = {h["id"]: h for h in existing.get("hospitals", [])}

    out_hospitals = []
    changed = False

    for src in sources.get("hospitals", []):
        if not src.get("enabled", True):
            continue
        hid = src["id"]
        prev = existing_by_id.get(hid, {})
        adapter_name = src.get("adapter", "sample")
        adapter = ADAPTERS.get(adapter_name)

        professors = prev.get("professors", [])
        source_tag = prev.get("source", adapter_name)

        if adapter is None:
            print(f"[warn] {hid}: 알 수 없는 adapter '{adapter_name}' — 기존 데이터 유지")
        else:
            try:
                professors = clean_professors(adapter(src))
                source_tag = adapter_name
                if professors != prev.get("professors", []):
                    changed = True
                print(f"[ok]   {hid}: {len(professors)}명 수집")
            except SkipUpdate as e:
                print(f"[skip] {hid}: {e}")
            except Exception as e:  # 한 병원 실패가 전체를 막지 않도록
                print(f"[fail] {hid}: {e} — 기존 데이터 유지")

        out_hospitals.append(
            {
                "id": hid,
                "name": src.get("name", prev.get("name", hid)),
                "url": src.get("url", prev.get("url", "")),
                "source": source_tag,
                "professors": professors,
            }
        )

    result = {
        "updatedAt": datetime.now(KST).isoformat(timespec="seconds"),
        "note": existing.get("note", ""),
        "hospitals": out_hospitals,
    }

    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"[done] {DATA_FILE} 갱신 (변경={'있음' if changed else '없음'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
