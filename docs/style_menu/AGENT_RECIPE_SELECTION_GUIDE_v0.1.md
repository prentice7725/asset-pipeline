# Codex/Claude 화풍 메뉴판 사용 계약 v0.1

상태: 후보 메뉴 12종 / 외부 참조만 확보 / 제작 레시피 **NOT_VERIFIED**.
정본 우선순위: 게임 Google Drive ACTIVE/SOT → 게임의 승인 아트 → Asset-Pipeline 참고 메뉴 → 내부 실행/검증 상태. 기존 `asset-production`의 출력별 QA와 명시적 Human Golden 승인은 유지.

## 사용 사례

- SF 사이버펑크 콘셉트를 설계한다 → STYLE-001(레드 네온 누아르), STYLE-002(앰버 블루 사이버 누아르), STYLE-012(펑크 지면) 후보를 원본 이미지로 비교한다.
- 판타지 치비 SD를 설계한다 → STYLE-004(동화책 구아슈), STYLE-005(파스텔 치비 픽셀 후보), STYLE-011(클레이 장난감 치비) 후보를 본다. **셋은 서로 다른 재질/파이프라인 가설**이며 '치비'라는 한 단어로 결합하지 않는다.
- 현대 일상물 → STYLE-008(평면 만화), STYLE-009(복고 그래픽) 후보.
- 중세 판타지 → STYLE-003(고딕 애니), STYLE-006(잉크 동화책), STYLE-007(다크 판타지 회화) 후보.

위 목록은 **탐색 색인**이지 품질이나 사용 적합성을 검증한 순위가 아니다. 메뉴 번호는 장르 번호가 아니라 고정 화풍 ID이며 동일 메뉴가 여러 장르에서 재사용될 수 있다.

## 비픽셀 집중 트랙 / PIXEL HOLD (2026-10-04)

Anima Base와 Krea2 Turbo의 **11개 비픽셀 스타일**을 [모델별 레시피 연구](NONPIXEL_PROMPT_RESEARCH_v0.1.md)에서 분리 설계했다. 검증/생성 단계에서는 STYLE-001/004/006/008부터 비교하며 STYLE-005와 나머지 PIXEL_STATIC은 HOLD. Krea2 RAW/Anima Turbo/Aesthetic-LoRA는 설치 확인과 분리 효과 시험 전까지 추측으로 기본 라우팅하지 않는다. Codex/Grok CLI는 스타일별 경쟁이 아니라 기존 2026-10-01 이미지 생성 성공 실물 증거 점검이 우선이다.

## 모델·LoRA·VAE·레시피 조합

메뉴에서 STYLE-005를 선택한 경우의 *실험 가설*:

```yaml
project_source: "게임 ACTIVE/SOT의 실제 문서 URL 또는 경로"
menu_style: STYLE-005
source_style_id: 6d67e449de82
evidence_state: EXTERNAL_PREVIEW_ONLY
target_output_class: PIXEL_STATIC   # 요구사항만 표시; 아래 모델과 직접 일치하지 않음
target_native_frame: [32, 32]      # 이 크기가 필요할 때 프로젝트 SOT 확인
candidate_workflow: krea2_base
candidate_output_class: NONPIXEL_IMAGE
candidate_model: krea2_turbo_fp8_scaled.safetensors
candidate_text_encoder: qwen3vl_4b_fp8_scaled.safetensors
candidate_vae: qwen_image_vae.safetensors
candidate_loras: []
preset: concept_art
adapter: krea2
upstream_style_prompt: "pixel art, kawaii aesthetic, pastel color palette, 8-bit retro style, chibi character design, clean isolated sprite, nostalgic game asset"
status: EXPERIMENT_REQUIRED_NOT_32PX_APPROVED
```

여기에는 중요한 충돌이 있다: `krea2_base`는 `NONPIXEL_IMAGE`용으로 등록되어 있다. **화풍이 픽셀이라는 말만으로 32px 게임 애셋의 PIXEL_STATIC 경로로 승격하거나 Pixel Gate를 우회해서는 안 된다.** 사용자는 외부 미리보기를 평가하고 32px 별도 검증 워크플로를 요구할 수 있다.

레시피 구성 요소는 고정/수정 가능 영역을 분리한다.

| 레이어 | 출처 | 에이전트 수정 조건 |
|---|---|---|
| 인물 정체성·복장·장비·색상 | 게임 ACTIVE/SOT | 승인 전 임의 변경 **금지** |
| 화풍 기본 선언 | 메뉴 source prompt / 외부 이미지 | 스타일 선택 후보. 게임 SOT로 오인 금지 |
| 모델/워크플로 | 실제 registry + 설치 상태 | 변경 시 별도 후보 생성 및 재검증, silent fallback 금지 |
| LoRA/VAE/Refiner | 설치된 파일·모델 호환 정보 | 신규 조합 시 **새 recipe ID**, 각 요소의 라이선스/해시/효과 확인 |
| 팔레트·선·명암·질감·배경 위계 | 선택 화풍과 프로젝트 SOT | 바꾸는 축을 하나씩 기록해 비교, 고정된 정체성 보존 |
| 샘플러/steps/CFG/seed | 실제 사용 workflow graph/preset | 별도 파라미터 실험이 아닌 경우 고정 |
| 최종 출력·앵커·알파 | 게임별 런타임 계약 | 프로젝트가 결정, 생성 소스 해상도와 구별 |
| 리뷰/승인 | 실제 원본·기술 Gate·human art review | 자동 PASS/Golden 승격 금지 |

## 성공 사례의 '메뉴' 승격을 위한 실험 기준

1. **외부 예시 확인:** 출처 `source_id`, 원본 prompt, image path를 pinned commit에 맞춰 확인. 외부 이미지 색/형태 자체를 우리 모델 테스트 결과로 주장 금지.
2. **로컬 재현:** 동일 계열 Krea2 Turbo 실제 설치 모델·hash·workflow·graph hash·정확한 prompt·seed, 생성 원본을 보존한다. 디폴트 CFG가 공식 안내와 다른 경우 차이를 기록하고 한 번에 튜닝하지 않는다.
3. **피사체 전이:** 동일 화풍으로 사람 전신, 장면 배경, 소품을 각각 생성한다. 피사체가 바뀌면 화풍이 사라지는지 기록한다. 외부 prompt에 박힌 `eyewear`, `character` 등은 프로젝트 identity를 오염시키지 않도록 따로 다룬다.
4. **모델 비교:** Anima에 복사/붙여넣기하는 것이 아니라 Anima adapter에 맞춰 **같은 의미 요구**를 변환한다. 같은 raw prompt/시드가 공정 비교 근거가 아님.
5. **게임 실용성:** 고유 캐릭터 실루엣, 장비 관계, 중성 배경 및 실제 표시 해상도. 픽셀은 반드시 별도 native 32px/64px 평가, 알파/앵커/PNG QA까지 포함.
6. **검증 레벨 승격:** `EXTERNAL_PREVIEW_ONLY` → `LOCAL_GENERATED` → `MULTISUBJECT_REVIEWED` → `RECIPE_REPRODUCED` → `GAME_SIZE_TESTED` → 프로젝트 `APPROVED`. 에이전트가 임의로 중간 단계를 생략할 수 없다.

**반복 실험의 최소 근거:** 최초 16-cell pilot은 후보를 걸러내는 용도이며, 특정 화풍을 추천하려면 살아남은 후보마다 추가 seed와 추가 피사체, 누락 없는 원본 리뷰가 필요하다. 이 계획은 현재 새 생성 비용/요청을 승인하는 명령이 아니다.

## 코드와 실제 실행 방법

```powershell
# 메뉴 구조 검사와 원본 스타일 확인(이미지 생성 없음)
python scripts/style_menu.py check

# 번호·이미지가 있는 Markdown 메뉴 다시 생성(이미지 생성 없음)
python scripts/style_menu.py render --output docs/style_menu/NUMBERED_CANDIDATE_MENU_v0.1.md

# 첫 pilot 검증 계획만 준비(기본 16 cells, 이미지 생성 없음)
python scripts/style_menu.py plan --output workspace/style_menu/pilot_plan.json
```

실제 생성은 사용자가 실행 중인 Windows ComfyUI의 정확한 설치 그래프/모델 해시를 확인한 후 기존 CLI/스킬의 승인 정책에 따라 진행한다. 위 세 명령은 외부 모델을 호출하지 않고 이미지 품질을 평가하지도 않는다.

## 적용 제한 및 원본 권리

화풍 정보 출처는 [ThetaCursed Style Explorer](https://kreastyles.thetacursed.com/)이다. 프로그램 소스가 MIT로 공개돼 있다는 사실만으로 개별 생성 미리보기 이미지의 사용·재배포 및 원본 모델 가중치 상업권을 포괄적으로 승인하지 않는다. 메뉴는 원본 이미지로 **링크**하며 실물 재배포하지 않는다. 작품별 SOT에 특정 원본 이미지를 Golden으로 자동 등재하지 않는다.
