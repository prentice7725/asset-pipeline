# ASSET PIPELINE PLUGIN M0
# Thin MCP Adapter + Plugin Creator Packaging

## PURPOSE

`asset-pipeline`의 검증된 core 기능을 ChatGPT와 Codex에서
고수준 작업 단위로 호출할 수 있도록 Plugin 계층을 추가한다.

이 작업은 asset-pipeline을 재구현하는 작업이 아니다.

Architecture:

ChatGPT / Codex
      ↓
Asset Pipeline Plugin
      ↓
Thin MCP Adapter
      ↓
assetpipe Python API / CLI
      ↓
ComfyUI / deterministic pipeline / Aseprite

PLUGIN = interface / orchestration layer
ASSET-PIPELINE = production engine

이 책임 경계를 절대 섞지 않는다.


# 0. PRECONDITION

먼저 현재 `asset-pipeline` repository와 HEAD를 실제로 확인한다.

다음 조건이 충족되어야 작업을 계속한다.

- Asset Brief schema exists
- Workflow Registry exists
- Router works
- ComfyUI provider works
- Aseprite provider works
- PIXEL_STATIC pipeline works
- PIXEL_ANIMATION pipeline wiring works
- NONPIXEL_IMAGE works
- manifests exist
- tests pass

아직 `ASSET_PIPELINE_V0_1_BOOTSTRAP_PASS` 상태가 아니라면
Plugin 작업을 시작하지 않는다.

부족한 항목을 보고하고 멈춘다.


# 1. HARD SCOPE LOCK

이번 milestone에서 만들지 않는다.

- 새로운 이미지 생성 알고리즘
- 새로운 pixelization 알고리즘
- 새로운 ComfyUI workflow
- Krea2 LoRA 연구
- GUI
- 독립 Web UI
- DB
- cloud service
- user account system
- workflow editor
- prompt marketplace
- autonomous art director
- public plugin publishing
- billing
- remote GPU support

목표는 단 하나:

"기존 asset-pipeline을 Plugin에서 안전하게 호출한다."


# 2. REPOSITORY STRUCTURE

기존 repository 안에 Plugin 계층을 추가한다.

asset-pipeline/

  src/assetpipe/
      ...

  integrations/
      mcp/
          server/
          tools/
          schemas/
          tests/

  plugin/
      instructions/
      references/
      manifests/
      README.md

  docs/
      plugin/

core production code를 `plugin/`으로 복사하지 않는다.

`integrations/mcp`는 thin adapter만 포함한다.


# 3. MCP RESPONSIBILITY

MCP server는 다음만 한다.

- request validation
- assetpipe API 호출
- run 상태 조회
- 결과 metadata 반환
- output file reference 반환

다음은 MCP에서 구현하지 않는다.

- workflow routing algorithm
- pixel analyzer
- pixel refiner
- image processing
- frame extraction
- palette projection
- Aseprite manipulation
- ComfyUI node graph construction

모든 production logic은 기존 `assetpipe`를 호출한다.


# 4. MCP TOOL SURFACE

M0에서는 tool을 최소화한다.

다음 6개만 구현한다.


## 4.1 asset_capabilities

Purpose:

현재 asset-pipeline이 무엇을 지원하는지 반환한다.

Return:

- supported output classes
- registered ACTIVE workflows
- providers
- supported input types
- supported animation actions
- optional recovery features
- environment readiness


## 4.2 asset_build_brief

Input:

- direct request text
- optional source document paths
- optional reference image
- optional requested output type

Output:

validated Asset Brief

Important:

프로젝트 기획문서를 참조하는 경우
source information을 명시적으로 보존한다.

MCP가 설정을 창작하지 않는다.


## 4.3 asset_route

Input:

Asset Brief

Output:

- selected pipeline
- selected workflow
- reason
- required capabilities
- missing requirements
- fallback candidate

실제 generation은 수행하지 않는다.


## 4.4 asset_generate

Input:

validated Asset Brief
or
brief file reference

Action:

Asset Brief
→ Router
→ registered workflow
→ requested production pipeline

Output:

- run_id
- status
- manifest
- generated outputs
- QA result

긴 작업 내부 세부 단계를 MCP tool 여러 개로 노출하지 않는다.


## 4.5 asset_continue_animation

Purpose:

이미 승인된 Static Master 또는 Base Image에서
animation/sprite 제작을 이어간다.

Input:

- asset/run reference
- action
- output class
- optional animation constraints

Examples:

walk
idle
attack

PIXEL_ANIMATION이면 기존 primary path만 사용한다:

Approved Static Master
→ Motion Reference
→ Semantic Frames
→ Character-local Direct
→ Identity/Palette correction
→ Pixel Gate
→ Aseprite
→ Sprite Sheet


## 4.6 asset_inspect_run

Input:

run_id

Output:

- current status
- route
- workflow
- manifest
- QA summary
- produced files
- review-required items

이 tool은 read-only다.


# 5. DO NOT EXPOSE LOW-LEVEL TOOLS

다음 같은 MCP tools를 만들지 않는다.

comfy_queue_prompt
comfy_set_node
comfy_upload_image
aseprite_paint_pixel
aseprite_move_region
pixel_replace_color
extract_frame_17

Plugin user에게 low-level production implementation을 노출하지 않는다.

Plugin은 다음 수준으로 사용되어야 한다.

"캐릭터를 만들어라"
"이 캐릭터 walk sprite를 만들어라"
"기획문서에서 캐릭터 브리프를 만들어라"


# 6. SOURCE-DRIVEN GENERATION

Plugin은 세 가지 input mode를 지원한다.

DIRECT_PROMPT

REFERENCE_IMAGE

PROJECT_SOURCES


## PROJECT_SOURCES RULE

기획문서 기반 요청에서는:

SOURCE
→ Asset Brief
→ Router
→ Production

순서를 반드시 지킨다.

예:

"이 게임 기획문서를 보고 주인공 픽셀 캐릭터 만들어"

Plugin은 먼저:

1. 관련 source 확인
2. canonical character facts 추출
3. Asset Brief 생성
4. unspecified 항목 표시
5. output type 결정
6. Router 실행

후 generation을 수행한다.

기획문서가 asset-pipeline 내부 SOT가 되는 것은 아니다.

각 프로젝트가 자신의 SOT를 소유한다.


# 7. PLUGIN INSTRUCTIONS

Plugin instruction은 긴 production algorithm 설명서가 되어서는 안 된다.

다음 행동 원칙만 포함한다.

- Source First
- Build Asset Brief before generation
- Use Workflow Registry
- Prefer ACTIVE workflows
- Respect user-selected workflow
- Never invent missing canon
- Never bypass QA
- Pixel output must pass Pixel Gate
- Approved Static Master is required for pixel animation
- Character-local Direct is the primary pixel animation path
- Do not use experimental recovery automatically
- Return run/output/review status clearly

Production implementation 세부사항은 asset-pipeline 문서가 담당한다.


# 8. PLUGIN REFERENCE FILES

Plugin에 필요한 reference material만 포함한다.

추천:

plugin/references/
    ASSET_BRIEF_SCHEMA.md
    OUTPUT_CLASSES.md
    ROUTING_RULES.md
    PIXEL_PIPELINE_CONTRACT.md
    WORKFLOW_STATUS_RULES.md

전체 코드베이스나 연구 기록을 reference로 넣지 않는다.

다음은 Plugin reference에서 제외한다.

- Phase 11/12 experiment history
- failed workflow sweeps
- Pixel Art Fixer research logs
- benchmark raw outputs
- Mushroom/Sword run artifacts

Plugin에게 필요한 것은 현재 production contract뿐이다.


# 9. MCP TRANSPORT

우선 local development용 MCP server를 만든다.

assetpipe core와 같은 로컬 머신에서 실행한다.

ComfyUI:
local

Aseprite:
local

assetpipe:
local

따라서 production path에서
원격 업로드를 새로 도입하지 않는다.

Server start/stop 방법을 README에 기록한다.


# 10. SECURITY BOUNDARY

MCP server가 임의 shell 실행 도구가 되면 안 된다.

금지:

- arbitrary command execution
- arbitrary filesystem delete
- arbitrary Python execution
- arbitrary ComfyUI JSON execution supplied by model
- arbitrary executable path supplied by model

허용:

- registered workflows
- validated assetpipe commands
- configured source/output roots
- explicit known asset references

Filesystem path는 configured roots 내부로 제한한다.


# 11. ASYNC / LONG RUN BEHAVIOR

이미지/영상 생성은 시간이 걸릴 수 있다.

tool timeout 안에 전체 작업이 끝나야 한다고 가정하지 않는다.

`asset_generate`는 내부 assetpipe run을 시작하고
가능하면 완료 결과를 반환한다.

장기 실행이 필요한 현재 구현이라면:

run_id
status

를 반환하고,

`asset_inspect_run`

으로 상태를 조회할 수 있게 한다.

MCP 내부에 별도 job system을 새로 만들지 않는다.

기존 assetpipe run model을 재사용한다.


# 12. OUTPUT CONTRACT

tool 결과는 모델이 해석하기 쉬운 structured response를 사용한다.

예:

{
  "run_id": "...",
  "status": "REVIEW_REQUIRED",
  "asset_id": "...",
  "output_class": "PIXEL_STATIC",
  "workflow_id": "...",
  "qa": {
    "pixel_gate": "PASS"
  },
  "outputs": [...],
  "review_items": [...]
}

불필요하게 대량 로그를 MCP 응답에 싣지 않는다.

상세 로그는 manifest/file reference로 제공한다.


# 13. PLUGIN CREATOR PACKAGING

MCP server smoke가 통과한 뒤에만 Plugin packaging을 한다.

가능한 경우 공식 Plugin Creator를 사용하여
지원되는 manifest 구조를 scaffold한다.

Plugin name:

Asset Pipeline

Description:

Create validated game-ready visual assets from prompts,
reference images, or project design sources using registered
local production workflows.

Plugin은 MCP app + reusable instructions/reference files 조합으로 구성한다.

manifest 형식을 기억으로 추측하지 않는다.

현재 Plugin Creator가 생성한 구조를 따른다.


# 14. CODEX / CHATGPT BEHAVIOR EXAMPLES

Plugin이 다음 요청을 처리할 수 있어야 한다.


### Example A

"검 든 전사 픽셀 캐릭터 만들어."

Expected:

DIRECT_PROMPT
→ Asset Brief
→ PIXEL_STATIC
→ Router
→ Pixel Workflow
→ QA
→ output


### Example B

"이 캐릭터로 walk sprite sheet 만들어."

Expected:

REFERENCE_IMAGE / existing asset
→ PIXEL_ANIMATION
→ approved Static Master check
→ animation pipeline


### Example C

"프로젝트 문서를 읽고 리안을 만들어."

Expected:

PROJECT_SOURCES
→ source extraction
→ Asset Brief
→ Router
→ generation


### Example D

"Krea2로 이 캐릭터 원화 만들어."

Expected:

user workflow preference
→ capability validation
→ NONPIXEL_IMAGE
→ Krea2 workflow

사용자 지정 workflow는 자동 Router보다 우선한다.


# 15. REVIEW GATES

Plugin은 QA status를 숨기지 않는다.

예:

PASS
REVIEW_REQUIRED
BLOCKED
FAILED

REVIEW_REQUIRED를 자동 PASS로 바꾸지 않는다.

예:

Pixel Gate PASS
but
identity review required

이면:

REVIEW_REQUIRED

그대로 반환한다.


# 16. PLUGIN M0 SMOKE TESTS

다음 네 테스트만 수행한다.


## Smoke A — Capabilities

Plugin
→ MCP
→ asset_capabilities

PASS 조건:

실제 registry와 동일한 정보 반환.


## Smoke B — Non-pixel image

Prompt
→ Asset Brief
→ Router
→ one ACTIVE nonpixel workflow
→ ComfyUI
→ output

품질 비교 금지.


## Smoke C — Pixel fixture animation

기존 검증 fixture 사용.

Approved Static Master
+
existing Motion Reference

→ existing pixel animation pipeline
→ output

새 motion generation은 하지 않는다.

기존 결과와 regression 여부만 확인한다.


## Smoke D — Document route

fixture design document
→ Asset Brief
→ Router

generation 생략 가능.

목표:

기획문서 → 제작 브리프 연결 확인.


# 17. TEST REQUIREMENTS

최소 테스트:

- schema validation
- invalid path rejection
- unknown workflow rejection
- EXPERIMENTAL workflow auto-selection rejection
- user workflow override
- missing Static Master block
- tool argument validation
- route response structure
- assetpipe API adapter
- MCP tool smoke

기존 assetpipe test suite도 계속 PASS해야 한다.


# 18. DOCUMENTATION

추가:

docs/plugin/ARCHITECTURE.md
docs/plugin/MCP_TOOL_CONTRACT.md
docs/plugin/LOCAL_SETUP.md
docs/plugin/TESTING.md

README에는 짧게:

ChatGPT/Codex Plugin
→ MCP
→ assetpipe

연결 구조만 추가한다.


# 19. DEFINITION OF DONE

다음이 모두 충족되면 완료:

- assetpipe core unchanged or minimally adapted
- MCP server starts
- 6 MCP tools available
- arbitrary execution unavailable
- registry remains source of workflow truth
- Plugin package created
- Plugin Creator validation passes
- capability smoke passes
- nonpixel smoke passes
- pixel fixture smoke passes
- document route smoke passes
- assetpipe regression tests pass
- Plugin/MCP docs complete

Final status:

ASSET_PIPELINE_PLUGIN_M0_PASS


# 20. STOP RULE

`ASSET_PIPELINE_PLUGIN_M0_PASS` 이후 멈춘다.

다음은 만들지 않는다.

- custom Plugin UI
- image gallery UI
- approval buttons
- remote server
- public publication
- marketplace submission
- multi-user support
- cloud storage
- workflow recommendation AI
- LoRA recommender
- automatic benchmark farm
- additional MCP tools

M0의 목적은:

"ChatGPT/Codex에서 기존 asset-pipeline을 안정적으로 호출할 수 있다."

여기까지다.