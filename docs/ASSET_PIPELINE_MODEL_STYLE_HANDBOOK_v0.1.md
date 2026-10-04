# Asset-Pipeline 모델·스타일 취급 설명서 v0.1

> 작성일: 2026-10-04 · 상태: **RESEARCH_INCOMPLETE / INVENTORY_ONLY — 모델 표현능력·스타일 최적 레시피 미검증**
>
> **이 문서를 읽는 대상:** 각 게임 프로젝트의 기획/아트 담당자, Codex, Claude.
>
> **핵심 원칙:** Asset-Pipeline은 **어떤 모델·워크플로·스타일·후처리를 사용하면 무엇을 시도할 수 있는지**를 설명한다. 각 **게임 프로젝트는 이를 참고해 자기만의 아트 레퍼런스와 SOT를 작성**한다. 파이프라인은 게임의 화풍이나 캐릭터를 대신 결정하지 않는다.

> ⚠️ **2026-10-04 정정:** 이 문서가 모든 설치 모델·워크플로의 실제 작동 및 화풍별 강점·최적 레시피를 조사한 것처럼 소개한 것은 과장이다. Git 등록 9 워크플로·6 prompt profiles·7 catalog styles·15 M2 recipe entries는 **기계적 목록**이며, 로컬 설치 본체와 예술적 품질은 전수 조사되지 않았다. pixel cohort 8/8 FAIL과 고립된 소수 생성 시도는 특정 생성 경로의 성공적인 품질 비교를 의미하지 않는다. 권장 모델이나 style winner 판단의 근거로 이 문서만 사용하지 말 것.
>
> 근거 및 미조사 범위: [MODEL_STYLE_EVIDENCE_AUDIT_20261004.md](research/MODEL_STYLE_EVIDENCE_AUDIT_20261004.md). 향후 통제된 비교 계획: [MODEL_STYLE_BENCHMARK_PROTOCOL_v0.1.md](research/MODEL_STYLE_BENCHMARK_PROTOCOL_v0.1.md). 현재 계획은 새 이미지 생성 승인이 아니다.

## 0. 취급 설명서의 역할

프로젝트가 파이프라인에 맞춰 `PROJECT_PROFILE.md`, `ASSET_REFERENCE.md`, `ASSET_MANIFEST.md` 같은 새로운 고정 양식을 작성할 필요는 **없다**. 각 프로젝트의 기존 아트 바이블, 개별 캐릭터 시트, UI 명세, 게임 화면 규격, 레퍼런스 이미지, Drive ACTIVE/SOT가 그대로 우선한다.

프로젝트는 아래 미완성 목록을 통해 모델·스타일 후보와 해상도·투명도 제약을 살펴볼 수 있다. 검증되지 않은 표현 강점과 우열은 아직 알 수 없으며, 프로젝트의 아트 방향은 자체 SOT·레퍼런스와 별도의 품질 비교를 근거로 결정해야 한다. 실제 작업 의뢰 시 Codex/Claude가 프로젝트 SOT와 레퍼런스에서 필요한 정보를 추출하여 **기존 `schemas/asset_brief.schema.json` 및 `schemas/prompt-spec.schema.json`** 형식으로 변환한다. 프로젝트 문서 자체에 YAML/front matter나 고정 파일명을 강제하지 않는다.

```text
Asset-Pipeline 설명서/스타일 카탈로그
   ├─ 등록된 모델 · LoRA · VAE · 워크플로
   ├─ 스타일별 적용 가능한 레시피와 표현 특징
   ├─ 성공/실패 실험, 샘플, 검증 및 승인 상태
   └─ 기능·제약·라이선스 검토
                 ↓ 참고
각 게임 프로젝트 (각자의 Drive ACTIVE/SOT)
   ├─ 아트 디렉션 / 캐릭터·환경 설정
   ├─ 작품에 맞춘 이미지 레퍼런스
   ├─ 최종 애셋 크기·앵커·렌더링·레이어 규칙
   └─ 사용할 모델·레시피 선정 또는 실험 요청
                 ↓
Codex / Claude 공통 asset-production 스킬
   → SOT 읽기 → 기존 Asset Brief/PromptSpec
   → 호환성 확인·모델별 프롬프트 컴파일
   → 생성 → 검증 → 게임별 승인/편입
```

## 1. 먼저 알아야 할 상태 표기

모델·레시피를 '쓸 수 있음'과 '그림을 잘 그림'은 완전히 다른 판단이다.

| 상태 | 정확한 의미 |
|---|---|
| `ACTIVE` | 현재 라우터에서 선택 가능한 워크플로. 그림의 품질이나 게임 적합성 보증이 아님 |
| `EXPERIMENTAL` | 명시적 선택·옵트인 및 준비상태 검사가 필요한 실험용 |
| `UNTESTED` | 설명/레시피만 있는 미검증 후보 |
| `NORMALIZED` / `OFFLINE_COMPILED` | 자료를 정리하거나 프롬프트 컴파일만 검증. 그림 자체는 아직 검증 안 됨 |
| `TESTED` | 특정 워크플로·프롬프트·시드·출력 조건에서 실제 생성/QA 근거가 있음 |
| `APPROVED` | 적용 대상과 승인 주체가 기록된 승인. 다른 게임의 SOT까지 자동 승인하지 않음 |
| `BLOCKED` | 핵심 기능이나 정본 사실이 빠져 있어 진행 금지 |

**성능 추천에는 근거 등급이 있어야 한다.** 모델 제작사 설명은 `AUTHOR_GUIDANCE`, 워크플로의 용도 태그는 `INTENDED_USE`, 실물 생성 결과는 `LOCAL_TESTED`, 비교 평가와 승인까지 있으면 `REVIEWED/APPROVED`로 분리한다. 근거 없는 'Anima가 인물을 더 잘 그린다' 또는 'Krea2가 배경을 더 잘 그린다' 같은 일반적 우열은 기록하지 않는다.

## 2. 사용 가능한 모델·워크플로

2026-10-04 현재 Git `main`의 레지스트리·모델 프로파일 기준 요약. 설치 환경이 달라질 수 있으므로 실행 시 `asset_capabilities` 및 `asset_route`로 재확인한다.

| 모델/워크플로 ID | 제작 후보로 고려할 표현 분야¹ | 등록 상태 | 중요한 제약 |
|---|---|---|---|
| **Anima Base** `anima_base` | 애니메이션 계열 인물, 판타지 일러스트, 초상화/캐릭터 콘셉트 | ACTIVE / NONPIXEL_IMAGE | T2I. Negative 가능. 참조 이미지 직접 입력, 직접 투명 알파, i2i 미지원 |
| **Krea2 Turbo** `krea2_base` | 자연어로 묘사하는 구성·장면, 판타지 콘셉트/일러스트 후보 | ACTIVE / NONPIXEL_IMAGE | T2I. 현재 연결 워크플로 **Native Negative 미지원**. 참조·직접 알파·i2i 미지원 |
| **Anima + Pixelate x4 VAE** `anima_pixelate_x4_vae` | 픽셀 느낌의 원천 후보와 픽셀 후처리 실험 | ACTIVE / PIXEL_STATIC | 실제 8개 픽셀 코호트 Pixel Gate 모두 FAIL. **32px 품질이 검증된 루트 아님** |
| **Anima Aesthetic + Tomohi LoRA** `tomohi_character` | 스타일화된 애니메이션 인물 실험 | EXPERIMENTAL / 명시 선택 | `tomohi` 트리거·LoRA 의존. 게임별 화풍 적합성 미승인 |
| **Codex ImageGen** `codex_imagegen` | 대체 자연어 생성 제공자 실험 | EXPERIMENTAL / 명시 선택 | 시드·정확한 크기·직접 알파·Native Negative 보장 안 됨 |
| **Grok Imagine** `grok_imagine` | 자연어 이미지 생성·편집 계열 실험 | EXPERIMENTAL / 명시 선택 | 레지스트리의 이미지 편집/참조 지원은 실제 도구에서 별도 확인. 시드·크기·알파·Native Negative 보장 안 됨 |
| **Krea2 Pixel Art LoRA + Refiner** | 64×64 픽셀 출력 연구 | **실험 문서만 존재; 자동 생산 레지스트리 미등록** | 64px에서 제한적 성공. 32px·투명도·LoRA 로더 완전 호환 미검증 |

¹ '고려할 분야'는 **모델 지침과 registry tags를 기반으로 한 용도 후보**다. 다른 모델보다 실제로 우수하다는 비교 결과가 아니다.

추가 출력 경로: `minimax_character_motion_reference`는 승인된 픽셀 Static Master가 있어야 사용하는 **모션 레퍼런스** 작업이며 독립적인 화풍 모델이 아니다. `audio_stable_audio_3_medium`은 SFX용이다. 일반 NONPIXEL_ANIMATION을 생산 가능한 것으로 소개하지 않는다.

**모델마다 프롬프트 표현도 다르다.**

- Anima: 등록된 adapter가 태그 + 명확한 캡션/관계 설명을 구성한다. `anima-pixel` 프로파일의 `pixel art, chibi` 접두어는 **그 프로파일에 한정**된다. 프로젝트가 치비를 승인하지 않았는데 모든 Anima 요청에 넣지 않는다.
- Krea2: 단순한 키워드 더미보다 장면·구도·관계·시선 집중을 담은 직접적인 자연어 설명을 사용하는 경로다. 필수 금지요소가 Native Negative를 요구하면 해당 워크플로를 우회시키지 말고 BLOCK한다.
- 두 모델 모두: 모델 전용 문법은 컴파일러가 책임진다. 프로젝트는 자기 화풍과 보존할 특징을 기술하며 Anima 태그 문법/Krea2 최적화 프롬프트를 직접 만들 필요가 없다.

관련 데이터: `config/workflow_registry.yaml`, `config/model_profiles.yaml`, `docs/PROMPT_SPEC.md`, `docs/style/MODEL_DIALECT_RULES.md`.

## 3. 스타일 카탈로그: 원하는 표현을 어떤 레시피로 시도하나

**Style ID는 시각적 문법의 이름**이지, 캐릭터·장비·세계관의 정체성이 아니다.

| Style ID | 표현 특징 | 현재 근거 및 선택 주의점 |
|---|---|---|
| `anime-cel` | 또렷한 외곽선, 2D 애니메이션, 분리된 셀 그림자 | UNTESTED. 모델 제작사 자료를 참고한 아트 후보 |
| `clean_anime_cel` | 단순한 색 덩어리, 폐곡선, 넓은 셀 그림자, 낮은 질감 노이즈 | mined recipe가 OFFLINE_COMPILED 수준. 생성 품질 미승인 |
| `graphic-risograph` | 강한 그래픽 형태, 색 블록, 얇은 인쇄 질감 | 스타일 자체 UNTESTED. Anima/Krea2 개별 recipe는 TESTED 이력, 인간 APPROVED 아님 |
| `ink-storybook` | 가는 잉크 선, 차분한 파스텔, 해칭 | UNTESTED |
| `storybook_gouache` | 불투명 채색·부드러운 붓질·종이 질감 | INSUFFICIENT_EVIDENCE / UNTESTED |
| `painterly_fantasy` | 넓은 명도 면, 회화적 경계, 제한된 붓질 | UNTESTED. 픽셀아트로의 성공을 뜻하지 않음 |
| `limited_palette_pixel` | 제한 팔레트, 단계형 윤곽, 큰 픽셀 클러스터 | UNTESTED. 해당 Pixelate 실험은 Pixel Gate FAIL |

주의: `anime-cel`과 `clean_anime_cel`은 서로 다른 catalog ID다.

검색/호출 구조는 **표현 → Style ID → 해당 스타일의 모델별 레시피 → 지원되는 워크플로 → 실제 검증 근거**다.

- `config/styles/catalog.yaml`: 스타일 설명, 색·선·명암·질감, 금지 표현, 출처와 상태
- `config/styles/model_recipes.yaml`: 스타일 × 워크플로의 세부 연결 및 시험 상태
- `config/styles/recipes/anima.yaml`: Anima용 추가 레시피 후보
- `config/styles/recipes/krea2.yaml`: Krea2용 추가 레시피 후보
- `config/styles/recipes/pixel.yaml`: 픽셀 관련 오프라인 연구 후보
- `docs/style/GOLDEN_RECIPE_REGISTRY.md`: Golden 승인 관련 레지스트리
- `docs/style/RECIPE_VALIDATION.md`: 어떤 근거가 있어야 생산으로 승격 가능한지

예시: '얇은 잉크 선의 동화책풍'을 원하면 `ink-storybook`을 조회해 특징과 모델 레시피를 살펴볼 수 있다. **아직 검증된 최적 모델은 없으므로** 프로젝트가 선택하거나 비교 실험을 거쳐야 한다. '자동 추천'을 위해 근거 없이 TESTED/APPROVED로 격상하지 않는다.

## 4. 실험에서 이미 확인된 사실

### 4.1 32px 목표에 대한 Anima Pixelate 경고

`docs/style/PIXEL_ROOT_CAUSE_AUDIT_20261001.md`의 실제 이미지 8개는 모두 Pixel Gate FAIL이었다. 지나치게 많은 RGB 색과 연속 그라디언트가 확인됐다. 워크플로의 이름에 `Pixelate`가 있거나 생성 결과를 Nearest로 줄였다는 것만으로 **실사용 32×32 픽셀 애셋**이 되는 것은 아니다.

### 4.2 Krea2 Pixel Art 64px 실험

`docs/research/KREA2_PIXEL64_SMOKE_20261003.md`에 기록된 **64×64** 두 후보는 Pixel Gate PASS(각 22색)와 Aseprite 왕복 검증을 통과했다. 그러나 배경이 불투명하고, `.magnitude` LoRA 키 120개가 로더에서 소비되지 않았다는 호환 경고가 있었다. 현재 승인된 32px Static Master나 범용 픽셀 솔루션은 아니다. **32px 프로젝트는 독립적으로 32px 가독성을 검증해야 한다.**

### 4.3 M2 모델별 스타일 평가 한계

`graphic-risograph`의 Anima/Krea2 recipe에는 각각 생성 테스트 근거가 있다. 그러나 사람이 검토해 '이 스타일에서는 어느 모델이 더 좋다'라고 판정한 성능 순위는 존재하지 않는다. 따라서 설명서에는 **검증 범위**를 적고 모델의 우열을 만들어내지 않는다.

### 4.4 출력 형식은 프로젝트가 결정

한 게임의 전투 애셋이 **32×32, 발 앵커, Nearest**를 요구하고 다른 게임의 모듈러 초상화가 **1212×1300, 투명 RGBA, 공통 파츠 캔버스**를 요구할 수 있다. 이 숫자들은 모델의 권장값이 아니라 프로젝트 SOT의 요구사항이다. 생성 원화 캔버스, 최종 내보내기 해상도, 게임에서 보이는 크기를 구분한다.

## 5. 프로젝트에서 이 설명서를 활용하는 방법

프로젝트 레퍼런스 문서가 반드시 답해야 할 질문들은 있지만 **파일 구조를 통일할 필요는 없다.**

1. **무엇을 그리나?** 어떤 화면에 들어가고 얼굴·행동·장비 중 무엇이 중요한가?
2. **무엇이 정본인가?** 인물 신체·복장·장비 관계, 세계관, 색채, 절대 바뀌면 안 되는 것이 무엇이며 어디에 근거하는가?
3. **어떻게 그릴 것인가?** 시점, 실루엣, 색 덩어리, 명암, 질감, 배경의 시각적 우선순위를 어떻게 설정하는가?
4. **어떤 결과물이 필요한가?** 프레임·캔버스·알파·앵커·레이어·애니메이션 및 실제 화면 크기에서의 검수 조건은 무엇인가?
5. **파이프라인의 어떤 도구를 활용하나?** 후보 style_id/workflow_id가 있는가? 검증된 이유인가, 아직 가설인가?

이 다섯 항목은 콘텐츠 작성 가이드이지 새 스키마가 아니다. 이미 해당 정보가 기존 아트 바이블에 있으면 그대로 사용한다. 필요한 부분만 프로젝트 안에서 보강한다.

### 실제 사용 예시: 32px 전투 유닛

해당 프로젝트 SOT가 '최종 32px 픽셀 유닛'을 요구한다면 설명서에서 Anima Pixelate의 실패 이력과 Krea2 Pixel64의 한계부터 확인한다. 64px에서 성공한 그래프를 곧바로 32px 검증된 제작법이라고 기록하지 않는다. 프로젝트는 자기 캐릭터 레퍼런스를 자유롭게 만들고, 필요한 경우 별도의 32px 실험을 명시적으로 승인한다.

### 실제 사용 예시: 비픽셀 모듈러 인물

프로젝트의 초상화 SOT가 허용한 체형, 나이 표현, 코스튬, 캔버스와 레이어 규칙을 먼저 확인한다. `anime-cel` 계열 같은 화풍 카탈로그를 참고할 수 있으나 카탈로그의 내용만으로 게임 캐릭터의 정체성을 새로 정하거나 `APPROVED`로 확정하지 않는다. 투명 파츠 합성은 별도의 기술검수가 필요하다.

## 6. Codex / Claude 사용 흐름

```text
(1) 설명서와 최신 registry 조회
(2) 프로젝트의 ACTIVE/SOT와 게임 실제 코드/표시 규칙 읽기
(3) 해당 프로젝트 고유의 아트 레퍼런스 해석
(4) 후보 모델·style_id·workflow 선택 근거 대조
(5) 기존 Asset Brief와 PromptSpec 작성
(6) capabilities/route/compile → 독립적 프롬프트 의미 검토
(7) 승인된 1회 생성 → 이미지 실물 검수 + 기존 QA
(8) 후보/기술검증/사람 승인/런타임 편입 상태 구별하여 보고
```

- 프로젝트가 이미 선택한 모델·화풍은 존중한다. 이 설명서는 프로젝트 SOT보다 위에 있지 않다.
- 필수 Negative, 참조 이미지, 알파, 정확한 크기 기능을 등록 워크플로가 제공하지 않으면 **BLOCK**한다. 조용히 다른 모델로 대체하지 않는다.
- 개별 프로젝트 파일로부터 `EXPLICIT` / `DERIVED` / `UNSPECIFIED` 근거를 보존한다. 불명확한 캐릭터 장비·성별·복장·설정은 추측해서 넣지 않는다.
- 프로젝트가 특정 모델을 고르지 않았을 때도 테스트되지 않은 '선호도'를 발명해 자동 확정하지 않는다.
- 생성 전 의미 검토의 프롬프트 수정은 기존 에이전트 계약에 따르되 무단 이미지 재시도·자동 승인·실험적 우회는 금지한다.
- 성능/승인 상태가 바뀔 때는 **실제 결과, 모델/LoRA 해시, 파라미터, 실패 사례, 정본 및 권리 검토**로 갱신한다.

## 7. 앞으로 이 설명서에 축적할 항목

각 모델·LoRA·VAE/스타일 조합마다 권장하는 **증거 카드(evidence card)**:

| 항목 | 기록 내용 |
|---|---|
| 모델 구성 | 모델/변형/해시, LoRA와 VAE, 라이선스 및 사용 범위 |
| 사용 용도 | 캐릭터, 배경, 오브젝트, UI, 픽셀, 초상화 등 정확한 분류 |
| 스타일 | style_id, line/color/shading/texture, 금지·회피 조건 |
| 설정 | workflow ID, 프리셋, 샘플러, CFG, steps, seed, 출력 크기 |
| 사례 | 원본 이미지·실사용 크기 미리보기·run manifest·QA 수치 |
| 관찰 | 실루엣/손·장비 연결/시점/배경/팔레트의 장점과 실패 유형 |
| 적용 한계 | 32px/64px 차이, 참조 입력 지원, 알파, 모듈 분리 여부 |
| 신뢰도 | UNTESTED / TESTED / APPROVED와 근거·검토자·날짜 |

측정 지표, 통제 비교군, 실제 인간 검토를 확보하기 전에는 **별점이나 모델별 순위표를 채우지 않는다.** 설명서는 실험 결과에 따라 갱신된다. 게임 프로젝트에 이미 잠긴 스타일을 변경하도록 역전파하지 않는다.

## 8. 함께 읽을 문서

- `README.md`: 설치, CLI, MCP 사용법
- `plugin/skills/asset-production/SKILL.md`: Codex/Claude 공통 스킬
- `plugin/references/STYLE_INTELLIGENCE.md`: 스타일과 프로젝트 SOT 우선순위
- `plugin/references/AGENT_PROMPT_WORKFLOW.md`: 에이전트 아트 디렉션, 모델별 프롬프트, 독립 검증(현재 NONPIXEL_IMAGE)
- `docs/PROMPT_SPEC.md`: 공통 PromptSpec과 Anima/Krea2 어댑터
- `config/workflow_registry.yaml`: 실제 워크플로와 기능
- `config/styles/catalog.yaml`, `config/styles/model_recipes.yaml`: 스타일과 레시피의 기계 판독 원본
- `docs/style/PIXEL_ROOT_CAUSE_AUDIT_20261001.md`: Pixelate 실패 사례
- `docs/research/KREA2_PIXEL64_SMOKE_20261003.md`: 64px 실험 근거

---
**유지관리 기준:** 모델/워크플로/스타일과 그 성능 기록은 Asset-Pipeline에서 유지한다. 게임의 아트 방향·승인된 레퍼런스·실제 출력 계약은 각 프로젝트가 유지한다. 두 층의 책임을 혼동하지 않는다.
