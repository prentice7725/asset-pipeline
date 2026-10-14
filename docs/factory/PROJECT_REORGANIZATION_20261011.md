> Historical inventory with dated follow-ups (2026-10-11). Statements such as not implemented, runtime IDs and test counts describe those snapshots. For current source contracts use the [factory index](README.md), [execution boundary](FACTORY_EXECUTION.md), and [2026-10-14 uncommitted-work review](../maintenance/UNCOMMITTED_TRIAGE_20261014.md). This note grants no generation or activation approval.

# 프로젝트 재정비: 최신 main 통합과 M3 착수 기준

**기준일:** 2026-10-11 / Asia/Tokyo
**대상:** 개발자·운영 담당자
**범위:** 최신 main 통합, 현황·우선순위 정리. M3.0 구현·생성·배포는 미실행.

이 문서는 [Factory Architecture](FACTORY_ARCHITECTURE_V1.md)와
[M3 Workplan](M3_FACTORY_WORKPLAN.md)의 설계를 현재 로컬 상태에 대응시키는 참조 문서다.
설계 문서의 과거 baseline과 현재 코드·운영·실험 상태를 구분한다.

## 1. 통합 및 보존

- 원격과 로컬 main: `36812e3b524d013d1567372affa213e69aabd19e`.
- 통합 전 로컬 HEAD: `51854d66ef4300fce5e802b06032e7e6587eca50`.
- 원격 추가 계획은 문서 전용 PR #15이며 M3 기능을 활성화하지 않는다.
- 기존 로컬 파일 65개를 `workspace/reorganization/20261011/preserved-local.zip`과
  `preserve-local-before-m3-main-20261011` stash에 보존했다. stash는 삭제하지 않았다.
- 원격과 겹친 6개는 3-way 통합했다. 나머지 59개는 원래 바이트로 복원했다.
- CLI 충돌은 최신 `rescue-plan`·`style-review`와 로컬 `fusion`을 함께 유지했다.
- plugin 지침은 최신 24-style 생산 메뉴를 우선하고, 로컬 구형 자료 링크는
  별도 연구 참조로 유지했다. 기존 연구 파일 자체는 삭제하지 않았다.
- 원격이 갱신하는 경로에 기존 ignored 파일이 겹치는 사례는 0개였다.
- 새 commit/push, 작업 파일 이동·삭제, 새 배포 후보 생성은 하지 않았다.

Git HEAD와 운영 런타임은 별개다. 운영은 여전히
`security-release-20261010-572b76ffe1e4`다. 최신 checkout으로 운영을 덮어쓰지 않는다.

## 2. 실제 상태표

| 항목 | 코드·증거 상태 | 현재 완료 경계 |
| --- | --- | --- |
| Factory envelope / planner | 미구현 | M3.0 NOT_IMPLEMENTED; 설계 YAML을 기존 API에 보내면 안 됨 |
| A NONPIXEL IMAGE_ONLY | 기존 이미지 pipeline·provider·QA 존재 | 기존 이미지 후보 경로; factory terminal 계약은 미구현 |
| A 선택적 IMAGE_TO_SPRITE | 범용 child continuation·sprite backbone 미구현 | M3.2 이후 별도 검증 |
| B 참조 1/2/3장 | 범용 role/count ingest 및 실제 소비 증거 없음 | 각 count별 BLOCKED_BACKEND_NOT_VERIFIED |
| C SFX AUDIO_ONLY | 기존 Stable Audio·FLAC/WAV·기술 QA 및 과거 smoke | factory 메타데이터·청취 승인·현재 운영 smoke는 별도 |
| D PIXEL64 IMAGE_ONLY | 기존 연구 후보와 과거 기술 증거 | EXPERIMENTAL, 사람 승인 없음; 범용 64px 성공 주장 금지 |
| D 선택적 IMAGE_TO_SPRITE | 전체 frame pixel/temporal QA E2E 없음 | NOT_IMPLEMENTED |
| 32px | 역사·연구 파일 및 기존 pixel 알고리즘 보존 | ON_HOLD_RESEARCH; 새로운 생산 기본값으로 승격하지 않음 |
| 기존 pixel walk | 검증된 blue-tunic/white-background 전용 경로 | 기존 계약 유지; 다른 대상에 일반화하지 않음 |
| 로컬 fusion | 미커밋 실험 코드·fixture | 범용 factory backbone이나 운영 기능으로 간주하지 않음 |
| 로컬 rendezvous_transform | 프로젝트 한정 recipe·compiler·단일 예약·영상 리뷰 및 합성 회귀 | OFFLINE 계약, GENERATION_NOT_RUN, 운영 미배포 |
| 운영 보안 패치 | 봉인 release의 source·hash 및 MCP 검증 기록 | 기존 승인 범위의 운영 설치; 모델 E2E·게임 승인과 별개 |

`rendezvous_transform`은 정확히 SKY_RENDEZVOUS / STYLE-103의 순서 있는 3장
참조 실험이다. 범용 B3 입력 역할, 영상 실제 소비, 독립 start/end 강제,
기계적 rig, frame 추출·sprite export 완료를 증명하지 않는다. 범용
NONPIXEL_ANIMATION의 다른 action은 계속 차단된다.

## 3. 기존 작업 분류와 보관 원칙

| 작업 묶음 | 주요 경로 | 다음 처리 |
| --- | --- | --- |
| 보안 코드 정합성 | providers/grok_cli, tests/fakes/fake_grok 및 기존 보안 보고서 | 봉인 보안 diff를 최신 소스에 맞게 검토·통합하는 별도 안정화 작업 |
| 프로젝트 변신 영상 | motion/rendezvous, video_recipes, 해당 테스트·문서 | 범용 M3와 분리된 scoped experimental 변경 묶음으로 리뷰 |
| Fusion 실험 | motion/fusion, fusion graph, CLI, fixture·문서 | 그대로 보존; 공유 backbone에 재사용할 수 있는 계약만 이후 검토 |
| 32/48/64px 및 refiner 연구 | untracked workflow·research 문서·스크립트 | 역사/연구 유지; M3 D는 명시적 64px 계약으로만 연결 |
| 메뉴·agent 자료 | README, 구형 후보 메뉴, plugin 연구 참조 | 최신 24-style 생산 진입점과 역사 자료를 구분 |
| 실제 run·운영 증거 | workspace 아래 보안·영상·style 증거 | 소스 모듈 밖에서 원본·hash·실패 기록 유지 |

재정비를 위해 파일을 임의로 이동하거나 검증 알고리즘을 새 디렉터리로
복제하지 않는다. 묶음별 변경 목록과 원본 백업을 먼저 유지하고, 이후
구현은 작은 리뷰 가능한 PR로 나눈다. 이번 작업은 자동 commit/push를 하지 않는다.

## 4. 실행 순서와 완료 게이트

1. **착수 전 안정화:** 통합 checkout의 실패 목록을 해결하고, 현재 운영 보안
   수정과 소스 차이를 hunk 단위로 검토한다. dirty Grok를 봉인 파일 전체로
   덮어쓰지 않는다. 전체 pytest·보안 경로·6개 schema가 통과할 때만 다음 게이트로 간다.
2. **M3.0 / M3-01:** versioned factory 계약·planner·dry-run만 구현한다.
   A/D IMAGE_ONLY는 영상 작업·노드 검사·예약 0개, C는 오디오만,
   B는 1/2/3 역할·count를 명시한다. 기존 Brief와 전용 walk fixture는 유지한다.
3. **M3.1 + A IMAGE_ONLY:** 기존 SFX와 이미지 runner에 narrow adapter를 붙인다.
   기존 compiler를 재사용한다. 생성 smoke와 청취/시각 리뷰는 별도 예산으로 진행한다.
4. **M3.2:** 로컬 backend의 실제 입력 역할·count·모델/노드 지원을 읽기 전용으로
   확인한다. 기존 extractor/alignment/keyframes/temporal를 계약에 맞게 재사용하고,
   새 child run에 원본 영상·frame·atlas·QA를 보존한다. 부모 이미지는 불변이다.
5. **M3.3 / M3.4 / M3.5:** A continuation, B의 1/2/3 독립 E2E,
   D의 64px static 및 모든 frame pixel/temporal gate를 각자 검증한다.
   한 count나 한 대상의 성공을 다른 count·대상에 승계하지 않는다.
6. **M3.6:** mode별 실제 evidence ID, 기술 QA, 사람 승인, 운영 소유자를 기록한다.
   새 운영 활성화는 독립 승인과 검증을 거친다.

이 순서는 backlog이며 이번 요청에서 M3.0 코드 구현을 시작하지 않는다.
실패 게이트가 남아 있으면 계획 문서의 존재만으로 다음 단계를 PASS로 바꾸지 않는다.

## 5. 검증 기록

통합 후 확정 결과는 다음과 같다.

| 검증 | 결과 |
| --- | --- |
| 전체 pytest | 488 PASS, 9 FAIL, 0 SKIP, 0 ERROR / 총 497 |
| 보안 회귀 | 61 PASS |
| 새 변신 영상 회귀 | 26 PASS |
| portrait/project 회귀 | 13 PASS |
| MCP 6개 schema 및 경로 거부 | PASS |
| CLI help·문서 링크·diff check | PASS |
| 통합 대상 외 로컬 파일 | 59개 바이트 동일 |
| 기존 운영 source | 896개 파일 변경 0 |

실패 9개는 기존 Grok Windows 세션 경로 오류와 후속 error_code/output
assertion이며 모두 `test_cli_providers`에 한정된다. 새 테스트 삭제·skip·assertion
완화는 하지 않았다. 최신 checkout은 전체 회귀가 green인 상태가 아니다.
이 문제를 해소하는 보안 소스 정합성 작업이 M3.0의 첫 선행 조건이다.
현재 checkout에는 로컬 legacy benchmark fixture가 있어 SKIP 0이며, 과거
격리 보안 검증 복사본의 benchmark SKIP 1을 소급해 PASS로 변경하지 않는다.

확정 결과와 실패 목록은
`workspace/reorganization/20261011/pytest.xml`, `pytest.log`,
`summary.json`, `mcp_summary.json`, `merged_protocol/protocol_report.json`,
`integration.json`, `preservation.json`에 기록한다.
과거 472 PASS / 1 SKIP은 보안 소스 검증 복사본의 결과이며 현재 checkout 결과로 재사용하지 않는다.

CLI help에서 fusion·rescue-plan·style-review 공존을 확인했다.
소유한 오프라인 MCP 서버에서 정확히 6개 schema 및 경로 거부를 검증했고,
검증 연결은 EOF 종료를 관찰했다. 운영 MCP 프로세스는 변경하지 않았다.

## 6. 승인 경계

- 현재 요청은 **최신 통합 + 재정비 문서**다. M3 구현, 실제 이미지·영상·SFX
  생성, 모델 설치, 실제 운영 교체는 별도 범위다.
- 로컬 MiniMax가 유료 API를 쓰지 않더라도 실제 생성과 GPU 실행은 자동 승인되지 않는다.
- 승인·Golden·SOT·provider ACTIVE·game_ready를 문서나 합성 fixture로 만들지 않는다.
- retry·provider/model fallback·전역 이미지 scan을 복구하지 않는다.
- 6개 MCP schema는 유지하며, factory envelope 추가는 M3.0에서 독립 검토한다.
- 새 배포 후보 생성은 현재 요구하지 않는다. 운영 보안 release를 보존한다.

## 후속 안정화 완료 — 2026-10-11

Grok Windows 경로의 기존 9개 실패를 해결했다. 현재 전체 회귀는
502 PASS / 0 FAIL / 0 ERROR / 0 SKIP이며, MCP 6개 schema 및 경로 거부가
일치한다. 변경 범위와 한계는
[Grok Windows 안정화 기록](GROK_WINDOWS_STABILIZATION_20261011.md)을 참조한다.
운영 런타임과 다른 미커밋 작업은 보존했다. 다음 개발 우선순위는
M3.0 factory 계약·planner dry-run이며 아직 구현하지 않았다.

## M3.0 후속 구현 — 계약과 생성 없는 계획

개발자·운영 담당자를 위한 현재 코드 상태다. `assetpipe.factory`에 버전 1
validator와 read-only planner를 추가했다. 기존 Asset Brief schema, legacy
동작과 정확한 6개 MCP schema는 그대로다. 공장 실행기는 구현하지 않았다.

| 공장 라인 | 출력 모드 | source kind | 계획의 legacy 매핑 |
| --- | --- | --- | --- |
| A NONPIXEL | IMAGE_ONLY / IMAGE_TO_SPRITE | GENERATE / EXISTING_RUN | NONPIXEL_IMAGE / NONPIXEL_ANIMATION |
| B REFERENCE_MOTION | IMAGE_TO_SPRITE | EXTERNAL_IMAGES / EXISTING_RUN, 정확히 1..3장 | NONPIXEL_ANIMATION |
| C SFX | AUDIO_ONLY | GENERATE | SFX |
| D PIXEL64 | IMAGE_ONLY / IMAGE_TO_SPRITE | GENERATE / EXISTING_RUN | PIXEL_STATIC / PIXEL_ANIMATION, 논리 64x64 |

계약 정본은 [factory_request_v1.schema.json](../../schemas/factory_request_v1.schema.json),
공개 Python 진입점은 `assetpipe.api.factory_plan(request_path, root, allowed_roots=None)`이다.
JSON schema는 구조·조합을 검증하고 Python validator/planner는 역할 중복,
파일 내용, 프로젝트, hash 및 parent binding을 추가 검증한다.

### CLI 사용과 입력

다음 명령은 동일한 입력을 다시 검증하여 stdout에 계획을 출력한다.
`inspect`도 저장된 상태를 신뢰하거나 실행을 재개하지 않는다.

```powershell
assetpipe --root C:/workspace/asset-pipeline factory plan --request workspace/factory/request.json
assetpipe --root C:/workspace/asset-pipeline factory dry-run --request workspace/factory/request.json
assetpipe --root C:/workspace/asset-pipeline factory inspect --request workspace/factory/request.json
```

이 경로는 사용자가 준비한 요청의 위치 예시다. artifact를 source module에
쓰지 않는다. 기본 허용 root는 `--root`이며 추가 source root가 필요하면
`--allowed-root`를 반복하여 전체 허용 목록을 명시한다. 상대 입력 경로는
요청 파일 기준, 문서 내부 상대 참조는 해당 문서 기준으로 해석한다.
아래 예제와 Brief는 모두 미승인 계획 데이터다.

```json
{
  "factory_contract_version": 1,
  "factory_line": "NONPIXEL",
  "output_mode": "IMAGE_ONLY",
  "project_id": "example_game",
  "asset_id": "example_asset",
  "source": {"kind": "GENERATE", "brief_ref": "brief.json"},
  "image": {"style_source": "explicit_project_contract"},
  "motion": null,
  "audio": null
}
```

`brief.json`는 기존 validator를 통과하고 project_id·asset_id·output_class가
요청과 일치해야 한다. 원래 prompt·정본·workflow/model 선택을 보존한다.
D는 요청의 `image.logical_size`와 Brief의 resolution이 모두 `[64,64]`여야
한다. C는 요청과 Brief의 `audio.duration_seconds`가 일치해야 한다.

B 참조는 선언 순서대로 `path`, `sha256`, `role`을 기록하며 외부 입력에는
`ownership`·`license` 선언도 필요하다. 허용 역할은 IDENTITY_PRIMARY,
ALTERNATE_VIEW, POSE_ANCHOR, START_FRAME, END_FRAME, STYLE_REFERENCE다.
동일 역할·동일 물리 파일·동일 내용은 중복으로 차단한다. STYLE_REFERENCE만으로
대상을 추정하지 않는다. 파일 SHA는 실제 파일 내용의 소문자 SHA-256이다.
소유권·license 문자열은 사용자의 선언을 보관하며 법적 권한을 증명하지 않는다.

EXISTING_RUN에는 `manifest_ref`, `manifest_sha256`, `images`가 필요하다.
선택 이미지는 manifest의 recorded output이어야 한다. parent의 Asset Brief와
정본·모델 선택을 그대로 유지하며, 누락된 Brief나 다른 프로젝트는 차단한다.
새 asset_id가 parent asset_id와 달라도 parent 상태와 원본을 변경하지 않는다.
VIDEO→FRAMES→SPRITES는 source task에 의존하는 별도 자식 작업 계획이다.

### 현재 완료 게이트와 승인 경계

IMAGE_ONLY/AUDIO_ONLY 계획에는 영상 task가 없고, dependency probe·provider
allocation·예산 예약·dispatch가 모두 0이다. 경로는 configured roots에서
symlink/junction을 해석한 뒤 읽거나 hashing한다. 중첩 provenance와 명시된
transitive JSON report도 검증하며, 참조 해시 변경 시 차단한다.

유효한 계획은 `OFFLINE_CONTRACT_PASS`와
`NOT_IMPLEMENTED_FACTORY_DISPATCH`를 함께 반환한다. 실행 가능성이나
승인 상태를 뜻하지 않는다. 영상 계획은 `BLOCKED_BACKEND_NOT_VERIFIED`와
실제 참조 count/role 소비 검증을 후속 게이트로 유지한다. plan은 승인 파일을
생성하지 않고 `authorization`의 문서용 label을 실행 권한으로 해석하지 않는다.

남은 위험은 실제 1/2/3-input backend 지원 미검증, 읽기 전후 동시 파일 변경,
미평가 parent 승인·image QA·license·project SOT다. 기존 pipeline의 품질·review
게이트는 이후 실행 연결 시 그대로 필요하다. M3.1 SFX 운영 마감과 M3.2
shared motion은 후속 단계이며 실제 생성·모델 설치·운영 배포는 별도 승인 범위다.

검증 원본·백업·설치 로그·전체 pytest와 MCP 결과는
`workspace/reorganization/20261011/m30/`에 보관한다. 새 candidate는 만들지 않았다.

최종 전체 pytest: **557 PASS / 0 FAIL / 0 ERROR / 0 SKIP**.
이 중 M3.0 계약 55, 보안 P1/P2 61, Grok Windows 5, 변신 영상 26,
portrait 13개가 통과했다. MCP initialize/tools/list·정확한 6개 schema·경로 거부,
CLI help와 실제 plan/dry-run/inspect, 필수 editable 설치도 PASS다.
다른 기존 미커밋 파일 67개와 운영 런타임 파일 954개는 변경되지 않았다.
판정은 **M3.0 OFFLINE_CONTRACT_PASS / GENERATION_NOT_RUN**이며,
factory 실행·생산 준비·운영 활성화 완료로 해석하지 않는다.
