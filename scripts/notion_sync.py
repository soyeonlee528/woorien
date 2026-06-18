#!/usr/bin/env python3
"""data/schedules.json → 노션 '교수 진료시간표' DB 동기화.

GitHub Actions(주간)에서 실행. 환경변수 NOTION_TOKEN 필요.
매 실행마다 기존 행을 보관(archive) 처리하고 최신 데이터로 다시 채운다.
"""
from __future__ import annotations
import json, os, sys, time
from pathlib import Path
from datetime import datetime, timezone, timedelta

import requests

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "schedules.json"

NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "").strip()
DB_ID = os.environ.get("NOTION_SCHEDULE_DB", "2d0715844efc41518680c3f6785625f9")
API = "https://api.notion.com/v1"
HEAD = {
    "Authorization": "Bearer " + NOTION_TOKEN,
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}
KST = timezone(timedelta(hours=9))
SDAYS = [("mon", "월"), ("tue", "화"), ("wed", "수"), ("thu", "목"), ("fri", "금")]


def daytext(slots):
    am = "AM" in (slots or [])
    pm = "PM" in (slots or [])
    if am and pm: return "오전·오후"
    if am: return "오전"
    if pm: return "오후"
    return ""


def rt(s):
    return [{"text": {"content": s}}] if s else []


def existing_page_ids():
    ids, cursor = [], None
    while True:
        body = {"page_size": 100}
        if cursor: body["start_cursor"] = cursor
        r = requests.post(f"{API}/databases/{DB_ID}/query", headers=HEAD, json=body, timeout=30)
        r.raise_for_status()
        j = r.json()
        ids += [p["id"] for p in j.get("results", [])]
        if not j.get("has_more"): break
        cursor = j.get("next_cursor")
    return ids


def archive(pid):
    requests.patch(f"{API}/pages/{pid}", headers=HEAD, json={"archived": True}, timeout=30).raise_for_status()


def create(hospital, p, today):
    props = {
        "교수": {"title": rt(p.get("name", ""))},
        "병원": {"select": {"name": hospital["name"]}},
        "진료과": {"select": {"name": p.get("department", "")}} if p.get("department") else {"select": None},
        "직위": {"rich_text": rt(p.get("title", ""))},
        "전문분야": {"rich_text": rt(p.get("specialty", ""))},
        "갱신일": {"date": {"start": today}},
    }
    for key, ko in SDAYS:
        props[ko] = {"rich_text": rt(daytext((p.get("schedule") or {}).get(key)))}
    r = requests.post(f"{API}/pages", headers=HEAD,
                      json={"parent": {"database_id": DB_ID}, "properties": props}, timeout=30)
    if r.status_code >= 300:
        print("[fail]", p.get("name"), r.status_code, r.text[:300])
    r.raise_for_status()


def main():
    if not NOTION_TOKEN:
        print("NOTION_TOKEN 없음 — 동기화 건너뜀"); return 0
    data = json.loads(DATA.read_text(encoding="utf-8"))
    today = datetime.now(KST).strftime("%Y-%m-%d")

    old = existing_page_ids()
    print(f"기존 {len(old)}행 보관 처리")
    for pid in old:
        archive(pid); time.sleep(0.2)

    n = 0
    for h in data.get("hospitals", []):
        for p in h.get("professors", []):
            if not p.get("name"): continue
            create(h, p, today); n += 1; time.sleep(0.2)
    print(f"[done] {n}명 노션 동기화 완료")
    return 0


if __name__ == "__main__":
    sys.exit(main())
