# Asset Pipeline

프롬프트, 레퍼런스 이미지, 프로젝트 기획문서를 바탕으로 게임용 이미지와 효과음 후보를 만드는 Python CLI 도구입니다. ComfyUI 생성, 후처리·검증, Aseprite 내보내기를 연결합니다.

**생성 결과는 자동 승인하지 않습니다.** 픽셀 캐릭터는 검증을 통과한 후보만 검토 후 Static Master로 승인하며, SFX도 기본 검증 후 직접 들어봐야 합니다. 실패한 단계는 중단하고 기록을 보존합니다.

## 지원 기능과 현재 상태

| 출력 유형 | 동작 |
| --- | --- |
| `PIXEL_STATIC` | 픽셀 후보 생성 → 분석 → 안전한 알파 처리 → Pixel Gate → 해상도 검토 → Aseprite 내보내기 → 명시적 승인 |
| `PIXEL_ANIMATION` | 승인된 Static Master와 기존 검토된 모션을 사용한 8프레임 걷기 제작, 팔레트·Pixel Gate 검증, Aseprite 내보내기 |
| `NONPIXEL_IMAGE` | ComfyUI 이미지 생성과 기본 QA. 최종 시각 검토 필요 |
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
