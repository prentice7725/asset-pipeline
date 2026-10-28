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
- provider 기록에서 베이스 이미지 해시와 `image_edit` 도구 사용을 확인한다(`reference_input: COPIED_TO_PROVIDER_INPUT`).
  이것은 이미지를 provider 입력으로 보냈다는 뜻이다. **모델이 인물을 유지했다는 뜻은 아니다.**
  `identity_review: HUMAN_REQUIRED`, `review_state: REVIEW_REQUIRED`, `game_ready: false`로 남는다.

## Provider 상태 (2026-10-28)

| Provider | 상태 |
| --- | --- |
| `grok_imagine` (Grok CLI) | 참조 편집 경로가 등록돼 있다. EXPERIMENTAL이며 실생성 근거는 아직 없다 |
| `codex_imagegen` (Codex CLI) | `character_reference`가 없어 계획 단계에서 차단된다. 참조 지원은 다음 단계 |
| AGY 나노바나나 | 미등록. [P0 조사](../m1/ANTIGRAVITY_P0_INSPECTION_20261014.md)의 재시도 상한·출력 대응 문제를 먼저 해결해야 한다 |
| ComfyUI 워크플로 | 현재 등록된 것은 참조 편집 기능이 없어 차단된다 |

## 알려진 제한

- **CLI provider로 만든 실행을 부모로 쓸 때:** 실행 기록에 provider가 처음 저장한 위치(`source_path`, 예: `~/.codex`, `~/.grok`)가 남는다.
  그 위치를 `--allowed-root`로 명시해야 한다. 변형 결과를 모션 작업 부모로 쓸 때도 같다. 기존 보안 검증을 유지한 결과다.
- **Visual SOT가 화풍·모델을 잠근 프로젝트:** 편집 provider와 충돌해 라우팅이 BLOCKED된다. SOT 잠금은 우회하지 않는다. 허용하려면 SOT 쪽 결정이 필요하다.
- **정확한 해상도·투명 배경:** 이를 요구하는 부모 Brief는 provider 기능이 없으면 계획 단계에서 차단된다.
- **외부 업로드:** 실행 시 베이스 이미지가 provider 서비스(xAI 등)로 전송된다.
- 테스트는 가짜 CLI만 사용한다. 실생성과 인물 유지 판정을 대신하지 않는다.
