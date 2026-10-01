# Asset Pipeline

프롬프트, 레퍼런스 이미지, 프로젝트 기획문서를 바탕으로 게임용 이미지와 효과음 후보를 만드는 Python CLI 도구입니다. ComfyUI 생성, 후처리·검증, Aseprite 내보내기를 연결합니다.

**생성 결과는 자동 승인하지 않습니다.** 픽셀 캐릭터는 검증을 통과한 후보만 검토 후 Static Master로 승인하며, SFX도 기본 검증 후 직접 들어봐야 합니다. 실패한 단계는 중단하고 기록을 보존합니다.

## 지원 기능과 현재 상태

| 출력 유형 | 동작 |
| --- | --- |
| `PIXEL_STATIC` | 픽셀 후보 생성 → 분석 → 안전한 알파 처리 → Pixel Gate → 해상도 검토 → Aseprite 내보내기 → 명시적 승인 |
| `PIXEL_ANIMATION` | 승인된 Static Master와 기존 검토된 모션을 사용한 8프레임 걷기 제작, 팔레트·Pixel Gate 검증, Aseprite 내보내기 |
| `NONPIXEL_IMAGE` | ComfyUI 이미지 생성과 기본 QA. 최종 시각 검토 필요. Codex CLI·Grok CLI는 명시 선택하는 실험 provider ([M1](#nonpixel-이미지-provider-comfyui-codex-cli-grok-cli)) |
| `NONPIXEL_ANIMATION` | 실험적 계약만 제공. 실제 생산 실행은 미지원 |
| `SFX` | Stable Audio 3 Medium 효과음 생성, 원본 FLAC·PCM WAV 저장, 기본 오디오 QA. 청취 검토 필수 |

현재 로컬 환경에서 **테스트 82개**가 통과했습니다. 초기 마이그레이션에서는 실제 Aseprite 왕복 검증과 기존 애니메이션 8프레임 RGBA 완전 일치를 확인했습니다. 이후 Krea2 생성과 SFX의 실제 CLI·MCP 생성도 검증했습니다.

검증 근거: [초기 검증](docs/bootstrap_status.json), [프롬프트 검증](docs/prompt_spec_verification.json), [SFX 검증](docs/sfx_verification.json), [플러그인 상태](docs/plugin/STATUS.json).
외부 프로그램, 모델 가중치와 로컬 벤치마크 자료는 저장소에 포함하지 않습니다.

## 설치

필요한 환경:

- Python 3.11 이상
- 설정된 주소에서 실행 중인 ComfyUI. 기본 주소는 `http://127.0.0.1:8188`
- 선택한 workflow의 모델과 노드
- 픽셀 마스터 제작·내보내기용 Aseprite
- 애니메이션 디코딩과 SFX WAV 변환용 FFmpeg. `PATH`에서 실행 가능해야 함

Windows PowerShell에서 설치합니다.

```powershell
git clone https://github.com/prentice7725/asset-pipeline.git
cd asset-pipeline
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,motion,mcp]"
assetpipe --help
```

가상환경을 활성화하지 않으면 `.venv\Scripts\python.exe`와 `.venv\Scripts\assetpipe.exe`를 직접 사용하세요. 외부 연동은 Windows에서 검증했으며 다른 운영체제는 아직 검증하지 않았습니다.

[config/pipeline.yaml](config/pipeline.yaml)에서 ComfyUI 주소와 제한 시간을 설정합니다. Aseprite는 `aseprite.executable` 또는 `ASEPRITE_PATH`로 지정할 수 있으며, `PATH`와 일반 설치 위치도 탐색합니다. workflow 그래프는 Python 코드와 분리해 [config/workflows](config/workflows)에 둡니다.

## Codex·Claude Code에서 사용하기

같은 MCP 서버와 스킬을 Codex와 Claude Code 양쪽에서 사용합니다. 먼저 로컬 설정 파일을 준비합니다.

```powershell
Copy-Item config\mcp_adapter.example.yaml config\mcp_adapter.local.yaml
```

로컬 설정이 이미 있으면 복사하지 마세요. 설정 파일의 `source_roots`에 작업할 프로젝트·애셋 폴더를 추가합니다. 여러 폴더는 YAML 목록으로 지정합니다.

```yaml
core_root: ..
source_roots:
  - C:/workspace/game-a
  - C:/workspace/game-b
  - ../examples
output_root: ../workspace/plugin_runs
```

상대 경로는 설정 파일이 있는 폴더를 기준으로 해석합니다. 소스 폴더는 미리 존재해야 합니다.

### Codex

저장소가 `C:\workspace\asset-pipeline`에 있다면:

```powershell
codex mcp add asset-pipeline -- "C:\workspace\asset-pipeline\.venv\Scripts\assetpipe-mcp.exe" --config "C:\workspace\asset-pipeline\config\mcp_adapter.local.yaml"
```

### Claude Code

**방법 1. 플러그인 설치 (스킬 + MCP 서버)**

플러그인은 `assetpipe-mcp`를 인자 없이 실행하므로, Claude Code를 시작하기 전에 가상환경의 `Scripts` 폴더를 `PATH`에 넣고 `ASSETPIPE_MCP_CONFIG`를 지정합니다.

```powershell
$env:PATH = "C:\workspace\asset-pipeline\.venv\Scripts;$env:PATH"
$env:ASSETPIPE_MCP_CONFIG = "C:\workspace\asset-pipeline\config\mcp_adapter.local.yaml"
claude
```

Claude Code 안에서 저장소를 마켓플레이스로 추가하고 설치합니다. 로컬 폴더 경로나 `prentice7725/asset-pipeline` 모두 사용할 수 있습니다.

```text
/plugin marketplace add C:\workspace\asset-pipeline
/plugin install asset-pipeline@asset-pipeline
```

**방법 2. MCP 서버만 연결**

스킬 없이 도구만 쓰려면 다음 명령 하나로 충분합니다.

```powershell
claude mcp add asset-pipeline --scope user -- "C:\workspace\asset-pipeline\.venv\Scripts\assetpipe-mcp.exe" --config "C:\workspace\asset-pipeline\config\mcp_adapter.local.yaml"
```

`/mcp`에서 연결 상태를 확인할 수 있습니다. 저장소 안에서 Claude Code를 실행하면 `CLAUDE.md`가 `AGENTS.md`의 기여 규칙을 그대로 불러옵니다.

### 요청 예시

설정 후 호스트를 재시작하고 다음처럼 요청합니다.

> asset-pipeline의 asset_capabilities로 준비 상태를 확인해줘.
>
> game-a 프로젝트에 칼 충돌 효과음을 3초로 만들어줘. 음악과 목소리는 없이.

MCP는 기존 코어를 호출하는 6개 도구를 제공합니다: `asset_capabilities`, `asset_build_brief`, `asset_route`, `asset_generate`, `asset_continue_animation`, `asset_inspect_run`.
서버는 Codex 또는 Claude Code가 실행하며, 이미지·오디오 생성 시 ComfyUI는 실행돼 있어야 합니다.

[로컬 설치 안내](docs/plugin/LOCAL_SETUP.md)와 [도구 계약](docs/plugin/MCP_TOOL_CONTRACT.md)을 참고하세요. Claude Code 플러그인은 Linux에서 매니페스트 검증(`claude plugin validate`), 로컬 마켓플레이스 설치, MCP 서버 연결까지 확인했습니다. 다만 Windows에서 실제 생성은 아직 확인하지 않았습니다. Codex 플러그인 패키지는 공식 Plugin Creator 검증과 실제 호스트 설치가 아직 미완료입니다. 공개 플러그인 배포나 원격 서비스는 포함하지 않습니다.

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

SFX 길이는 1–30초이며 기본값은 5초입니다. 현재 `audio_stable_audio_3_medium`은 직접 텍스트 입력 경로로 연결하며 선택적 Qwen 확장 단계는 제외합니다. 원본 FLAC과 16-bit PCM WAV, 길이·무음·피크·RMS 등의 QA 기록을 보존합니다. 통과 후에도 청취 검토가 필요합니다. [SFX 사용 안내](docs/SFX.md).

모든 생성 명령은 실행 manifest 경로를 출력합니다. 저장소 밖에서 실행할 때는 하위 명령 앞에 `assetpipe --root <저장소 경로>`를 지정하세요.

## NONPIXEL 이미지 provider (ComfyUI · Codex CLI · Grok CLI)

`NONPIXEL_IMAGE`는 세 가지 생성 provider를 같은 인터페이스로 지원합니다. 어느 쪽이든 같은 브리프·라우터 preflight, 같은 이미지 QA, 같은 `CANDIDATE_READY_REVIEW_REQUIRED` 검토 게이트를 통과해야 합니다. Pixel·SFX 경로는 바뀌지 않았습니다.

| provider | workflow ID | 사용 도구 | 상태 | 선택 방법 |
| --- | --- | --- | --- | --- |
| ComfyUI | `anima_base`, `krea2_base` 등 | JSON workflow | `ACTIVE` | 자동 라우팅 또는 ID 지정 |
| Codex CLI | `codex_imagegen` | `codex exec` 내장 `image_gen` | `EXPERIMENTAL`, `explicit_only` | ID 지정 + `allow_experimental` |
| Grok CLI | `grok_imagine` | Grok Build 내장 `image_gen` / `image_edit` | `EXPERIMENTAL`, `explicit_only` | ID 지정 + `allow_experimental` |

> **현재 검증 수준.** 단위 테스트(가짜 CLI 사용)와 실제 CLI 상태 진단까지만 확인했습니다. **실제 이미지 생성(E2E)은 아직 한 번도 검증하지 못했습니다.** 그래서 두 CLI provider는 `ACTIVE`로 올리지 않았고 자동 선택되지 않습니다. 근거는 [M1 상태 기록](docs/m1/STATUS.json)과 [상세 설명](docs/m1/PROVIDERS.md)을 보세요.

### 로컬 설치

두 CLI는 이 저장소가 설치해 주지 않습니다. 각자 설치하고 로그인해야 합니다.

```powershell
npm install -g @openai/codex      # Codex CLI
codex login                       # ChatGPT 계정 로그인

npm install -g @xai-official/grok # Grok Build CLI
grok login                        # 브라우저가 없으면: grok login --device-code
```

`assetpipe`는 계정 로그인 상태만 사용합니다. 로그인되어 있지 않으면 **API 키를 찾아 우회하지 않고** `BLOCKED`로 멈춥니다. Grok은 예외적으로 `XAI_API_KEY` 환경변수를 쓸 수 있으며, registry의 `backend.auth`에 `mode: env_api_key`와 변수 이름을 직접 적었을 때만 동작합니다(아래 "격리와 보안" 참고).

실행 파일이 `PATH`에 없으면 [config/pipeline.yaml](config/pipeline.yaml)의 `providers.codex_cli.executable` / `providers.grok_cli.executable`에 경로를 적습니다.

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

레퍼런스 이미지로 편집하려면 Grok의 `image_edit`를 씁니다(Codex는 아직 레퍼런스를 지원하지 않아 라우터가 차단합니다).

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
| 투명 배경 | 라우터가 `transparent_output` 부족으로 차단 |
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
| `ASPECT_RATIO_UNSUPPORTED`, `REFERENCE_UNSUPPORTED` | `FAILED` | 요청 전에 중단됨. 브리프 조건 조정 |
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

Codex·Grok은 npm으로 설치하면 `.cmd` 실행 파일이 생깁니다. 이 저장소는 셸 없이 인자 목록으로 실행하며 프롬프트를 stdin/파일로 넘기므로 `.cmd`도 동작하도록 만들었지만, **Windows에서의 실제 실행은 검증하지 못했습니다**(개발·테스트는 Linux).

## Asset Brief와 공통 프롬프트

입력은 [Asset Brief 스키마](schemas/asset_brief.schema.json)를 통과합니다. 프로젝트·애셋 ID, 목적, 출처, 캐릭터 정본 특징, 제약, 애니메이션 요구, workflow 선호, 금지 요소와 미정 항목을 기록합니다.

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

Krea 스타일 문구는 선택한 설명과 출처 URL을 기록할 수 있습니다. [한국어 PromptSpec 안내](docs/PROMPT_SPEC.md)를 참고하세요. Qwen·Flux·SDXL 어댑터는 아직 연결하지 않았습니다.

## Workflow 선택

[workflow registry](config/workflow_registry.yaml)에 출력 유형, 기능, 태그, 우선순위, 상태, 파일과 모델을 등록합니다. 라우터는 출력 유형과 기능을 확인하고 태그·상태·우선순위로 선택합니다. 호환되는 명시적 workflow 지정은 우선합니다.

| 상태 | 선택 규칙 |
| --- | --- |
| `ACTIVE` | 자동 선택 가능 |
| `VALIDATED` | 명시적으로 지정하면 사용 가능 |
| `EXPERIMENTAL` | workflow ID와 `allow_experimental: true`가 필요 |
| `REJECTED` | 실행 금지 |

지원하지 않는 레퍼런스·negative prompt·이미지 속 글자 요구는 조용히 버리지 않고 차단합니다. 선택 근거와 대체 후보는 `route_decision.json`에 기록합니다.

## 픽셀 검증과 Static Master 승인

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

## 픽셀 애니메이션

```text
승인된 Static Master + 기존 검토된 모션
  → 의미별 프레임 선택 → CHARACTER_LOCAL_DIRECT → 마스터 팔레트
  → Pixel Gate → Aseprite → 스프라이트 시트
```

Brief의 `production`에 `static_master`, `approval_record`, `motion_reference`, `selection`, `direct_profile`을 지정합니다. 진입 시 승인 근거를 다시 검증하며 새 모션 생성은 자동 실행하지 않습니다.

현재 검증된 `blue_tunic_white_matte_v1`은 파란 튜닉 캐릭터와 흰 레퍼런스 배경의 검토된 8프레임 걷기만 지원합니다. 범용 캐릭터·동작 복원 알고리즘이 아닙니다. 기존 픽셀 연산과 FFmpeg 색 변환을 보존합니다.

[마이그레이션 예제](examples/pixel_animation_smoke.yaml)는 인접한 기존 `pixel-pipeline`의 자료를 참조합니다. 해당 자료는 배포하지 않으며, 강화된 승인 규칙을 적용하려면 검토된 정적 내보내기에서 새 승인 기록을 만들어야 합니다.

Aseprite는 RGBA 왕복 일치, 프레임 수·시간·태그·메타데이터를 검증합니다. 애니메이션 결과도 최종 검토가 필요하며 `game_ready: false`로 남습니다. Pixel Art Fixer는 선택적 복구 정책으로만 유지합니다.

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

[마이그레이션 목록](docs/migration_inventory.json)은 원본 해시와 변경 내용을 기록합니다. bootstrap 스크립트는 기존 저장소와 로컬 벤치마크가 필요한 마이그레이션 도구이며 일반 설치 단계가 아닙니다.
GUI·웹 UI·클라우드 배포·DB·범용 애니메이션 복원은 현재 범위에 포함하지 않습니다.
# M2 Style Intelligence

공통 스타일 후보와 모델별 레시피는 `config/styles/`에서 관리합니다.
프로젝트 Visual SOT → 승인된 프로젝트 Style Pack → 공통 Catalog → 모델 기본값 순으로
선택하며, `style_id`는 선택적 Brief 필드입니다. 사람의 승인과 실생성 근거가 없는
조합은 자동 기본값이 되지 않습니다. 명시한 workflow/model은 기능 검증 후 우선합니다.
Codex와 Claude Code는 동일한 플러그인 스킬을 사용합니다.

[설정·비교 생성·승인 계약](docs/m2/STYLE_INTELLIGENCE.md)을 참고하세요.
