# 교수 진료 시간표 모아보기

고대안암병원·의정부성모병원의 **정형외과·신경외과 교수 외래 진료 시간표**를 한 화면에서 모아보고,
내 일정도 함께 관리하는 개인용 페이지입니다. 매주 자동 갱신됩니다.

- **보기 페이지**: `schedule.html`
- **데이터**: `data/schedules.json` (GitHub Actions가 매주 자동 갱신)
- **수집기**: `scripts/scrape.py` + `scripts/sources.json`
- **자동화**: `.github/workflows/update-schedules.yml` (매주 월요일 KST 00시 + 수동 실행)

## 동작 방식

1. 매주 GitHub Actions가 `scrape.py` 실행 (Playwright headless chromium)
2. 두 병원의 내부 JSON API 를 호출해 요일별 오전/오후 진료 여부 수집
   - **고대안암**: `department.do`(진료과 코드) → `doctorApi.do`(의료진) →
     `getDoctorSchedule.do`(향후 8주 날짜별 진료 → 요일 패턴으로 집계)
   - **의정부성모**: `/api/doctor?deptCd=`(정형외과 160 / 신경외과 103, `hoursAm`/`hoursPm` 배열)
3. `data/schedules.json` 갱신 → 변경분 자동 커밋 → 페이지 자동 반영
4. "내 일정" 탭에서 입력한 일정은 **각자 브라우저(localStorage)** 에만 저장

> 두 병원 모두 봇/비브라우저 요청을 차단하므로, 일반 HTTP 가 아니라
> Playwright(실제 브라우저 네트워크 스택)로 API 를 호출합니다.

## 참고

- 안암은 향후 8주 진료일정을 요일 패턴으로 집계한 값이라 휴진·임시변경이 있을 수 있고,
  의정부성모는 병원이 제공하는 요일별 표를 그대로 가져옵니다.
- 외래를 운영하지 않는 교수(수술·연구 전담)는 "휴진"으로 표시됩니다.

## 진료과·병원 추가

`scripts/sources.json` 의 `departments`(진료과명)나 `deptCodes` 를 수정하면 됩니다.
새 병원은 `sources.json` 에 항목을 추가하고 `scrape.py` 의 `ADAPTERS` 에
같은 이름의 adapter 함수를 등록하세요.
adapter(req, src) → `[{name, department, specialty, title, schedule}]`,
schedule = `{"mon":["AM","PM"], ...}` (월~일).
