# Asset Pipeline 상세 사용 안내

[README](../README.md)의 짧은 안내에서 다루지 않는 명령, 옵션, 상태 값, 제한을 모았습니다.

## 목차

- [프로젝트별 저장](#프로젝트별-저장)
- [이미지와 효과음 생성](#이미지와-효과음-생성)
- [NONPIXEL 이미지 provider (ComfyUI · Codex CLI · Grok CLI)](#nonpixel-이미지-provider-comfyui--codex-cli--grok-cli)
- [크기·투명·용량 규격으로 내보내기](#크기투명용량-규격으로-내보내기)
- [Asset Brief와 공통 프롬프트](#asset-brief와-공통-프롬프트)
- [Workflow 선택](#workflow-선택)
- [넌픽셀 애니메이션 (명시적 모션 작업)](#넌픽셀-애니메이션-명시적-모션-작업)
- [동일 인물 변형 (표정·포즈)](#동일-인물-변형-표정포즈)
- [픽셀 검증과 Static Master 승인](#픽셀-검증과-static-master-승인)
- [픽셀 애니메이션 (기존 blue-tunic 프로필)](#픽셀-애니메이션-기존-blue-tunic-프로필)
- [64px 픽셀 애니메이션 (walk·idle·attack)](#64px-픽셀-애니메이션-walkidleattack)
- [STYLE MENU v1 — 운영용 비픽셀 화풍 선택](#style-menu-v1--운영용-비픽셀-화풍-선택)
- [프로젝트별 애셋 레퍼런스를 설계할 때](#프로젝트별-애셋-레퍼런스를-설계할-때)
- [검증 근거 기반 모델 지식 조회 (읽기 전용)](#검증-근거-기반-모델-지식-조회-읽기-전용)
- [실행 기록과 개발](#실행-기록과-개발)
- [부가 기능](#부가-기능)

## 프로젝트별 저장

Brief에 `project_id`를 지정하거나 CLI에서 `--project game-a`를 사용합니다. 생략하면 `default`를 사용하며 소스 경로로 프로젝트를 추측하지 않습니다.

```text
MCP: output_root/프로젝트ID/runs/애셋ID/실행ID/
CLI: workspace/프로젝트ID/runs/애셋ID/실행ID/
```

MCP 요청 기록은 `output_root/프로젝트ID/requests/`에 저장합니다. 이어서 만드는 애니메이션도 원래 프로젝트를 유지합니다. CLI의 명시적 `--output`은 지정 경로를 그대로 사용합니다.
프로젝트 ID는 영문·숫자로 시작하고 영문·숫자·하이픈·밑줄만 사용하며 최대 64자입니다.

## 이미지와 효과음 생성

일반 이미지 후보:

```powershell
assetpipe create --type nonpixel-image --project game-a --asset-id scout --workflow anima_base --preset smoke --seed 101 --prompt "fantasy scout, short brown hair, blue cloak, light armor, dagger"
```

효과음 후보:

```powershell
assetpipe create --type sfx --project game-a --asset-id sword_hit --duration 3 --prompt "A single metallic sword impact, sharp clang with a short ringing decay, dry close recording, no music, no speech."
```

SFX 길이는 1–30초이며 기본값은 5초입니다. 현재 `audio_stable_audio_3_medium`은 직접 텍스트 입력 경로로 연결하며 선택적 Qwen 확장 단계는 제외합니다. 원본 FLAC과 16-bit PCM WAV, 길이·무음·피크·RMS 등의 QA 기록을 보존합니다. 통과 후에도 청취 검토가 필요합니다. [SFX 사용 안내](SFX.md).

모든 생성 명령은 실행 manifest 경로를 출력합니다. 저장소 밖에서 실행할 때는 하위 명령 앞에 `assetpipe --root <저장소 경로>`를 지정하세요.

## NONPIXEL 이미지 provider (ComfyUI · Codex CLI · Grok CLI)

`NONPIXEL_IMAGE`는 세 가지 생성 provider를 같은 인터페이스로 지원합니다. 어느 쪽이든 같은 브리프·라우터 preflight, 같은 이미지 QA, 같은 `CANDIDATE_READY_REVIEW_REQUIRED` 검토 게이트를 통과해야 합니다. Pixel·SFX 경로는 바뀌지 않았습니다.

| provider | workflow ID | 사용 도구 | 상태 | 선택 방법 |
| --- | --- | --- | --- | --- |
| ComfyUI | `anima_base`, `krea2_base` 등 | JSON workflow | `ACTIVE` | 자동 라우팅 또는 ID 지정 |
| Codex CLI | `codex_imagegen` | `codex exec` 내장 `image_gen` | `EXPERIMENTAL`, `explicit_only` | ID 지정 + `allow_experimental` |
| Grok CLI | `grok_imagine` | Grok Build 내장 `image_gen` / `image_edit` | `EXPERIMENTAL`, `explicit_only` | ID 지정 + `allow_experimental` |

> **현재 검증 수준.** 단위 테스트(가짜 CLI 사용)와 실제 CLI 상태 진단까지만 확인했습니다. **실제 이미지 생성(E2E)은 아직 한 번도 검증하지 못했습니다.** 그래서 두 CLI provider는 `ACTIVE`로 올리지 않았고 자동 선택되지 않습니다. 근거는 [M1 상태 기록](m1/STATUS.json)과 [상세 설명](m1/PROVIDERS.md)을 보세요.

### 로컬 설치

두 CLI는 이 저장소가 설치해 주지 않습니다. 각자 설치하고 로그인해야 합니다.

```powershell
npm install -g @openai/codex      # Codex CLI
codex login                       # ChatGPT 계정 로그인

npm install -g @xai-official/grok # Grok Build CLI
grok login                        # 브라우저가 없으면: grok login --device-code
```

`assetpipe`는 계정 로그인 상태만 사용합니다. 로그인되어 있지 않으면 **API 키를 찾아 우회하지 않고** `BLOCKED`로 멈춥니다. Grok은 예외적으로 `XAI_API_KEY` 환경변수를 쓸 수 있으며, registry의 `backend.auth`에 `mode: env_api_key`와 변수 이름을 직접 적었을 때만 동작합니다(아래 "격리와 보안" 참고).

실행 파일이 `PATH`에 없으면 [config/pipeline.yaml](../config/pipeline.yaml)의 `providers.codex_cli.executable` / `providers.grok_cli.executable`에 경로를 적습니다.

### 상태 진단

진단은 과금 요청을 만들지 않습니다. provider마다 독립적으로 확인하며, 하나가 실패해도 다른 결과에 영향을 주지 않습니다.

```powershell
assetpipe providers                       # 세 provider 모두
assetpipe providers --provider codex_cli  # 하나만
```

MCP에서는 `asset_capabilities`의 `provider_readiness`로 같은 정보를 볼 수 있습니다(도구 6개 계약은 그대로입니다).

| 상태 | 뜻 | 조치 |
| --- | --- | --- |
| `AVAILABLE` | 설치·로그인 확인됨. 생성 요청을 시도할 수 있음 | 실제 생성은 요청해 봐야 확정됨 |
| `BLOCKED` | 설치는 됐지만 사용자 조치가 필요함(로그인 안 됨 등) | `codex login` / `grok login` |
| `UNAVAILABLE` | 실행 파일이 없거나 실행할 수 없음, 이미지 기능이 꺼져 있음 | 설치 또는 경로 설정 |

`AVAILABLE`은 "생성에 성공했다"는 뜻이 아닙니다. Codex는 `codex features list`로 `image_generation` 기능이 켜져 있는지 확인하지만, 진단의 `generation_probe`는 항상 `NOT_RUN`이며, Grok의 도구별 가용성(`image_gen`/`image_edit`)은 `NOT_PROBED`로 표시됩니다. 도구 목록을 과금 없이 조회할 방법이 없기 때문입니다.

### 사용

```powershell
assetpipe create --type nonpixel-image --project game-a --asset-id fox `
  --workflow codex_imagegen --allow-experimental `
  --prompt "a small fox scout with a red scarf, flat colors"
```

레퍼런스 이미지 편집은 Grok의 `image_edit` 또는 Codex의 `image_gen` 참조 입력을 명시해 사용합니다.
Codex는 복사본 1장을 `--image`로 첨부합니다. 두 경로 모두 실험적입니다. 프로젝트 초상화 참조 편집은 실생성으로 검증했지만,
인물이 유지됐는지는 결과마다 사람이 확인합니다([동일 인물 변형 작업](factory/IDENTITY_VARIANT.md)).

```powershell
assetpipe create --type nonpixel-image --asset-id fox --reference ref.png `
  --prompt "same fox, add a blue cloak" --workflow grok_imagine --allow-experimental
```

MCP 클라이언트(Codex·Claude Code)에서는 준비한 브리프의 `workflow_preferences`에 `id`와 `allow_experimental: true`를 지정합니다. CLI provider는 자동 선택되지 않으며, 사용자가 명시한 workflow ID로만 선택됩니다.

### 프롬프트와 금지 요소

PromptSpec은 provider별 프롬프트로 컴파일되며 `canonical_traits`, `visual_traits`, `style`, `silhouette`, `forbidden_elements`를 모두 보존합니다. CLI provider는 이 항목을 라벨이 붙은 자연어 문단으로 전달합니다. 컴파일 결과는 `assetpipe compile-prompt`로 미리 볼 수 있습니다.

| 구분 | 의미 | 대상 |
| --- | --- | --- |
| 네이티브 negative prompt (`negative_prompt`) | 모델이 별도 입력으로 받아 억제함 | ComfyUI의 Anima 계열 |
| 자연어 금지 지시 (`negative_prompt_instruction`) | "다음을 포함하지 마라"는 문장일 뿐 **보장되지 않음** | Codex CLI, Grok CLI |

자연어 지시는 manifest에 `negative_prompt_mode: NATURAL_LANGUAGE_INSTRUCTION`으로 기록되고, QA 보고서의 `review_required`에 금지 요소와 정본 특징이 사람 검토 항목으로 남습니다. 자동으로 준수 여부를 판정하지 않습니다.

### 지원하지 않는 것

CLI provider는 아래를 보장하지 못합니다. 요청에 이런 조건이 있으면 조용히 무시하지 않고 **라우터가 과금 전에 차단**하거나 **QA가 실패 처리**합니다.

| 항목 | 처리 |
| --- | --- |
| `seed`, 정확한 재현 | 미지원. manifest에 `seed: null`, `seed_support: UNSUPPORTED`로 기록하고 사용자가 지정한 값은 `requested_seed`로만 남김 |
| 정확한 해상도(`constraints.resolution`) | 라우터가 `exact_resolution` 부족으로 차단 |
| 투명 배경 | `resolution`과 함께 요청하면 로컬 배경 제거로 전달(아래 "크기·투명·용량 규격으로 내보내기"), 크기 없이 요청하면 라우터가 `transparent_output` 부족으로 차단 |
| 이미지 속 글자 | 라우터가 `text_rendering` 부족으로 차단 |
| 종횡비 | Grok은 지원 목록 밖이면 요청 전에 중단, 그 외는 결과를 QA가 3% 허용 오차로 검사 |

### 격리와 보안

- **작업 폴더**: 시스템 임시 폴더(프로젝트·git 트리 밖)에 일회용으로 만들고 실행 후 삭제합니다. 모델은 이 안에 복사된 파일만 볼 수 있으며, 프로젝트 문서·소스 경로는 전달하지 않습니다.
- **환경변수**: 허용목록(`PATH`, `HOME` 등 실행에 필요한 최소 항목)만 자식 프로세스에 넘깁니다. 프록시나 API 키가 필요하면 `providers.<id>.pass_env`에 **이름만** 적습니다. manifest에는 값이 아니라 이름만 기록합니다.
- **프롬프트**: 명령줄 인자가 아니라 stdin/파일로 전달합니다.
- **로그**: 키·토큰·`Bearer` 등 비밀로 보이는 값은 마스킹한 사본만 저장합니다.
- **재귀 차단**: 자식 프로세스에는 `ASSETPIPE_PROVIDER_DEPTH=1`을 설정하고, 이 값이 있으면 `assetpipe create`와 `assetpipe-mcp`가 시작 즉시 `RECURSION_BLOCKED`로 거부합니다. Codex는 `--ignore-user-config`로 사용자 설정(MCP 서버 포함)을 읽지 않고 `--sandbox read-only`로 실행합니다.
- **Grok 인증 방식별 차이**: 로그인 모드는 인증 저장소가 실제 홈에 있어 홈을 그대로 쓰되, 외부 훅·MCP·스킬 가져오기를 끄고 허용 도구를 이미지 도구 하나로 제한합니다. `env_api_key` 모드는 `GROK_HOME`을 빈 임시 폴더로 바꿔 사용자 플러그인·MCP가 아예 로드되지 않습니다.
- **registry 인자 검증**: `backend.cli_args`에 `--always-approve`, `--sandbox`, `-c`, `--cwd` 등 격리·승인 정책을 약화하는 인자는 쓸 수 없습니다.

### 사용량과 비용

- 생성 요청 1회는 이미지 1장을 만들려는 **한 번의 CLI 실행**입니다. 타임아웃·실패 시에도 자동으로 다시 시도하지 않습니다(중복 과금 방지).
- 다른 provider로 자동 전환(fallback)하지 않습니다. 실패하면 오류 코드와 함께 멈추고, 다시 시도할지는 사용자가 정합니다.
- 사용량이 계정 플랜에서 차감되는지, 과금되는지는 로그인 방식과 계정 정책에 따릅니다. 이 도구는 잔여 한도를 조회하지 않습니다. CLI가 사용량 정보를 출력하면 `usage`로 기록하고, 아니면 `usage_support: NOT_REPORTED`로 표시합니다.
- 진단(`assetpipe providers`, `asset_capabilities`)은 생성 요청을 만들지 않습니다.

### 실패 모드

실패해도 provider 기록(진단·로그·타이밍)은 manifest의 `generation.provider`에 남고, `outputs`는 비어 있으며 `game_ready`는 `false`입니다. `BLOCKED`/`UNAVAILABLE`은 manifest `status`에도 그대로 기록됩니다.

| 오류 코드 | manifest 상태 | 의미와 조치 |
| --- | --- | --- |
| `EXECUTABLE_NOT_FOUND`, `CLI_NOT_RUNNABLE`, `IMAGE_FEATURE_DISABLED` | `UNAVAILABLE` | CLI 설치·경로 설정, Codex 이미지 기능 활성화 |
| `AUTH_NOT_CONFIGURED` | `BLOCKED` | 로그인(`codex login` / `grok login`) 또는 API 키 환경변수 설정 |
| `RECURSION_BLOCKED` | 없음(실행 폴더·manifest를 만들기 전에 거부) | 생성 CLI 안에서 assetpipe를 다시 호출함. 의도한 동작이 아니면 CLI의 플러그인·MCP 설정 확인 |
| `ASPECT_RATIO_UNSUPPORTED` | `FAILED` | 요청 전에 중단됨. 브리프 조건 조정 |
| `REFERENCE_UNSUPPORTED` | `BLOCKED` / `FAILED` | 참조 입력 미지원. Codex는 `exec --help`의 `--image` 지원 확인 필요 |
| `TIMEOUT` | `FAILED` | 시간 초과 후 프로세스 종료. **재시도하지 않음**. 계정에서 요청이 처리됐을 수 있으니 확인 후 직접 재실행 |
| `CLI_EXIT_NONZERO` | `FAILED` | CLI 비정상 종료. `stderr.log`(마스킹됨) 확인 |
| `REFUSED` | `FAILED` | CLI가 생성을 거절함. 프롬프트·금지 요소 검토 |
| `OUTPUT_MISSING` | `FAILED` | 종료는 정상인데 이미지 파일이 없음. 로그 확인 |
| `OUTPUT_AMBIGUOUS` | `FAILED` | 이미지가 둘 이상 생겨 어느 것인지 판단하지 않음. `orphan_outputs`에서 직접 확인 |
| QA 실패 | `FAILED` | 해상도·종횡비·투명도 불충족. 원본은 `rejected_outputs`에 보존, 자동 통과 없음 |

### 기록되는 정보

`run_manifest.json`의 `generation.provider`에는 provider ID·엔진·도구·모델(설정값과 CLI가 보고한 값)·CLI 버전·인증 방식(종류만, 비밀 제외)·실행 상태·소요 시간·요청/세션 ID와 사용량(CLI가 보고할 때만)·전송한 프롬프트의 해시와 파일·실제 명령(`argv`)과 전달한 환경변수 이름·원본 이미지의 경로와 SHA-256이 들어갑니다. 원본 이미지는 CLI가 저장한 위치에서 복사해 `010_generation/<codex_cli 또는 grok_cli>/raw/`에 보존하며 원래 위치는 건드리지 않습니다.

### ACTIVE 승격 조건

실제 생성이 검증되지 않은 CLI provider는 registry에서 `ACTIVE`가 될 수 없고, 로더가 거부합니다. 다음을 모두 만족해야 합니다.

1. 로그인한 환경에서 `python scripts/provider_e2e.py --provider codex_imagegen --confirm-paid-request` (또는 `grok_imagine`)를 실행해 `REAL_GENERATION_VERIFIED` 증거를 만든다. 계정 사용량이 소모됩니다.
2. 생성된 이미지를 사람이 직접 확인한다.
3. 증거 JSON을 `docs/m1/`에 커밋하고 registry의 `validation.status`를 `REAL_GENERATION_VERIFIED`, `validation.evidence`를 그 경로로 바꾼다.

승격 후에도 `selection: explicit_only`는 별도 판단 전까지 유지하세요. 스크립트는 `status`를 자동으로 바꾸지 않습니다.

### Windows 참고

Codex·Grok은 npm으로 설치하면 `.cmd` 실행 파일이 생깁니다. 이 저장소는 셸 없이 인자 목록으로 실행하며 프롬프트를 stdin/파일로 넘깁니다. Windows에서 두 Provider의 프로젝트 참조 편집을 실제 검증했습니다. 설치된 CLI의 기능·로그인과 프로젝트 계약은 실행 전에 확인합니다.

## 크기·투명·용량 규격으로 내보내기

게임 매니페스트 규격(예: 256×256, 알파, 512KB 이하)은 브리프의 `constraints`에 그대로 적습니다.

```json
"constraints": {"resolution": [256, 256], "transparency": true, "max_file_kb": 512, "palette": [], "silhouette": null, "style": null}
```

`resolution`과 `transparency: true`가 함께 있고 workflow가 투명 출력을 지원하지 않으면, NONPIXEL_IMAGE는
흰 배경 원본을 workflow 기본 크기(krea2_base는 1024px) 이상으로 생성한 뒤 로컬에서 배경을 제거하고
비율을 유지한 채 정확한 캔버스에 가운데 맞춥니다(잘라내지 않음). 설정은 `config/pipeline.yaml`의
`nonpixel_delivery`이며 프로젝트 초상화와 같은 `u2netp.onnx` 모델과 `rembg==2.0.69`(`pip install -e ".[portrait]"`)를 씁니다.
모델이 없거나 해시가 다르면 과금 전에 라우터가 차단합니다. `max_file_kb`를 넘는 결과는 QA가 실패 처리합니다.
프로젝트 Visual SOT가 있는 프로젝트는 SOT의 `delivery_profile`만 따르고 이 기본값을 쓰지 않습니다.
결과는 여전히 `CANDIDATE_READY_REVIEW_REQUIRED`, `game_ready: false`이며 사람이 고릅니다.

## Asset Brief와 공통 프롬프트

입력은 [Asset Brief 스키마](../schemas/asset_brief.schema.json)를 통과합니다. 프로젝트·애셋 ID, 목적, 출처, 캐릭터 정본 특징, 제약, 애니메이션 요구, workflow 선호, 금지 요소와 미정 항목을 기록합니다.

문서 근거는 `EXPLICIT`(명시), `DERIVED`(근거 있는 해석), `UNSPECIFIED`(미정)로 구분합니다. 미정 내용을 정본으로 자동 확정하지 않으며 프로젝트 문서가 정본입니다.

```powershell
assetpipe brief from-docs tests/fixtures/character_test.md --prepared examples/character_test_brief.yaml --output workspace/document_brief.json
assetpipe route --brief workspace/document_brief.json --output workspace/document_route.json
```

Codex·Claude Code 또는 사람이 문서를 읽고 Brief를 준비합니다. `from-docs`는 준비된 Brief와 출처 경로를 검증하며, 문서 내용을 자동 해석하지 않습니다.

프롬프트는 **공통 PromptSpec → 모델별 어댑터 → ComfyUI workflow**로 연결합니다. Anima·Krea2 어댑터는 특징과 제약을 보존하고 모델 전용 접두어를 프로파일에서 관리합니다. Tomohi의 트리거 워드는 `tomohi`입니다.

```powershell
assetpipe compile-prompt --brief examples/prompt_spec_courier.yaml --output workspace/compiled.json
assetpipe create --brief examples/prompt_spec_courier.yaml --project game-a
```

Krea 스타일 문구는 선택한 설명과 출처 URL을 기록할 수 있습니다. [한국어 PromptSpec 안내](PROMPT_SPEC.md)를 참고하세요. Qwen·Flux·SDXL 어댑터는 아직 연결하지 않았습니다.

## Workflow 선택

[workflow registry](../config/workflow_registry.yaml)에 출력 유형, 기능, 태그, 우선순위, 상태, 파일과 모델을 등록합니다. 라우터는 출력 유형과 기능을 확인하고 태그·상태·우선순위로 선택합니다. 호환되는 명시적 workflow 지정은 우선합니다.

| 상태 | 선택 규칙 |
| --- | --- |
| `ACTIVE` | 자동 선택 가능 |
| `VALIDATED` | 명시적으로 지정하면 사용 가능 |
| `EXPERIMENTAL` | workflow ID와 `allow_experimental: true`가 필요 |
| `REJECTED` | 실행 금지 |

지원하지 않는 레퍼런스·negative prompt·이미지 속 글자 요구는 조용히 버리지 않고 차단합니다. 선택 근거와 대체 후보는 `route_decision.json`에 기록합니다.

## 넌픽셀 애니메이션 (명시적 모션 작업)

기존 NONPIXEL_IMAGE 결과 하나를 부모로 지정한 작업 파일(job)로 실행합니다. 작업 파일은 요청, 영상 또는
생성 입력, 원본 해시, 프레임 구간, 알파 정책을 고정합니다.

```powershell
assetpipe factory motion-plan --job workspace/my-job.json
assetpipe create --type nonpixel-animation --motion-job workspace/my-job.json `
  --motion-plan-sha256 <반환된-plan-sha256> --output workspace/my-new-motion-run
```

```text
부모 정지 이미지 → (I2V 생성 또는 기존 영상) → 원본 영상 보존 → 프레임 추출
  → 알파·정렬 → 명시적 루프 선택(레시피) → 아틀라스 → Godot SpriteFrames / Phaser atlas
```

- `--output`은 설정 루트의 `workspace` 아래 새 디렉터리여야 합니다.
- 실생성은 별도로 승인된 1회 예산이 있을 때만 수행하며 재시도·provider fallback은 없습니다.
- 프롬프트·Brief만으로 영상을 자동 생성하지 않습니다. 참조 이미지는 현재 1장(`IDENTITY_PRIMARY`)만 검증되었습니다.
- 결과는 `REVIEW_REQUIRED`, `game_ready=false`로 남습니다.

작업 파일 형식과 예산·리뷰 경계는 [모션 작업 계약](factory/MOTION_JOB.md),
레시피는 [모션 리뷰 레시피](factory/MOTION_REVIEW_RECIPE.md)를 참고하세요.

## 동일 인물 변형 (표정·포즈)

T2I로 만든 베이스 1장을 사람이 고른 뒤, 그 이미지를 참조로 provider의 이미지 편집을 1회 실행해
표정이나 포즈만 바꿉니다. 같은 인물을 유지한 정지 이미지를 만들기 위한 경로이며, 결과는 모션 작업의 부모로도 쓸 수 있습니다.

```powershell
assetpipe factory variant-plan --job workspace/jobs/fox_surprised.json --allowed-root . --allowed-root <provider 출력 폴더>
assetpipe factory variant-run --job workspace/jobs/fox_surprised.json --plan-sha256 <plan_sha256> `
  --authorization workspace/jobs/fox_surprised-auth.json --authorize-generation --allowed-root . --allowed-root <provider 출력 폴더>
```

- 참조 편집은 Grok CLI(`grok_imagine`)와 Codex CLI(`codex_imagegen`)에 등록돼 있습니다. 둘 다 실험적이며 프로젝트 초상화의 실제 참조 편집·RGBA 전달 근거가 있습니다. 인물 보존 수용은 결과별 사람 검토로 기록합니다. [프로젝트 참조 편집 계약](factory/IDENTITY_VARIANT.md)을 따릅니다. AGY 나노바나나는 후속 단계입니다.
- 유지 항목(얼굴·헤어·의상·장비·화풍 등)은 변형 종류별로 고정되며, 인물이 유지됐는지는 사람이 판단합니다.

작업 파일 형식, 승인 파일, 제한 사항은 [동일 인물 변형 작업](factory/IDENTITY_VARIANT.md)을 참고하세요.

## 픽셀 검증과 Static Master 승인

> 32px 픽셀 연구는 동결 상태입니다. 64px(Krea2 Pixel64) 경로만 2026-11-07 재개되었습니다.

PIXEL_STATIC 후보는 Pixel Gate 앞에서 색 수를 `pixel.max_colors`(기본 32색)로 줄입니다(디더 없음, 알파·크기 보존).
브리프에 `palette`가 있으면 각 픽셀을 가장 가까운 허용 색으로 맞춥니다. 결과는 `035_quantize/`에 보고서와 함께 남고,
양자화 전 분석의 실패 사유(그라데이션·안티에일리어스 의심)도 manifest에 그대로 기록됩니다. 색을 줄였다고 승인되지는 않습니다.
끄려면 `config/pipeline.yaml`의 `pixel.quantize_to_budget: false`.

### 64px 픽셀 (Krea2 Pixel64)

`krea2_pixel64`(VALIDATED, ID로 지정하면 `allow_experimental` 없이 사용)는 Krea2 Turbo FP8과 제작자 k2-pixel64 DoRA LoRA로 1024px를 만들고 제작자 Refiner로
64×64·24색으로 정리합니다. LoRA의 `.magnitude`까지 적용하는 저장소 노드를 ComfyUI에 설치해야 합니다.
`create`는 생성 전에 ComfyUI가 실제로 불러온 노드의 해시를 저장소 파일과 비교해, 설치가 안 됐거나
업데이트 후 재시작하지 않았으면 `COMFYUI_CUSTOM_NODE_MISSING`/`STALE`로 멈춥니다.

```powershell
.venv/Scripts/python scripts/install_comfyui_dora.py --comfyui-root <ComfyUI 폴더> --update --restart
```

기존 로더(magnitude 미적용) 그래프는 `krea2_pixel64_stock`(EXPERIMENTAL)입니다. alpha/rank=1은 소스 근거 가설입니다.
VALIDATED는 [검증 기록](research/KREA2_PIXEL64_VALIDATION_20261108.json)의 그래프·노드 해시가 지금과 같을 때만
유지됩니다. 그래프나 노드를 바꾸면 레지스트리가 이 항목을 EXPERIMENTAL로 내리고 `evidence_check`에 이유를 남깁니다.

MCP에서는 기존 여섯 도구로 씁니다. `asset_capabilities`의 `validated_workflows`에 나오고, `asset_build_brief`에
`workflow_id: krea2_pixel64`를 주면 `asset_generate`로 실행됩니다. `asset_inspect_run`은 투명 납품본 상태와 구멍 가능성 수,
남은 사람 단계(`next_human_steps`), 승인 기록이 있으면 다시 검증한 결과(`static_approval`)를 돌려줍니다.
크기 선택·Aseprite 확인·승인은 MCP로 하지 않고 위 CLI 명령으로 사람이 합니다.

```powershell
assetpipe create --brief brief.json --allow-experimental --seed 20261108 --output workspace/run
assetpipe pixel-transparent --input workspace/run/035_quantize/quantized.png --output workspace/run/071_holes --created-by me --hole 29,6 --aseprite
assetpipe pixel-edit --input <투명 PNG> --spec edit.json --output workspace/run/080_edit --created-by me --aseprite
assetpipe pixel-ledger review --ledger workspace/pixel64_ledger.json --id knight --candidate <파일> --decision ADOPTED --edit-minutes 0 --reviewer me
```

`create`는 Pixel Gate 통과 후 `070_transparent/`에 이진 알파 납품본, 검토 미리보기, Aseprite 왕복 결과를 만듭니다.
테두리가 흰 배경 한 색이 아니면(생성된 검은 띠 등) 납품본 없이 `BLOCKED_REVIEW_REQUIRED`로 이유를 남기고,
캐릭터 안에 갇힌 배경은 표시만 합니다(자홍색 = 구멍 가능성, 청록색 = 하이라이트 가능성). 지울 곳은 `pixel-transparent --hole X,Y`로 새 폴더에 다시 만듭니다.
프로젝트 고정 팔레트는 `create --palette-file <.gpl|.hex|.txt>`로 지정합니다. 파일 색이 브리프 `palette`가 되고
manifest에 파일 경로·해시가 남습니다. 흰 배경 근처 픽셀은 흰색 그대로 두어 투명 처리에서 지우고, 나머지는 가장 가까운
팔레트 색(RGB 거리)으로 바꿉니다. 팔레트에 비슷한 색이 없으면 피부·옷 색이 바뀔 수 있으니 결과를 꼭 확인하세요.
결과는 모두 사람 검토가 필요합니다. 경위와 수치는 [Pixel64 계획](factory/PIXEL64_PRODUCTION_PLAN_20261107.md)에 있습니다.

채택한 스프라이트를 Static Master로 승인하는 순서입니다. 마지막 단계는 사람이 Aseprite에서 확인한 뒤에만 실행합니다.

```powershell
assetpipe review-resolution --run <run> --resolution 64 --reviewed-by me --reason "native 64px"
assetpipe export-static --run <run> --resolution-review <run>/resolution_review.json
assetpipe approve-static --run <run> --reviewed-by me --reason "checked in Aseprite" --aseprite-reviewed --transparent <run>/070_transparent/transparent.png
```

`--transparent`를 주면 투명 납품본도 승인 기록에 해시와 함께 들어갑니다. 납품본은 승인한 불투명 마스터에서 배경만 지운
것이어야 하고 Aseprite 왕복이 PASS여야 합니다. 구멍 가능성 영역이 남아 있으면 `--hole`로 지우거나
`--accept-possible-holes`로 명시해야 합니다. `pixel-edit`로 고친 납품본은 마스터와 픽셀이 달라 이 경로로 승인되지 않습니다.

```text
Brief → 라우터 → 생성 후보 → 분석 → 안전한 알파 처리
      → Pixel Gate → 해상도 검토 → Aseprite 내보내기 → 명시적 승인
```

```powershell
assetpipe create --type pixel-static --project game-a --asset-id warrior --prompt "sword wielding fantasy warrior"
```

자동 변경은 바이너리 알파 처리로 제한합니다. 캐릭터 정체성·의상·장비·실루엣 의미를 자동으로 다시 디자인하지 않습니다. Pixel Gate가 실패하면 중단하고 내보내기를 차단합니다. 검토 대기 후보도 자동 진행하지 않습니다.

`RESOLUTION_REVIEW_REQUIRED` 상태에서는 `assetpipe.pixel.resolution.record_resolution_review`로 통과 후보의 해상도·검토자·사유를 기록합니다. 이후:

```powershell
assetpipe export-static --run <실행 폴더> --resolution-review <검토 기록.json>
assetpipe approve-static --run <실행 폴더> --aseprite-reviewed --reviewed-by "<검토자>" --reason "<Aseprite 검토 결과>"
```

`approve-static`은 통과한 정적 내보내기와 명시적 Aseprite 검토에 한해 `approval_record.json`을 만듭니다. 승인 기록은 검증 manifest, 해상도 보고서·검토 기록, 후보, Aseprite 마스터와 내보낸 이미지의 해시에 연결합니다. 근거가 바뀌면 승인은 무효이며, 상태·이미지 해시만 적힌 기존 승인 기록은 충분하지 않습니다.

## 픽셀 애니메이션 (기존 blue-tunic 프로필)

```text
승인된 Static Master + 기존 검토된 모션
  → 의미별 프레임 선택 → CHARACTER_LOCAL_DIRECT → 마스터 팔레트
  → Pixel Gate → Aseprite → 스프라이트 시트
```

Brief의 `production`에 `static_master`, `approval_record`, `motion_reference`, `selection`, `direct_profile`을 지정합니다. 진입 시 승인 근거를 다시 검증하며 새 모션 생성은 자동 실행하지 않습니다.

현재 검증된 `blue_tunic_white_matte_v1`은 파란 튜닉 캐릭터와 흰 레퍼런스 배경의 검토된 8프레임 걷기만 지원합니다. 범용 캐릭터·동작 복원 알고리즘이 아닙니다. 기존 픽셀 연산과 FFmpeg 색 변환을 보존합니다.

[마이그레이션 예제](../examples/pixel_animation_smoke.yaml)는 인접한 기존 `pixel-pipeline`의 자료를 참조합니다. 해당 자료는 배포하지 않으며, 강화된 승인 규칙을 적용하려면 검토된 정적 내보내기에서 새 승인 기록을 만들어야 합니다.

Aseprite는 RGBA 왕복 일치, 프레임 수·시간·태그·메타데이터를 검증합니다. 애니메이션 결과도 최종 검토가 필요하며 `game_ready: false`로 남습니다. Pixel Art Fixer는 선택적 복구 정책으로만 유지합니다.

## 64px 픽셀 애니메이션 (walk·idle·attack)

승인된 64px Static Master 하나에서 걷기·대기·공격을 만듭니다. 위의 blue-tunic 프로필과는 별개 경로이며, 그 프로필을 64px 캐릭터에 쓰지 않습니다.

```powershell
assetpipe pixel64-motion-reference --run <승인된 정적 실행> --output workspace/m/ref
assetpipe pixel64-motion-video --reference workspace/m/ref --output workspace/m/video --seed 1 --action walk
assetpipe pixel64-motion-frames --video <영상 파일> --output workspace/m/frames
# 접촉 시트를 보고 사람이 프레임 번호를 골라 selection JSON을 씁니다.
assetpipe pixel64-motion-build --run <승인된 정적 실행> --video <영상 파일> --selection selection.json --output workspace/m/build
assetpipe pixel64-motion-approve --run workspace/m/build --reviewed-by me --reason "checked in Aseprite" --aseprite-reviewed
```

- 영상은 로컬 ComfyUI의 MiniMax H3 R2V로 실행당 1회만 만들며, 재시도·fallback은 없습니다.
- `--action`은 `walk`·`idle`·`attack`입니다. attack은 반복하지 않고 한 번만 재생됩니다(Godot `loop: false`, Phaser `repeat: 0`).
- `--motion-note`로 캐릭터별 지시(예: 이미 칼을 뽑아 든 상태)를 덧붙일 수 있습니다.
- selection JSON에는 `frames`, `fps`, 선택적 `durations_ms`(프레임별 40–1000ms)와 `master_lock`을 적습니다. `master_lock`은 머리처럼 거의 움직이지 않는 영역을 승인 마스터에서 그대로 붙여 프레임마다 선이 떨리는 것을 막습니다.
- 결과는 `REVIEW_REQUIRED`이며 Aseprite에서 사람이 확인한 뒤에만 승인합니다. 형식과 실행 기록은 [Pixel64 애니메이션 계획](factory/PIXEL64_ANIMATION_PLAN_20261108.md)에 있습니다.

## STYLE MENU v1 — 운영용 비픽셀 화풍 선택

[24종 운영 메뉴와 실제 이미지](../research/style_catalog/style_menu_v1/STYLE_MENU_v1.md) · [Agent Recipe Selection Guide v1](style_menu/AGENT_RECIPE_SELECTION_GUIDE_v1.md) · [모델/recipe/workflow 설정](../config/styles/style_menu_v1.yaml)

게임 SOT의 `art_style` → STYLE-101~124 → 모델별 recipe/compiler/workflow로 연결합니다. family는 탐색용이고 24종은 독립 선택 단위입니다. 216장 실증 기준 Krea2 Turbo20 / Anima Base rebuilt3 / unresolved1이며, STYLE-117은 용도별 정책이 필요합니다. 생산 결함은 별도 경고이고 생성 자산은 human review 전 REVIEW_REQUIRED입니다. 메뉴 조회는 새 generation 승인이 아닙니다.

옛 CAND 및 STYLE-001~012 메뉴/연구 문서는 history 용도로 보존합니다. 운영 기본 선택에는 사용하지 않습니다.

Manual / Rescue Override: 승인된 실행 범위 안에서만 NONPIXEL_IMAGE 모델을 수동 지정하거나
구제 후보를 쓸 수 있습니다. 화풍과 캐논은 잠긴 상태로 유지되며, `assetpipe rescue-plan`은 생성 없이 후보만 준비합니다.
적용 전에 범위 승인과 1회 요청 예산이 필요하고 자동 fallback이나 우승 후보 자동 승격은 없습니다.
자세한 내용은 [Manual / Rescue Override](style_menu/MANUAL_RESCUE_OVERRIDE.md)를 참고하세요.

## 프로젝트별 애셋 레퍼런스를 설계할 때

게임마다 레퍼런스 문서 양식을 통일할 필요는 없습니다. [모델·스타일 취급 설명서](ASSET_PIPELINE_MODEL_STYLE_HANDBOOK_v0.1.md)는 현재 **조사 미완성 목록**입니다. 등록된 모델/워크플로/스타일과 일부 실패·기술 QA 결과만 확인되었고, 특정 표현의 우월성이나 최적 레시피는 입증되지 않았습니다. [근거 감사](research/MODEL_STYLE_EVIDENCE_AUDIT_20261004.md) 및 [재설계 실험 계획](research/MODEL_STYLE_BENCHMARK_PROTOCOL_v0.1.md)을 먼저 확인하세요. 각 게임은 자체 ACTIVE/SOT에 적합한 미술 레퍼런스를 자유롭게 작성하고, 제작 스킬은 이를 **기존 Asset Brief/PromptSpec**로 변환해 실행합니다. 설명서는 프로젝트 캐논이나 모델 품질 승인이 아닙니다.

## 검증 근거 기반 모델 지식 조회 (읽기 전용)

모델·워크플로·화풍 카탈로그의 **등록 상태**와 실물 이미지의 **예술적 검증 상태**를 혼동하지 않도록 오프라인 조회 기능을 제공합니다. [모델 지식 기반 취급 설명서](knowledge/MODEL_CAPABILITY_GUIDE_v0.1.md)를 참고하세요.

```powershell
assetpipe knowledge --model-id anima-base
assetpipe knowledge --style-id limited_palette_pixel
assetpipe knowledge --models-root "C:/path/to/ComfyUI/models" --hash-models --discover-unregistered --output workspace/local_weight_inventory.json
```

이 기능은 생성·모델 다운로드·모델 교체·Golden 승인 작업을 수행하지 않습니다. 로컬 모델 경로 스캔도 사용자가 `--models-root`를 명시했을 때만 진행되며, 모형이 설치되었거나 SHA256을 계산했다고 해서 모델이 좋은 그림을 그린다고 평가하지 않습니다. 검증된 모델별 미술적 추천/순위는 아직 없습니다.

## 실행 기록과 개발

실패를 포함한 생성 시도마다 `run_manifest.json`을 기록합니다. workflow 해시·버전, 모델·LoRA, seed, 실제 프롬프트·파라미터, ComfyUI 실행 ID, 단계별 상태, QA, 출력과 시간을 보존합니다. 중간 파일을 삭제하거나 기존 실행 폴더를 덮어쓰지 않습니다.
생성물과 로컬 설정은 Git 추적에서 제외합니다.

```powershell
python -m pytest
assetpipe --help
```

Aseprite가 없으면 실제 Aseprite 테스트를 건너뛰며, 로컬 벤치마크가 없으면 해당 애니메이션 회귀 검증을 건너뜁니다. 단위 테스트에는 실행 중인 ComfyUI가 필요하지 않습니다.

```text
src/assetpipe/
  brief/ router/ registry/     # 입력 계약과 workflow 선택
  prompts/                    # 공통 프롬프트와 모델별 컴파일
  providers/ pipelines/       # 외부 도구 연결과 생산 경로
  pixel/ motion/              # 픽셀·모션 인터페이스
  manifests/ cli/             # 실행 기록과 CLI
  _ported/                    # 이식한 검증 구현
integrations/mcp/             # 로컬 MCP 어댑터
plugin/                      # 플러그인 지침과 참조 자료
config/ schemas/ examples/ tests/ docs/
```

[마이그레이션 목록](migration_inventory.json)은 원본 해시와 변경 내용을 기록합니다. bootstrap 스크립트는 기존 저장소와 로컬 벤치마크가 필요한 마이그레이션 도구이며 일반 설치 단계가 아닙니다.
GUI·웹 UI·클라우드 배포·DB는 현재 범위에 포함하지 않습니다.

## 부가 기능

### 스타일 인텔리전스 (M2)

공통 스타일 후보와 모델별 레시피는 `config/styles/`에서 관리합니다.
프로젝트 Visual SOT → 승인된 프로젝트 Style Pack → 공통 Catalog → 모델 기본값 순으로
선택하며, `style_id`는 선택적 Brief 필드입니다. 사람의 승인과 실생성 근거가 없는
조합은 자동 기본값이 되지 않습니다. 명시한 workflow/model은 기능 검증 후 우선합니다.
Codex와 Claude Code는 동일한 플러그인 스킬을 사용합니다.
[설정·비교 생성·승인 계약](m2/STYLE_INTELLIGENCE.md)을 참고하세요.

### 오프라인 레시피 연구 (M2.6)

`assetpipe mining`은 저장된 공개 메타데이터를 검증하거나 생성 없이 후보 레시피를 컴파일합니다.
후보 레시피는 운영 기본값이 되지 않습니다.
[프롬프트 마이닝 방법](style/PROMPT_MINING_METHOD.md), [M2.5 검증 인계](style/RECIPE_VALIDATION.md)를 참고하세요.

### 시각 위계 리뷰 미리보기

기술 QA를 통과한 기존 정지 후보에 `assetpipe visual-review --run <실행 디렉터리>`로
재현 가능한 리뷰 미리보기를 만들 수 있습니다. NONPIXEL_IMAGE Brief에 초점 의도를 선언할 수 있으며,
자산을 승인하지는 않습니다. [범위·충돌 처리·사용법](style/VISUAL_HIERARCHY.md)을 참고하세요.
