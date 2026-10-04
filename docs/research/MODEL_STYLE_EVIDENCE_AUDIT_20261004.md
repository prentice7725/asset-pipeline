# MODEL / WORKFLOW / STYLE EVIDENCE AUDIT — 2026-10-04

> **판정: INVENTORY_PARTIAL / QUALITY_CHARACTERIZATION_NOT_ESTABLISHED / BENCHMARK_NOT_VALIDATED**
>
> 범위: GitHub `prentice7725/asset-pipeline`의 2026-10-04 `main` 상태에서 확인 가능한 코드·레지스트리·체크인된 결과 설명서. 로컬 Windows ComfyUI/설치 모델 디렉터리와 ignore된 실제 이미지 원본은 이번 원격 감사에서 접근하지 못했다. 모델 시각적 우열, 전체 실제 작동, 최신 모델 파일 상태를 검증했다고 주장하지 않는다.
>
> 목적: 모델·워크플로의 **등록**, **현재 기계적 지원**, **제작사 주장**, **실제 생성 증거**, **예술적 실용성**을 분리하여 기존 취급 설명서의 과대해석을 차단한다. 새 이미지 생성 0건, 모델/워크플로/품질 Gate 변경 0건.

## A. 최초 주장 정정

`docs/ASSET_PIPELINE_MODEL_STYLE_HANDBOOK_v0.1.md`는 **미완성 조사 노트**다. 프로젝트가 모델이나 스타일을 선택할 근거로 단독 사용하면 안 된다. 기존 문서에서 모델 용도로 기술한 '인물/판타지/그래픽' 등은 워크플로 tags 또는 제작사 포지셔닝에 따른 **연구 대상 후보**일 뿐 측정된 장점이 아니다. M2에서 `TESTED`로 기록된 것은 이미지 생성·기술 QA 근거이지 미술 품질 검증이나 프로젝트 승인 기록이 아니다.

## B. 등록 범위 전수 목록

`config/workflow_registry.yaml`에 명명된 **9개 워크플로**:

| ID | 출력 | 레지스트리 상태 | 무엇이 아직 증명되지 않았나 |
|---|---|---|---|
| `anima_base` | NONPIXEL_IMAGE | ACTIVE | 품목별 강점, 레퍼런스 재현, 최적 설정, 실제 프로젝트 적용 |
| `krea2_base` | NONPIXEL_IMAGE | ACTIVE | 동일 항목의 통제 비교, Native Negative를 요구하는 사용처 |
| `anima_pixelate_x4_vae` | PIXEL_STATIC | ACTIVE | 32px 제작 적합성; 2026-10-01의 8/8 Pixel Gate FAIL과 충돌하는 '추천' 해석 금지 |
| `tomohi_character` | NONPIXEL_IMAGE | EXPERIMENTAL | 미형 편향, 일관성, Aesthetic/LoRA의 정량·정성 기여 분리 |
| `minimax_character_motion_reference` | PIXEL_ANIMATION | ACTIVE | 일반 애니메이션 성공 및 임의 캐릭터 모션 적용. 승인된 Static Master 선행 필수 |
| `nonpixel_motion_contract` | NONPIXEL_ANIMATION | EXPERIMENTAL | 일반화된 Nonpixel 애니메이션 실생산 완료; 미지원 상태를 성공으로 쓰지 말 것 |
| `audio_stable_audio_3_medium` | SFX | ACTIVE | 사람의 청감 승인·게임 믹싱 적합성은 기술 QA와 별도 |
| `codex_imagegen` | NONPIXEL_IMAGE | EXPERIMENTAL / explicit_only | 재현성·모델 선택 통제·표현 강점. M1 E2E는 특정 생성 성공만 입증 |
| `grok_imagine` | NONPIXEL_IMAGE | EXPERIMENTAL / explicit_only | 편집·참조 기능의 end-to-end 성공·표현 강점. M1 E2E는 일부 생성 성공만 입증 |

`config/model_profiles.yaml`의 **6개 프롬프트 프로파일**은 anima-base, anima-pixel, anima-tomohi, krea2, codex-imagegen, grok-imagine이다. 여기서 profile은 독립 모델 가중치 수가 아니다. 등록 수가 설치된 체크포인트·LoRA·VAE의 실물 인벤토리 수나 최신 상태를 의미하지도 않는다.

### 모델/버전 조사를 빠뜨린 부분

- Anima **Base / Aesthetic / Turbo**: 공식 자료가 서로 다른 유도 특성과 기본값을 설명하지만, 실제로 같은 품목에 대한 3종 비교가 없다. Turbo는 현재 이 프로젝트의 지정 생산 workflow에 별도로 등록되어 있지 않다.
- Krea 2 **Raw / Turbo**: Raw를 별도 후보로 등록·비교하지 않았다. 현재 등록 `krea2_base`는 Turbo 기준이다. 원 저작자의 장단점 설명은 참고사항이지 사용 중인 FP8 체크포인트와 설정에서의 측정이 아니다.
- Pixel 관련 파생: Anima Pixelate x4 VAE, Krea2 Pixel64 LoRA+Refiner는 **서로 다른 실제 논리 해상도와 후처리**를 가진 별개 가설이다. 검증 결과를 섞을 수 없다.
- Codex/Grok 내부 모델/버전이 고정·식별되지 않는 경로에서 '스타일 품질 우위'를 재현 가능한 실험처럼 단정하지 않는다.
- 정확한 로컬 체크포인트/LoRA·VAE 설치 인벤토리, full hash와 설정/라이선스 매칭은 이 감사에서 **미확인**이다.

## C. 스타일 카탈로그 및 레시피

`config/styles/catalog.yaml`: **7개 스타일 키**
`graphic-risograph`, `ink-storybook`, `anime-cel`, `clean_anime_cel`, `storybook_gouache`, `painterly_fantasy`, `limited_palette_pixel`.

`config/styles/model_recipes.yaml`: **3개 스타일 그룹 × 5개 워크플로 = 15개 조합**. 기록된 상태 **TESTED 2**, **UNTESTED 13**. TESTED인 것은 `graphic-risograph` × `anima_base` / `krea2_base`의 생성 흔적이며 미술적 실용성의 우열 점수는 없다. 일반 카탈로그의 상태와 개별 레시피의 생성 테스트 상태를 혼동해서는 안 된다.

`config/styles/recipes/{anima,krea2,pixel}.yaml`의 mined 레시피는 별도 오프라인 실험 후보로, 실행 시 자동 사용되는 승인된 기본 세트가 아니다. `docs/style/GOLDEN_RECIPE_REGISTRY.md`에는 **Golden 0개**라고 명시되어 있다. 외부 웹상의 수많은 스타일이 검색 가능하다는 사실을 현재 설치·검증된 스타일로 셀 수 없다.

필수 보완: 모델별 시각 표현 능력 카탈로그(종류별로 silhouette, pose, spatial relations, faces, equipment count/attachment, composition, typography, materials, background coherence)를 동일한 관찰 기준으로 비교한 기록이 없다. '잘 표현함'이라는 점수는 **NONE/UNKNOWN**으로 유지해야 한다.

## D. 실험 증거·실패의 근거

| 코호트/문서 | 실제 입증한 범위 | 외삽 금지 |
|---|---|---|
| M2 `docs/m2/STATUS.json` | `graphic-risograph`에서 Anima/Krea2 각각 한 생성과 이미지 파일/기술 기록, 사람 리뷰 REQUIRED | 모델 우열, 품질 점수, 범용 스타일 충실도 |
| M2.5 `docs/style/M25_BLOCKER.md` | 12회 요청. NONPIXEL 4/4 **기본 기술 QA** PASS, PIXEL_STATIC **0/8 Pixel Gate PASS** | NONPIXEL이 시각적으로 좋았다거나 PIXEL이 생산 가능하다는 주장 |
| `docs/style/PIXEL_ROOT_CAUSE_AUDIT_20261001.md` | 실패 픽셀 출력 8건의 색수/그라디언트/원본·워크플로 검사 | 실패 원인을 VAE 자체에 단독 귀속, 32px 또는 256px 변환 성공 예측 |
| `docs/research/KREA2_PIXEL64_SMOKE_20261003.md` | 제한된 두 64×64 결과 Pixel Gate PASS·Aseprite 왕복. 리뷰/승인 여전히 필요 | 32×32 품질, 투명 완성본, 범용 LoRA 로더 호환성 |
| `docs/style/VISUAL_HIERARCHY.md` | M2.6 기반 동일 캐릭터/배경 비교 4회. 기술 QA는 통과했으나 **옷만 떨어져 나오는 실패** 관찰 | Subject-first 시각 개선, 완전 인체 보존, 모델 스타일 승인 |
| `docs/style/M27_SUBJECT_FIRST.md` | 구조화된 프롬프트 강제사항의 **offline Gate A** | 실제 이미지 개선 검증, Gate B 수행 |
| `docs/m1/STATUS.json` / `docs/m2/STATUS.json` | 특정 CLI/E2E 생성 흔적 | 제공자 성능의 재현 가능한 벤치마크 |

**실험 설계의 구체적인 결함**

1. 모델별로 충분한 반복·품목 다양성·일관된 평가 루브릭이 없다. 한 장의 잘 나온 이미지나 기술 PASS는 '표현력이 좋다'는 증거가 아니다.
2. 그림을 확인할 때 사용 목적(32px native preview, 실제 전투 화면, 1212×1300 파츠 합성)별 승인 기준이 달랐는데, 단일 품질 판단처럼 이야기했다.
3. 512×768의 픽셀 후보에 최종 logical pixel size가 명확히 잠기지 않은 코호트가 있다. 생성 크기와 엔진 최종 프레임이 분리되지 않아 32px 결론에 사용할 수 없다.
4. 픽셀 평가 코호트에서 `painterly_fantasy`, `storybook_gouache` 등 부드러운 회화 질감 지시와 고정밀 pixel cluster 지시가 섞였다. 이는 픽셀 루트의 최적화를 검증하는 고립 변수 시험이 아니다.
5. Anima와 Krea2는 프롬프트 문법·네이티브 기능·샘플러가 달라 단일 raw 문자열/시드를 사용했다고 같은 조건의 통제 비교가 되지 않는다.
6. 이미지 원본에 대한 **독립적 의미·미술 리뷰 및 게임 크기 실사용**이 없는 경우가 많다. 양적 스코어나 세분화 지표가 없다는 사실뿐 아니라, 개별 판단의 증거를 모으는 프로세스가 부족했다.
7. 일부 문서의 오래된 설명이 이후 실험 상태와 어긋난다. 특히 `RECIPE_VALIDATION.md`의 'M2.5 미구현' 문구는 이후 M2.5 12회 기록과 함께 읽어야 한다. 오래된 스냅샷을 최신 상태로 사용하면 안 된다.
8. 레지스트리 `codex_imagegen`/`grok_imagine`의 `validation.real_generation: NOT_RUN`과 M1의 한정 E2E 생성 성공 기록이 다른 층에 존재한다. 두 기록은 스코프와 최신성 근거를 함께 보여 주고 재검증할 필요가 있다.

## E. 제작사 자료 조사에서 추가로 밝혀진 누락

- Anima 공식 모델 카드: Base는 다양성과 유연성, Aesthetic는 안정적 미술 스타일, Turbo는 빠른 추론과 기본 스타일 편향이라는 **제작사 설명**이 있다. Anima는 anime/art에 초점을 맞추며 텍스트 렌더링/실사에 한계를 명시한다. 공식 일반 설정은 30–50 steps·CFG 4–5를 안내하지만 현재 `anima_base` portrait preset은 24 steps여서 로컬 최적화 근거가 필요하다. `https://huggingface.co/circlestone-labs/Anima`.
- Krea2 공식 prompting 문서는 자연어·상세한 설명·화면 내 문구의 따옴표 사용을 설명한다. 이는 특정 프로젝트의 의미 보존 성능 검증과 다르다. `https://github.com/krea-ai/krea-2/blob/main/docs/prompting.md`.
- 권리 검토: Anima 모델 가중치의 비상업 라이선스와 **출력물의 상업 이용 허용** 조항은 다르다. Krea2 Community License에는 상업적 사용 시 매출 조건과 다른 의무가 있다. 프로젝트별 사용 방식·배포·LoRA 파생 조건은 별도 검토하고 '무료·모든 상업 사용 가능'이라는 한 줄로 단순화하지 않는다. `https://github.com/krea-ai/krea-2/blob/main/docs/KREA-2-COMMUNITY-LICENSE`.

웹의 제작사 포지셔닝은 `AUTHOR_CLAIM`이라는 별도 열에 기록한다. 직접 테스트하지 않은 특징은 `LOCAL_QUALITY=UNKNOWN`이다.

## F. 즉각적인 분류 변경 제안

| 범주 | 선언 가능한 것 | 선언 금지 |
|---|---|---|
| 모델 | 설치/등록된 경로, 문법, 기능 선언, 공식 저작자 주장 | 얼굴·소품·배경 '잘 그린다'라는 검증 없는 선호도 |
| 스타일 | ID, 표현 설명, 관련 레시피 존재 | 프로젝트 공통 '추천 화풍', 승인이 없는 Golden |
| 결과 | 실행 ID, 파일 hash, 기술 QA, 개별 관찰 | 한 실험으로 전 품목·해상도·프로젝트 품질 보증 |
| 선택 | 사용자의 모델 선택, 제약 일치, 실험 필요 판단 | 없는 품질 랭킹으로 자동 기본 모델 선택 |
| 게임 적용 | 해당 프로젝트의 SOT·인게임 배치 검사와 인간 승인 | 해당 프로젝트 자료 없이 범용 game-ready 판정 |

현재 등록과 검증을 분리하는 새 기계 플래그를 **이 감사에서는 변경하지 않는다**. 실제 라우터 상태 변경은 회귀 시험과 별도 승인 후 수행한다.

## G. 미확인 작업 목록 (차후 작업 단위)

- 설치 모델·파생 모델·LoRA·VAE·workflow별 checksum/license/compatibility 실제 inventory.
- 공식 Anima Base/Aesthetic/Turbo와 Krea2 Raw/Turbo 각각의 버전·파라미터·품목별 검증.
- 애셋 카테고리(캐릭터·배경·소품·픽셀·초상화 레이어·UI/SFX)별 **동일 요구사항 테스트**.
- Native 출력 vs 후처리 출력의 분리 평가, alpha·frame anchor·pixel-art 원칙을 지킨 실제 delivery QA.
- 32px 독립 benchmark; Krea64 성공을 전용 32px 루트로 전용하지 말 것.
- 모델별 실패 유형의 원본 이미지/리뷰 기록과 설명서의 자동 갱신 가능 구조.
- 외부 모델/LoRA 상업적 사용 조건별 provenance 검토.

다음 연구 기준: `docs/research/MODEL_STYLE_BENCHMARK_PROTOCOL_v0.1.md`. 이 계획서는 **이미지 생성 요청이나 실험 승인 자체가 아니다**.
