#!/usr/bin/env python3
"""수집 실패 시 이메일 알림. 워크플로의 `if: failure()` 단계에서 호출된다.

필수 환경변수(= GitHub 저장소 시크릿):
  MAIL_SERVER   SMTP 서버 주소 (예: smtp.office365.com, smtp.gmail.com)
  MAIL_PORT     SMTP 포트 (587=STARTTLS 권장, 465=SSL)
  MAIL_USERNAME 보내는 계정 (로그인 아이디 = 보내는 주소)
  MAIL_PASSWORD 비밀번호(또는 앱 비밀번호)
선택:
  MAIL_TO       받는 주소 (기본: soyeon.lee@woorien.com)
  RUN_URL       실행 로그 링크 (워크플로에서 주입)

시크릿이 하나라도 없으면 조용히 건너뛴다(작업을 추가로 실패시키지 않음).
"""
import os
import ssl
import smtplib
import sys
from email.message import EmailMessage
from pathlib import Path

TO = os.environ.get("MAIL_TO") or "soyeon.lee@woorien.com"


def main():
    server = os.environ.get("MAIL_SERVER")
    port = os.environ.get("MAIL_PORT")
    user = os.environ.get("MAIL_USERNAME")
    pw = os.environ.get("MAIL_PASSWORD")
    if not (server and port and user and pw):
        print("[notify] 메일 시크릿(MAIL_*) 미설정 — 이메일 생략")
        return 0
    port = int(port)

    prob = Path(__file__).resolve().parent.parent / "scrape_problems.txt"
    detail = prob.read_text(encoding="utf-8") if prob.exists() else "(상세 내역 없음 — 실행 로그를 확인하세요)"
    run_url = os.environ.get("RUN_URL", "")

    msg = EmailMessage()
    msg["Subject"] = "[교수 시간표] 주간 자동 갱신 문제 발생"
    msg["From"] = user
    msg["To"] = TO
    msg.set_content(
        "교수 시간표 주간 자동 갱신 중 문제가 발생했습니다.\n\n"
        "■ 문제가 발생한 병원\n" + detail + "\n"
        "데이터는 기존 값이 그대로 유지되어 앱은 정상 동작합니다.\n"
        "사이트 구조가 바뀐 경우 어댑터 수정이 필요할 수 있습니다.\n\n"
        "■ 실행 로그\n" + run_url + "\n"
    )

    ctx = ssl.create_default_context()
    if port == 465:
        with smtplib.SMTP_SSL(server, port, context=ctx) as s:
            s.login(user, pw)
            s.send_message(msg)
    else:
        with smtplib.SMTP(server, port) as s:
            s.starttls(context=ctx)
            s.login(user, pw)
            s.send_message(msg)
    print("[notify] 이메일 발송 완료 →", TO)
    return 0


if __name__ == "__main__":
    sys.exit(main())
