# Agent Recipe Selection Guide v1

상태: STYLE MENU v1 운영 라우팅 / 생성 자산 REVIEW_REQUIRED.
게임의 ACTIVE/SOT와 승인 아트가 정체성·복장·장비·실루엣·출력 계약을 결정한다. 메뉴는 화풍과 모델 선택을 제공하며 Golden/Aseprite 승인이나 게임 적합성을 대신하지 않는다.

## 기본 진입점

1. 실제 게임 SOT를 읽고 `art_style`을 선택한다. family는 탐색용이며 recipe/model 선택 단위는 독립된 STYLE-101~124 24종이다.
2. [config/styles/style_menu_v1.yaml](../../config/styles/style_menu_v1.yaml)에서 primary_model, binding, recipe, workflow, known_limitations를 읽는다.
3. [실제 exemplar/failure 메뉴](../../research/style_catalog/style_menu_v1/STYLE_MENU_v1.md)의 원본 이미지를 확인한다. 대표 이미지와 SHA는 저장소 내부 경로로 연결돼 있다.
4. 기존 Brief/PromptSpec → model-specific compiler → 등록 workflow를 사용한다. 완성 프롬프트를 사람이 따로 작성하거나 우회하지 않는다.
5. 생성 요청과 예산이 실제 승인된 경우에만 설치 모델·hash·VAE·encoder·workflow·라이선스·queue를 점검하고 generation을 실행한다. 메뉴 선택 또는 이 가이드만으로 생성 예산이 승인되지 않는다.
6. 원본, 생성 파라미터, compiled prompt, workflow, route decision, manifest, QA와 실패를 보존한다. known limitations를 검토한 뒤 실제 human review를 받는다.

```text
게임 SOT → art_style (family는 탐색만)
         → STYLE MENU v1 → primary_model + recipe + workflow
         → model-specific compiler → generation
         → known limitations + QA + human review
```

## 모델 배치

- Krea2 Turbo (`krea2_base` registry alias): 20 styles.
- Anima Base rebuilt: STYLE-103 `retro_sci_fi_anime`, STYLE-109 `manga_screentone_noir`, STYLE-119 `graphic_neon_cyberpunk`.
- STYLE-117 `flat_vector_editorial`: primary unresolved. `style_selection_policy: style_fidelity`는 Krea2, `character_readability`는 Anima Turbo를 선택한다. 정책 미지정은 차단된다.
- Anima Turbo: 기본 화풍 경쟁군에서는 optional/experimental. 117의 명시적 readable-face 정책으로 선택 가능하다.
- runner_up은 비교 참고 정보다. 자동 fallback/retry가 아니다. 승인된 실행별 override 없이 메뉴 binding과 충돌하면 fail-closed한다. STYLE 및 정체성 잠금은 override에서도 유지한다.

## Manual / Rescue Override

STYLE MENU primary model is an evidence-informed default for the evaluated fixtures and style-fidelity goals, not a universal subject-capability lock or production approval.

승인된 USER_MANUAL은 해당 자산·실행에서 모델 기본값보다 우선한다. model_override는 model_profile, workflow_override는 workflow ID이며 executor와 provider는 독립적이다. `krea2` / `krea2_base`를 구별한다. 승인 파일·사유·원래 선택·실제 선택·fingerprint를 기록하고 모든 출력은 REVIEW_REQUIRED를 유지한다.

subject_domain은 선택 필드이며 asset_type에서 추론하지 않는다. SUBJECT_RESCUE는 실제 원본/검토 기록의 해시와 승인된 반복 실패 근거를 요구한다. `assetpipe rescue-plan`은 최대 3개 후보의 기존 compiler/recipe 호환성을 검사하며 생성하지 않는다. 생성에는 별도 exploration 승인 및 영구 예약되는 1회 예산 승인이 필요하다. 자동 fallback/retry와 global primary 변경은 없다.

Grok/Codex/Claude executor 연결은 현재 미구현이며 EXECUTOR_UNAVAILABLE로 차단된다. Grok용 STYLE-103 recipe도 없으므로 기존 recipe gate에서 차단된다. 로컬 GREEN은 실제 그림 품질·화풍 호환 승인 근거가 아니다.

실제 fixture 범위, 승인 JSON, SOT 예외, 기능·예산·감사 계약과 SKY RENDEZVOUS 후속 변경안은 [Manual / Rescue Override 상세](../../docs/style_menu/MANUAL_RESCUE_OVERRIDE.md)를 따른다. Google Drive SOT는 별도 소유자 검토·수정이 필요하다.

## SOT / Brief 예시

프로젝트 SOT는 실제 source를 지정한다. 기존 게임 문서를 자동 수정하지 않는다.

```yaml
art_style: retro_sci_fi_anime
source: game/ACTIVE_SOT.yaml
```

미해결 스타일의 목적 선택:

```yaml
art_style: flat_vector_editorial
style_selection_policy: character_readability
source: game/ACTIVE_SOT.yaml
```

생성 없이 실제 라우팅 확인:

```powershell
assetpipe route --brief research/style_catalog/style_menu_v1/examples/retro_sci_fi_anime.json --output workspace/menu_route.json
```

## 증거와 제작 한계

24 styles × 3 models × 3 seeds = 216장 실제 생성 증거. 화풍 우세는 Krea20 / Base3 / unresolved1 / Turbo0. [메뉴 JSON](../../research/style_catalog/style_menu_v1/style_menu_v1.json)은 style fidelity와 production reliability를 분리한다. [고정 evidence archive](../../research/style_catalog/style_menu_v1/evidence_archive.json)는 원본 216장, 원본 SHA, 역사적 run records와 이전 판정을 연결한다.

나침반 좌우, camera drift, crop, 추가 인물은 화풍 승자 판정을 자동 HOLD시키지 않는다. 하지만 해당 생산 결함은 경고로 남고, 기술 QA나 모델 배치만으로 실제 자산을 승인하지 않는다. 세 seed는 관찰된 변동만 보여준다. 동일 seed 재실행 repeatability는 NOT_MEASURED. 새 인물·소품·배경·게임 표시 크기에서 품질을 보장하지 않는다.

운영 메뉴 선택은 사용자가 승인한 모델 binding을 명시 선택으로 전달한다. registry의 EXPERIMENTAL 상태와 역사적 recipe/style 승인 상태를 APPROVED로 조작하지 않는다. 모든 기존 기술 및 human review gate를 유지한다. 픽셀 실험은 이 NONPIXEL_IMAGE 메뉴의 범위가 아니다.

## Research/history 경계

`CAND-*`, 옛 STYLE-001~012, `candidates_v0.yaml`, `nonpixel_prompt_research_v0.yaml`, `scripts/style_menu.py`와 `scripts/nonpixel_research.py`는 historical research/evidence 용도다. production agent는 이 자료를 기본 선택 계약으로 먼저 읽지 않는다. 역사적 Anima R1/R2/R3 compiler fixture는 증거 검증을 위해 그대로 유지한다.

이전 가이드는 [history/v0.1](../../docs/style_menu/history/AGENT_RECIPE_SELECTION_GUIDE_v0.1.md)에 보존돼 있다. 과거 연구 지시서는 현재 생성 승인이나 운영 recipe를 대체하지 않는다.
