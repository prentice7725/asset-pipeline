# ASSET PIPELINE v0.1 — BOOTSTRAP / MIGRATION DIRECTIVE

## 목적

기존 `pixel-pipeline`에서 검증된 이미지/픽셀/애니메이션 제작 기능을
특정 게임에 종속되지 않는 범용 게임 애셋 제작 도구로 분리한다.

새 repository:

asset-pipeline

Python package / CLI:

assetpipe

이 작업의 목표는 새로운 알고리즘 연구가 아니다.

기존 검증 기능을 재사용하여:

Prompt
Reference Image
Project Documents

중 하나를 입력으로 받고,

적절한 ComfyUI workflow를 선택하여,

PIXEL_STATIC
PIXEL_ANIMATION
NONPIXEL_IMAGE
NONPIXEL_ANIMATION

중 하나의 생산 경로로 라우팅할 수 있는
최소 범용 기반을 만드는 것이 목표다.

---

# 0. HARD SCOPE LOCK

이번 작업에서는 다음을 하지 않는다.

- 새로운 이미지 생성 모델 연구
- 새로운 pixelization 알고리즘 연구
- 새로운 animation reconstruction 방식 연구
- Pixel Art Fixer 추가 연구
- Krea2 LoRA 품질 비교
- GUI 제작
- Web UI 제작
- MCP server 제작
- Cloud 배포
- DB 도입
- 기존 pixel-pipeline 대규모 리팩터링
- 기존 검증 알고리즘 재작성

기존에 통과한 기능은 재구현하지 말고 이식 또는 adapter화한다.

v0.1이 동작하면 즉시 멈춘다.

---

# 1. SOURCE FIRST

작업 시작 전 실제 기존 repository를 확인한다.

우선순위:

1. 현재 `pixel-pipeline` HEAD
2. 기존 config / workflow / tests
3. 실제 ComfyUI 설치 상태
4. 실제 Aseprite 설치 상태

기억이나 이전 보고만으로 구조를 추측하지 않는다.

다음 검증 완료 모듈을 찾아 실제 구현을 기준으로 이식한다.

- ComfyUI Bridge
- Pixel Analyzer
- Safe Refiner
- Resolution Gate
- Aseprite Bridge
- Motion Extractor
- Semantic Keyframe selection
- Character-local Direct Pixelization
- Pixel Gate
- generation/run manifest 관련 코드

현재 동작 중인 원본은 수정하지 않는다.

---

# 2. NEW REPOSITORY

새 repository 구조를 생성한다.

asset-pipeline/

src/assetpipe/
    brief/
    router/
    registry/
    providers/
        comfyui/
        aseprite/
    pipelines/
        pixel_static/
        pixel_animation/
        nonpixel_image/
        nonpixel_animation/
    pixel/
        analyzer/
        refiner/
        resolution/
        direct/
        recovery/
    motion/
        extractor/
        keyframes/
        alignment/
        temporal/
    qa/
    manifests/
    cli/

config/
    workflow_registry.yaml
    workflows/

schemas/

tests/
    unit/
    integration/
    fixtures/

examples/

docs/

README.md
AGENTS.md

Do not copy old run artifacts into the new repository.

---

# 3. CORE CONCEPT — ASSET BRIEF

모든 입력은 바로 ComfyUI로 보내지 않는다.

다음 공통 중간 표현을 만든다.

Asset Brief

입력:

A. direct prompt
B. reference image
C. project/design documents

↓

Asset Brief

↓

Workflow Router

↓

Production Pipeline

Asset Brief 최소 필드:

asset_id
asset_type
output_class
purpose

source:
  type
  paths
  references

identity:
  canonical_traits
  visual_traits

constraints:
  resolution
  transparency
  palette
  silhouette
  style

animation:
  action
  frame_target
  motion_constraints

workflow_preferences

forbidden_elements

unspecified_elements

source_notes

Asset Brief schema를 정의하고 validation을 만든다.

---

# 4. DOCUMENT-DRIVEN ASSET BRIEF

기획문서 기반 생성도 지원한다.

예:

assetpipe brief from-docs ...

단 v0.1에서는 범용 문서 AI 시스템을 새로 만들지 않는다.

Codex가 실제 프로젝트 문서를 읽어
Asset Brief JSON/YAML을 생성할 수 있는
입출력 계약만 제공한다.

원칙:

- 문서에 명시된 내용 = EXPLICIT
- 문서 근거로 필요한 최소 해석 = DERIVED
- 정의되지 않은 항목 = UNSPECIFIED

UNSPECIFIED를 자동으로 canon으로 확정하지 않는다.

기획문서 SSOT 충돌 해결 자체는
각 프로젝트의 SOURCE FIRST 규칙을 따른다.

asset-pipeline이 프로젝트의 설정 정본을 소유하지 않는다.

---

# 5. OUTPUT CLASS

다음 네 개만 지원한다.

PIXEL_STATIC
PIXEL_ANIMATION
NONPIXEL_IMAGE
NONPIXEL_ANIMATION

Router는 Asset Brief의 output_class를 기준으로
생산 경로를 선택한다.

---

# 6. WORKFLOW REGISTRY

ComfyUI workflow를 코드에 hardcode하지 않는다.

`config/workflow_registry.yaml`

형식 예:

workflows:

  anima_pixelate_x4_vae:
    provider: comfyui
    status: ACTIVE

    outputs:
      - PIXEL_STATIC

    tags:
      - character
      - pixel
      - pixel_candidate

    workflow:
      path: config/workflows/anima_pixelate_x4_vae.json

    capabilities:
      text_to_image: true
      reference_image: true
      transparent_output: false

    priority: 100


  anima_base:
    provider: comfyui
    status: ACTIVE

    outputs:
      - NONPIXEL_IMAGE

    tags:
      - character
      - illustration
      - general

    workflow:
      path: config/workflows/anima_base.json


  tomohi:
    provider: comfyui
    status: ACTIVE

    outputs:
      - NONPIXEL_IMAGE

    tags:
      - character
      - anime
      - portrait


  krea2_base:
    provider: comfyui
    status: ACTIVE

    outputs:
      - NONPIXEL_IMAGE

    tags:
      - polished
      - illustration
      - character

실제 workflow filename, model filename, LoRA filename을
현재 ComfyUI 설치에서 확인한다.

추측 금지.

---

# 7. WORKFLOW STATUS

지원 상태:

EXPERIMENTAL
VALIDATED
ACTIVE
REJECTED

Router 기본 선택 대상:

ACTIVE only

VALIDATED는 명시적 요청 시 사용 가능.

EXPERIMENTAL은 자동 선택 금지.

---

# 8. ROUTER

Router 입력:

Asset Brief
+
Workflow Registry

Router 판단 순서:

output_class
capability
tags
status
priority

사용자가 workflow를 명시했으면 사용자 지정 우선.

단 capability가 맞지 않으면 실행하지 않는다.

결과:

route_decision.json

최소 기록:

selected_workflow
output_class
matching_tags
selection_reason
fallback_candidates

---

# 9. PIXEL_STATIC

기본 생산 경로:

Asset Brief
→ Workflow Router
→ pixel candidate generation
→ Pixel Analyzer
→ Safe Refiner
→ Resolution Gate
→ Aseprite Static Master
→ export

현재 기본 후보:

Anima + Pixelate x4 VAE only

단 이것을 true pixel이라고 가정하지 않는다.

Pixel Gate / 기존 validation을 반드시 통과시킨다.

---

# 10. PIXEL_ANIMATION

기존 검증된 primary path를 그대로 연결한다.

Approved Static Master
→ Motion Reference
→ Semantic Frame Selection
→ Character-local Direct Pixelization
→ Static Master Palette / Identity Correction
→ Pixel Gate
→ Aseprite
→ Sprite Sheet

PRIMARY:

CHARACTER_LOCAL_DIRECT

다음은 primary 금지:

- articulated body-part reconstruction
- Static Master pose recreation
- independent Pixel Art Fixer detection

Pixel Art Fixer는:

OPTIONAL_RECOVERY

로만 유지한다.

이번 v0.1에서 추가 실험하지 않는다.

---

# 11. NONPIXEL_IMAGE

생산 경로:

Asset Brief
→ Router
→ selected ComfyUI workflow
→ generation
→ basic image QA
→ export

후보 workflow:

Anima Base
Tomohi
Krea2 Base

Krea2 + LoRA variants는
실제 검증 이후 registry에 추가한다.

이번 작업에서 LoRA 연구는 하지 않는다.

---

# 12. NONPIXEL_ANIMATION

v0.1에서는 구조만 제공한다.

Approved Base Image
→ Motion Reference
→ Frame Extraction
→ Alignment
→ QA
→ Sprite Sheet

새 알고리즘을 만들 필요 없다.

아직 production-ready가 아니면:

SUPPORTED_EXPERIMENTAL

로 표시한다.

---

# 13. PROVIDER LAYER

ComfyUI와 Aseprite를 pipeline 코드에 직접 박지 않는다.

provider interface를 둔다.

예:

ComfyUIProvider
AsepriteProvider

기존 pixel-pipeline Bridge 구현을 최대한 재사용한다.

기능 중복 구현 금지.

---

# 14. MANIFEST

모든 run은 manifest를 생성한다.

run_manifest.json

최소:

asset_id
input_type
asset_brief
output_class

workflow:
  id
  hash
  version
  model
  loras

generation:
  seed
  resolution
  prompt
  negative_prompt
  comfy_prompt_id

pipeline_steps

qa_results

outputs

timestamps

manifest는 재현과 QA를 위한 기록이며
프로젝트의 설정 SOT가 아니다.

---

# 15. CLI

최소 다음 CLI를 제공한다.

## direct prompt

assetpipe create \
  --type pixel-static \
  --prompt "sword wielding fantasy warrior"

## reference image

assetpipe create \
  --type pixel-animation \
  --reference character.png \
  --action walk

## prepared Asset Brief

assetpipe create \
  --brief character_brief.yaml

## routing test

assetpipe route \
  --brief character_brief.yaml

v0.1에서는 자연어 요청 전체를 자동 해석하는
거대한 `auto` agent를 만들지 않는다.

Codex가 Asset Brief를 만들어 CLI를 호출하는 구조로 충분하다.

---

# 16. MIGRATION POLICY

기존 `pixel-pipeline`은 그대로 보존한다.

당장 rename하거나 삭제하지 않는다.

새 `asset-pipeline`이 기존 기능을 정상적으로 대체한다고
확인될 때까지 legacy source 역할을 한다.

Migration 시:

COPY / ADAPT
→ TEST
→ VERIFY

순서로 진행한다.

기존 기능을 깨면서 정리하지 않는다.

---

# 17. TEST FIXTURES

기존 실험 캐릭터를 production 데이터로 넣지 않는다.

다음은 test fixture / benchmark 용도로만 사용한다.

Mushroom Courier
Sword Warrior

용도:

- static pixel validation
- animation direct pipeline regression
- Pixel Gate regression
- palette regression
- Aseprite round-trip regression

---

# 18. FIRST SMOKE — PIXEL

첫 E2E smoke는 기존 검증된 fixture를 사용한다.

입력:

approved Static Master
+
existing walk motion reference

목표:

asset-pipeline의 새 wiring만 검증한다.

새 이미지를 생성하지 않는다.

PASS 조건:

Asset Brief
→ Router
→ existing direct pipeline
→ Pixel Gate
→ Aseprite export
→ manifest

전체가 정상적으로 이어질 것.

기존 결과와 픽셀 결과가 달라지는 경우
새 알고리즘으로 보정하지 말고 migration defect로 취급한다.

---

# 19. SECOND SMOKE — NONPIXEL

현재 설치된 ACTIVE workflow 중 하나를 사용한다.

예:

Anima Base 또는 Krea2 Base

간단한 character image 1장을 생성한다.

목표:

Brief
→ Router
→ ComfyUI
→ output
→ manifest

연결 확인뿐이다.

품질 경쟁은 하지 않는다.

---

# 20. THIRD SMOKE — DOCUMENT BRIEF

작은 fixture markdown을 만든다.

예:

character_test.md

내용:

- fantasy scout
- short brown hair
- blue cloak
- light armor
- dagger
- no heavy armor

Codex가 이 문서를 읽고:

character_test_brief.yaml

을 작성한다.

그 Brief를 Router에 넣는다.

목표:

Project Source
→ Asset Brief
→ Router

까지만 검증한다.

이미지 생성까지 할 필요 없다.

---

# 21. README

README 첫 부분에는 프로젝트 목적을 명시한다.

Asset Pipeline is a workflow-driven production toolkit that turns
prompts, reference images, and project design sources into validated
game-ready visual assets using ComfyUI, deterministic post-processing,
and Aseprite.

README에는 최소 다음을 설명한다.

- supported output classes
- supported input types
- workflow registry
- providers
- pixel pipeline
- basic CLI examples

실험 역사 전체를 README에 넣지 않는다.

---

# 22. LEGACY / EXPERIMENTAL

다음은 production default에서 제외한다.

Articulated Reconstruction
Pixel Art Fixer
old Phase 11/12 pose reconstruction experiments
old failed pixel workflow sweeps

필요한 경우:

docs/research/
또는
experimental/

에 참고 기록만 남긴다.

---

# 23. DEFINITION OF DONE

v0.1 완료 조건:

Repository bootstrap PASS

Workflow Registry PASS

Asset Brief schema PASS

Router PASS

ComfyUI Provider PASS

Aseprite Provider PASS

PIXEL_STATIC wiring PASS

PIXEL_ANIMATION wiring PASS

NONPIXEL_IMAGE wiring PASS

Document → Asset Brief smoke PASS

Pixel E2E smoke PASS

Non-pixel E2E smoke PASS

Tests PASS

README PASS

여기까지 완료하면:

ASSET_PIPELINE_V0_1_BOOTSTRAP_PASS

를 기록한다.

그리고 멈춘다.

---

# 24. STOP RULE

ASSET_PIPELINE_V0_1_BOOTSTRAP_PASS 이후
다음 기능을 자발적으로 추가하지 않는다.

- MCP
- GUI
- LoRA recommender
- workflow editor
- workflow marketplace
- automatic prompt engineer
- video editor
- tileset generator
- audio generator
- Live2D-like rigging
- autonomous art director

추가 요구가 있을 때만 별도 milestone으로 진행한다.

이번 목표는 "게임 제작에 실제 사용할 수 있는 최소 범용 애셋 파이프라인"이다.

도구를 만들기 위한 도구를 더 만들지 않는다.