> Historical stabilization record (2026-10-11). Its test counts and pending work describe the recorded checkout. The later [canonical Grok collection fix](../m1/GROK_SESSION_COLLECTION_20261012.md) supplements this path handling.

# Grok Windows 경로 안정화 — 2026-10-11

최신 main `36812e3b524d013d1567372affa213e69aabd19e`에 기존 미커밋 작업을
보존한 checkout의 9개 Grok 회귀 실패를 수정한다. 운영 런타임 교체와 새
candidate 구성은 수행하지 않는다.

## 원인과 수정

최초 실패는 세션 부모 디렉터리 생성이었다. 긴 작업 절대경로 전체를 URL
인코딩하여 Windows 경로 예산을 초과했고, 이후 오류 코드·호출 기록 검증도
함께 실패했다. 정상 인증·생성 fixture까지 같은 원인의 영향을 받았다.

기존 봉인 보안 release의 관련 수정만 현재 소스에 반영했다.

- 실제 디렉터리와 동일함을 확인한 Windows 8.3 경로를 cwd/home에 사용한다.
  해시나 문자열 자르기로 작업 디렉터리를 대체하지 않는다.
- API-key 모드는 작업마다 빈 `h` 홈을 사용한다. 로그인 설정·플러그인을 복사하지 않는다.
- 각 작업에 UUID를 한 번 배정하고 `--session-id`로 전달한다. 반환 세션이
  다르면 `OUTPUT_UNCORRELATED`로 차단한다.
- 경로 예산을 초과하거나 파일시스템 별칭의 동일성을 확인할 수 없으면
  dispatch 전에 차단한다. 폴백·재시도는 추가하지 않는다.
- 공통 수집기의 Windows namespace를 정규화하여 긴 경로, containment,
  snapshot 및 dedup 비교를 일치시킨다. symlink/junction 세션 alias 거부는 유지한다.
- fake CLI도 전달된 UUID를 반환하도록 수정했다. 합성 fixture가 실제 CLI를 호출하지 않는다.

추가 회귀는 긴 경로의 두 인증 모드, 각 모드의 동시 4개 작업 독립성,
다른 세션 거부, 경로 단축 불가능 시 사전 차단의 5개 사례다.
기존 P1/P2 공격·정상 세션 검증은 유지한다.

## 검증 기록

`workspace/reorganization/20261011/grok_fix/`에 원본 파일 백업,
`before.json`, 전체 `pytest.xml`·`pytest.log`, `verification.json`,
MCP protocol report 및 editable 설치 로그를 보관한다.

전체 회귀는 수정 전 488 PASS / 9 FAIL에서 수정 후 **502 PASS / 0 FAIL /
0 ERROR / 0 SKIP**으로 개선됐다. 기존 497개와 신규 5개를 모두 실행했다.
선택 회귀 119 PASS. MCP initialize/tools/list 및 정확한 6개 schema가
기존 봉인 기준과 일치하며 경로 거부도 PASS다. 소유한 검증 서버는 EOF로
정상 종료했다. CLI help와 source import 경로도 확인했다.

다른 기존 미커밋 파일 65개와 운영 런타임 파일 954개는 검증 전후
바이트 해시가 동일하다. 런타임 수에는 기존 캐시 파일도 포함한다.
필수 editable 설치는 sandbox DNS 제한으로 처음 실패했으며, 동일 명령의
권한 확장 실행에서는 성공했다.

## 남은 한계

합성 CLI는 실제 Grok의 8.3 cwd 해석 및 생성 결과를 증명하지 않는다.
8.3 이름을 제공하지 않거나 경로 예산을 만족하지 않는 볼륨은 안전하게
차단될 수 있다. 파일 검증과 읽기 사이의 동시 파일시스템 변경 위험은
여전히 존재한다. 실제 생성·과금, 운영 교체, Golden/SOT/provider ACTIVE
변경은 수행하지 않았다. M3.0 구현은 별도 다음 작업이다.
