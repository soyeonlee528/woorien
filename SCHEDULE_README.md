# 교수 진료 시간표 모아보기

여러 대학병원의 교수 외래 진료 시간표를 한 화면에서 모아보고, 내 일정도 함께 관리하는 기능입니다.

- **보기 페이지**: `schedule.html` → 배포 주소 `https://soyeonlee528.github.io/woorien/schedule.html`
- **데이터**: `data/schedules.json` (GitHub Actions가 매주 자동 갱신)
- **수집기**: `scripts/scrape.py` + `scripts/sources.json`
- **자동화**: `.github/workflows/update-schedules.yml` (매주 월요일 KST 00시)

## 구성

```
schedule.html                  # 웹앱 (필터·검색·내 일정 입력)
data/schedules.json            # 표시용 데이터 (자동 생성/갱신)
scripts/sources.json           # 수집 대상 병원 목록
scripts/scrape.py              # 수집 스크립트 (병원별 adapter)
scripts/requirements.txt       # 파이썬 의존성
.github/workflows/update-schedules.yml  # 주간 cron 자동 갱신
```

## 동작 방식

1. 매주 GitHub Actions가 `scrape.py` 실행
2. `sources.json` 의 병원마다 해당 adapter 로 시간표 수집
3. `data/schedules.json` 갱신 후 변경분 자동 커밋
4. `schedule.html` 이 이 JSON 을 읽어 표로 보여줌
5. "내 일정" 탭에서 입력한 일정은 **각자 브라우저(localStorage)** 에만 저장

> 현재는 **샘플 데이터**로 채워져 있습니다(`adapter: "sample"`).
> 실제 병원을 연결하기 전까지 기존 데이터를 그대로 유지합니다.

## 실제 병원 추가하기

각 병원 사이트는 구조가 달라서 병원당 adapter 함수 하나를 작성해야 합니다.

1. **대상 페이지 확인** — 그 병원의 "외래 진료 시간표 / 의료진 진료일정" 페이지 URL.
   페이지가 JavaScript 로 그려지면(대부분의 대학병원) 브라우저 개발자도구 →
   Network 탭에서 실제 데이터를 주는 API(JSON) 주소를 찾는 게 가장 안정적입니다.

2. **`scripts/sources.json`** 에 항목 추가:
   ```json
   { "id": "snuh", "name": "서울대학교병원", "url": "<시간표 URL 또는 API>",
     "adapter": "snuh", "enabled": true }
   ```

3. **`scripts/scrape.py`** 의 `ADAPTERS` 에 함수 등록:
   ```python
   def adapter_snuh(source):
       data = fetch(source["url"])          # 또는 requests.get(...).json()
       professors = []
       # ... 파싱 ...
       professors.append({
           "name": "홍길동",
           "department": "소화기내과",
           "specialty": "내시경",
           "schedule": {"mon": ["AM"], "wed": ["AM", "PM"]},  # 비는 요일 생략 가능
       })
       return professors

   ADAPTERS["snuh"] = adapter_snuh
   ```
   - 한 곳 수집에 실패해도 다른 병원과 기존 데이터는 보존됩니다.
   - 시간대는 `"AM"`(오전)/`"PM"`(오후) 또는 `"오전"`/`"오후"` 모두 인식합니다.
   - 단순 `<table>` 구조라면 `adapter_generic_table` 을 복사해 selector 만 맞추세요.

4. **로컬 테스트**:
   ```bash
   pip install -r scripts/requirements.txt
   python scripts/scrape.py
   ```

## 참고 (수집 시 주의)

- 각 병원 사이트의 이용약관/robots.txt 를 확인하고, 요청 간격을 두어 과도한 부하를 주지 마세요.
- 공개된 외래 진료시간표 외의 개인정보는 수집하지 않습니다.
