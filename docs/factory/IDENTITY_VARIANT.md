# 동일 인물 변형 작업 (표정·포즈)

ComfyUI 이미지 모델은 T2I만 지원해서 매번 새로 그리면 같은 인물이 유지되지 않는다.
그래서 정지 이미지를 두 단계로 나눈다. 먼저 T2I로 베이스를 만들고, 사람이 그중 한 장을 고른다.
그 한 장을 참조로 provider의 이미지 편집(i2i)을 실행해 **표정** 또는 **포즈**만 바꾼다.

```text
1. 기존 정지 경로: ComfyUI T2I → 후보 → 기술 QA → REVIEW_REQUIRED
2. 사람이 Identity Base 1장을 선택 (작업 파일에 실행 manifest·이미지 해시·선택자·이유 기록)
3. factory variant-plan: 부모·해시·provider 기능·라우팅 확인, 생성 0건
4. factory variant-run: 승인 파일 + 동의 플래그로 편집 1회 → QA → REVIEW_REQUIRED
5. (선택) 변형 결과를 모션 작업의 부모(IDENTITY_PRIMARY)로 사용
```

## 작업 파일

[예시](../../examples/factory_identity_variant_job.json)의 0 해시와 경로는 실제 값으로 바꿔야 한다.
상대 경로는 작업 파일 위치 기준이다.

| 필드 | 의미 |
| --- | --- |
| `asset_id` | 변형 결과의 새 asset ID. 부모와 같으면 거부한다 |
| `base.manifest_ref` / `manifest_sha256` | 베이스를 만든 NONPIXEL_IMAGE 실행의 `run_manifest.json` |
| `base.image` | 그 실행에 기록된 출력 이미지 1장과 SHA-256 |
| `base.selected_by` / `reason` | 누가 왜 이 베이스를 골랐는지. **인물 선택일 뿐 미술 승인이 아니다** |
| `variation.kind` | `EXPRESSION` 또는 `POSE` |
| `variation.target` | 바꿀 내용(예: `surprised, eyes wide`, `mid-stride running, side view`) |
| `provider.workflow_id` | 참조 편집이 등록된 워크플로를 명시. 자동 선택·전환은 없다 |

베이스 실행은 상태가 `CANDIDATE_READY_REVIEW_REQUIRED`이고 QA 실패가 없어야 한다.

## 바꿀 것과 유지할 것

유지 목록은 변형 종류별로 고정돼 있고, 작업 파일에서 줄일 수 없다. 이 목록은 편집 지시문에 들어간다.

| 종류 | 바꾸는 것 | 유지하는 것 |
| --- | --- | --- |
| `EXPRESSION` | 얼굴 표정 | 얼굴형·이목구비, 헤어, 의상, 액세서리, 장비·개수, 체형, 팔레트, 렌더링 화풍, **포즈, 구도·캔버스**, 배경 |
| `POSE` | 몸 포즈(PromptSpec `pose`에 반영) | 얼굴형·이목구비, 헤어, 의상, 액세서리, 장비·개수, 체형, 팔레트, 렌더링 화풍, 배경 |

부모 Brief의 정체성 특징(`identity`), 금지 요소, 제약 조건은 그대로 이어받는다.
베이스 모델용 화풍 바인딩과 우회 필드(`style_id`, `art_style`, override 계열)는 편집 provider와 맞지 않는다.
그래서 제거하고, 제거한 목록을 계획의 `removed_parent_fields`에 남긴다. 화풍은 참조 이미지와 유지 목록으로 전달한다.

## 실행

```powershell
assetpipe factory variant-plan --job workspace/jobs/fox_surprised.json --allowed-root . --allowed-root <provider 출력 폴더>
assetpipe factory variant-run --job workspace/jobs/fox_surprised.json --plan-sha256 <plan_sha256> `
  --authorization workspace/jobs/fox_surprised-auth.json --authorize-generation --allowed-root . --allowed-root <provider 출력 폴더>
```

승인 파일은 다음 필드만 가진다. `max_requests`는 1이어야 한다. `plan_sha256`, `workflow_id`, `workflow_sha256`은 계획 결과와 같아야 한다.

```json
{"schema_version": 1, "type": "IDENTITY_VARIANT_AUTHORIZATION", "authorization_id": "<32자리 hex>",
 "project_id": "game_a", "asset_id": "fox_surprised", "plan_sha256": "<계획>", "workflow_id": "grok_imagine",
 "workflow_sha256": "<계획의 workflow.hash>", "max_requests": 1, "authorized_by": "<이름>", "reason": "<이유>"}
```

- 예산은 Factory 실행기와 같은 `workspace/factory_budget/<authorization_id>`에 원자적으로 예약한다.
  실패해도 예약을 해제하지 않으므로 같은 승인 ID로는 다시 실행할 수 없다. 재시도·provider 전환도 없다.
- 결과는 예약 폴더의 `variant.json` 영수증, `job-input.json`, `run/run_manifest.json`이다.
- provider 기록에서 베이스 이미지 해시와 계획에 고정한 편집 도구 사용을 확인한다(Grok `image_edit`, Codex `image_gen`; `reference_input: COPIED_TO_PROVIDER_INPUT`).
  이것은 이미지를 provider 입력으로 보냈다는 뜻이다. **모델이 인물을 유지했다는 뜻은 아니다.**
  `identity_review: HUMAN_REQUIRED`, `review_state: REVIEW_REQUIRED`, `game_ready: false`로 남는다.

## Provider 상태

| Provider | 상태 |
| --- | --- |
| `grok_imagine` (Grok CLI) | EXPERIMENTAL·명시 선택 전용. 이세계 초상화 계약의 실제 편집·로컬 RGBA 전달과 사용자 인물 보존 수용 근거가 있다. 일반 Provider 승격·최종 미술 승인은 별도다 |
| `codex_imagegen` (Codex CLI) | 참조 복사본 1장을 `codex exec --image`로 첨부한다. 프로젝트 초상화의 실제 `image_gen` 참조 편집·로컬 RGBA 기술 검증 근거가 있다. EXPERIMENTAL·명시 선택 전용이며 인물 보존·최종 미술 승인은 결과별로 기록한다 |
| AGY 나노바나나 | 미등록. [P0 조사](../m1/ANTIGRAVITY_P0_INSPECTION_20261014.md)의 재시도 상한·출력 대응 문제를 먼저 해결해야 한다 |
| ComfyUI 워크플로 | 현재 등록된 것은 참조 편집 기능이 없어 차단된다 |

Codex는 실행 전 `exec --help`에 `--image`가 있는지 확인하며, 없으면 생성 전에
`REFERENCE_UNSUPPORTED`로 차단한다. `image_edit`라는 별도 Codex 도구를 가정하지 않는다.
참조 입력 지원과 실제 인물 유지는 별개다. 프로젝트 참조 편집의 실제 근거와,
일반 M1 `provider_e2e.py`의 T2I 검증·ACTIVE 승격은 구분한다.
CLI 입력 옵션은 [공식 문서](https://learn.chatgpt.com/docs/cli/reference)를 따른다.
새 편집 기능은 워크플로 해시와 변형 계획에 반영되므로 기존 계획·승인 파일을 재사용하지 않는다.

## 알려진 제한

- **CLI provider로 만든 실행을 부모로 쓸 때:** 실행 기록에 provider가 처음 저장한 위치(`source_path`, 예: `~/.codex`, `~/.grok`)가 남는다.
  그 위치를 `--allowed-root`로 명시해야 한다. 변형 결과를 모션 작업 부모로 쓸 때도 같다. 기존 보안 검증을 유지한 결과다.
- **Visual SOT가 화풍·모델을 잠근 프로젝트:** 명시적인 프로젝트 참조 편집 계약이 없으면 BLOCKED된다. SOT 잠금은 우회하지 않는다.
- **정확한 해상도·투명 배경:** 이를 요구하는 부모 Brief는 provider 기능이 없으면 계획 단계에서 차단된다.
- **외부 업로드:** 실행 시 베이스 이미지가 provider 서비스(xAI 등)로 전송된다.
- 단위 테스트는 가짜 CLI를 사용한다. 별도 Grok 실생성·사용자 수용 근거는 아래 검증 기록에 한정하며, 다른 Provider의 실제 편집·인물 유지 판정을 대신하지 않는다.

## 이세계 전생 심사국 초상화 참조 편집 계약 (2026-10-30)

사용자가 승인한 `character_portrait.reference_edit_contracts`는 명시적인
`REFERENCE_IMAGE` + 등록된 `grok_imagine` 또는 `codex_imagegen` +
`project_contract_required: true`에만 적용한다. 이전 단일
`reference_edit_contract` 형식도 지원하지만, 두 형식을 함께 선언하면 차단한다.
Krea2 T2I 바인딩과 STYLE-104 지문은 그대로 유지한다. 같은 스타일의 참조 편집
레시피는 `UNTESTED`이며, 새 화풍이나 미술 승인으로 취급하지 않는다.
각 계약의 workflow/model 쌍과 고정 RGBA·중립 배경·최종 크기·사람 검수 조건을
검증한다. 알 수 없는 편집기나 불일치 선언은 허용하지 않는다.

- 선택한 1212×1300 RGBA를 그대로 복사한다. 입력 크기·모드·복사 해시를 확인하고,
  원래 선택 해시 및 등록된 편집 도구(`image_edit`/`image_gen`)의 실제 참조 소비는 별도로 검증한다.
- 표정 변형의 부모 `pose`에 남은 무표정 지시는 새 표정 목표로 교체한다.
  몸 포즈·구도는 참조에 고정하고, T2I용 머리 여백 지시를 다시 적용하지 않는다.
- Grok의 네이티브 투명도·정확한 크기 지원은 여전히 false다. 기존 로컬 분할/매팅,
  경계 RGB 복원과 crop 없는 contain-fit이 최종 1212×1300 RGBA를 전달한다.
- 편집기가 흰색 대신 밝은 회색을 반환할 수 있다. 이 계약에 한해 확실한 배경
  표본의 중앙값을 측정하고, 밝기≥220·채널 차≤10·99% 이상이 채널별 ±10 이내인
  단색 중립 배경만 허용한다. 검증한 실제 배경색으로 합성식을 계산한다.
  일반 T2I의 기존 흰색 기준은 유지한다. 패턴·유색·어두운 배경은 통과시키지 않는다.
- 계획에 프로젝트 SOT 경로·파일 해시·편집 계약을 고정한다. 변경 시 기존 계획은
  예약 전에 차단되고, 실행의 컴파일 계약도 계획과 대조한다.

기존 여섯 MCP 도구와 공개 작업 스키마는 바꾸지 않았다. 현재 개발 CLI의
[실제 검증](PROJECT_REFERENCE_EDIT_VALIDATION_20261030.md)은 선택된 사람 베이스
한 건에 대한 실험적 근거다. 해당 Grok 결과는 사용자가 인물 보존을 수용했으며,
최종 미술·Aseprite/Golden 승인과 운영 활성화는 별도다.

후속 [Codex 프로젝트 참조 편집 검증](CODEX_PROJECT_REFERENCE_EDIT_VALIDATION_20261030.md)은
첨부 PNG의 실제 세션 내 해시와 도구가 소비한 복사본 경로, 실제 `image_gen` 1회,
최종 1212×1300 RGBA를 별도로 확인한다. 사용자는 이번 Codex 결과도 별도로 동일 인물
변형으로 수용했다. 해당 리뷰는 정확한 결과 해시에 연결되며 최종 미술 승인은 아니다.
새 계약으로 계획/SOT 해시가 바뀌므로 이전 승인 파일은 재사용하지 않는다.
