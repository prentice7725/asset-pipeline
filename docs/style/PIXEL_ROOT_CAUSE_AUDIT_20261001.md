# M2.5 Pixel Root Cause Audit — 2026-10-01

## 범위와 판정 기준

- 감사 대상은 `workspace/style_lab/cohorts/20261001T131720658569Z`의 PIXEL_STATIC 8건이다. ComfyUI 생성은 0건 제출했다.
- 분석은 `010_generation/*.png` 원본을 직접 읽어 계산했다. 연락용 미리보기는 색상·픽셀 측정에 사용하지 않았다.
- 각 원본 PNG SHA256은 코호트 기록과 대조했다. `generation.json`, Analyzer, Refiner, Pixel Gate JSON도 8개 샘플 모두 읽었다.
- 로컬 `main` HEAD와 `origin/main`은 `9d4012d2620966c393cbb5e42de059f7a7f6a971`로 같고, 시작 시 미커밋 변경은 없었다. `b92b6542210d3c56c4c8d41d62173aab294ce19f`는 코호트의 `base_commit`이며 현재 HEAD의 조상이다. 현재 workflow registry와 `anima_mushroom_courier_production.json`은 b92 기준과 같다. 현재 HEAD의 추가 변경은 M2.5 독립 경로 및 기존 후보 정적 재검증에 관한 것이다.
- 코호트 예약 예산 12/12, 남은 예산 0, 실제 generation request 12건이다. 픽셀 8건은 모두 Pixel Gate에서 멈췄다. 새 생성·재시도·fallback은 하지 않았다.

## 원본 8건 측정

색상 수와 빈도는 원본 RGB PNG의 393,216개 픽셀을 대상으로 계산했다. 빈도는 가장 많이 나온 불투명 RGB 색상 상위 3개이며 `색상: 픽셀 수 (전체 대비 %)`로 표시한다. `small-step`은 Analyzer가 기록한 인접한 서로 다른 RGB edge 중 거리 임계값 24 이하인 비율이다. 연결 성분·고립 픽셀은 Analyzer의 border-color foreground 추정에 따른 휴리스틱이며, 의미상 결함 판정은 아니다.

| 스타일 후보 / 용도 | 불투명 RGB 색상 수 (예산 32) | 상위 색상 빈도 | Gradient suspicion | Edge / cluster 지표 | Alpha | 원본 → 논리 캔버스 | Pixel Gate |
|---|---:|---|---|---|---|---|---|
| clean_anime_cel / character | 24,567 | `#FFFFFF` 236,529 (60.15%); `#000000` 4,483 (1.14%); `#FC8D09` 959 (0.24%) | HIGH, small-step 82.90% | AA MEDIUM 13.78%; 성분 4; 고립 0성분/0px | RGB, alpha 채널 없음; 전체 불투명 | 512×768 → UNSPECIFIED | FAIL: 색상 수·gradient; 해상도 검토 사유 있음 |
| clean_anime_cel / prop | 8,456 | `#FFFFFF` 203,857 (51.84%); `#004CA5` 26,861 (6.83%); `#004BA4` 26,208 (6.67%) | HIGH, 90.43% | AA LOW 6.33%; 성분 6; 고립 0/0 | RGB, alpha 채널 없음; 전체 불투명 | 512×768 → UNSPECIFIED | FAIL: 색상 수·gradient; 해상도 검토 사유 있음 |
| limited_palette_pixel / character | 23,744 | `#FFFFFF` 219,011 (55.70%); `#000000` 17,767 (4.52%); `#FE9509` 3,041 (0.77%) | HIGH, 84.48% | AA MEDIUM 11.79%; 성분 3; 고립 0/0 | RGB, alpha 채널 없음; 전체 불투명 | 512×768 → UNSPECIFIED | FAIL: 색상 수·gradient; 해상도 검토 사유 있음 |
| limited_palette_pixel / prop | 7,821 | `#FFFFFF` 215,552 (54.82%); `#003491` 43,002 (10.94%); `#003492` 16,102 (4.10%) | HIGH, 90.13% | AA LOW 6.84%; 성분 7; 고립 3성분/3px | RGB, alpha 채널 없음; 전체 불투명 | 512×768 → UNSPECIFIED | FAIL: 색상 수·gradient; 해상도 검토 사유 있음 |
| painterly_fantasy / character | 21,506 | `#FFFFFF` 209,059 (53.17%); `#000000` 4,975 (1.27%); `#080000` 789 (0.20%) | HIGH, 88.47% | AA MEDIUM 12.09%; 성분 2; 고립 0/0 | RGB, alpha 채널 없음; 전체 불투명 | 512×768 → UNSPECIFIED | FAIL: 색상 수·gradient; 해상도 검토 사유 있음 |
| painterly_fantasy / prop | 15,596 | `#FFFFFF` 211,855 (53.88%); `#001C55` 5,310 (1.35%); `#000000` 3,975 (1.01%) | HIGH, 88.39% | AA MEDIUM 10.52%; 성분 5; 고립 2성분/3px | RGB, alpha 채널 없음; 전체 불투명 | 512×768 → UNSPECIFIED | FAIL: 색상 수·gradient; 해상도 검토 사유 있음 |
| storybook_gouache / character | 20,967 | `#FFFFFF` 55,720 (14.17%); `#FDFCFF` 20,112 (5.12%); `#FFFEFF` 12,811 (3.26%) | HIGH, 95.58% | AA MEDIUM 13.19%; 성분 132; 고립 58성분/73px | RGB, alpha 채널 없음; 전체 불투명 | 512×768 → UNSPECIFIED | FAIL: 색상 수·gradient; 해상도 검토 사유 있음 |
| storybook_gouache / prop | 6,913 | `#FFFFFF` 227,037 (57.74%); `#00498D` 31,044 (7.90%); `#00498C` 11,167 (2.84%) | HIGH, 90.89% | AA LOW 6.22%; 성분 2; 고립 0/0 | RGB, alpha 채널 없음; 전체 불투명 | 512×768 → UNSPECIFIED | FAIL: 색상 수·gradient; 해상도 검토 사유 있음 |

8개 모두 Analyzer와 Refiner가 FAIL이고 Pixel Gate는 FAIL이다. 각 Gate의 실패 원인은 `unique colors exceed ... > 32`와 `high gradient suspicion from dense small RGB steps`다. 모든 Analyzer의 `interpolation_evidence`는 HIGH이고 `target_width`/`target_height`/`matches_target`는 null이다. 고정 팔레트는 없으며 Analyzer의 `allowed_palette`도 null이다. Alpha 검사 기준의 393,216개 불투명 픽셀은 실제 PNG가 RGBA라는 뜻이 아니다. 원본 포맷은 RGB로 alpha 채널 자체가 없다.

원본 이미지 해시:

| 샘플 | Original PNG SHA256 |
|---|---|
| clean_anime_cel / character | `b2c061f10feba1f11d4758615954c69d1968c6cfe92801fe163b634b6eafffb4` |
| clean_anime_cel / prop | `ce5496b1b672a8273ddeded15e4ff552f958e6b295e892bb4aae990c6a1b70a9` |
| limited_palette_pixel / character | `714acc37d871787ad78d5d24d7afff6977e2a4f686a434e2ee3c1a6cdcd33cb7` |
| limited_palette_pixel / prop | `24ff44c10afb966793dc472888915e91531148da0c643fa172189d0981e2b1c5` |
| painterly_fantasy / character | `f84d117509cd5ac7e11ff573feb5407a6047875ae12000c5e2470860e7b8779a` |
| painterly_fantasy / prop | `2d5678e5b7db27b511f1c1304ae86a659a6e208929af494aa6e9b804588894c3` |
| storybook_gouache / character | `13de8e55fc4538d0d5722f035dec9e1ab987409669797906ad7424ae0f937750` |
| storybook_gouache / prop | `6ab9dfbda092958f8ccd4931e2c1a7a98a0e87c05202fe101b80d87435d413d5` |

## 실제 workflow, preset, seed와 모델

| 항목 | cohort / registry에서 확인한 사실 |
|---|---|
| Registry workflow ID | `anima_pixelate_x4_vae`, output `PIXEL_STATIC`, status `ACTIVE`; prompt prefix는 `pixel art, chibi`. 태그는 `character`, `pixel`, `static`, `chibi`, `low_postprocess_cost`이며 `prop` 태그는 없다. |
| 사용된 graph | `anima_mushroom_courier_production`, workflow SHA256 `de1d031aad7181b96fc176f243a53ee7f4caf58e92c86023ee1be185c60e01a2`. 현재 파일의 바이트 해시와 generation.json의 해시가 일치한다. 저장 graph의 VAE loader는 `pixelateX4VAEForAnima_animaV10.safetensors`를 지정한다. |
| 실제 preset | generation.json에는 preset ID가 저장되지 않았다. 기록된 실제 파라미터 `512×768, 30 steps, CFG 4.0, er_sde/simple`는 registry default `character_portrait`와 일치한다. workflow graph 자체의 기본 크기는 512×512지만 실행은 preset 값 512×768이다. 따라서 `character_portrait`는 파라미터 일치에 따른 식별이며 manifest에 기록된 preset 이름은 아니다. |
| Character / prop 적용 | registry에는 `character_portrait`·`full_body_character`만 있고 prop preset/태그가 없다. Cohort prop 4건은 `explicit compatible workflow`로 같은 workflow를 명시 선택했고 `matching_tags=[]`다. 즉, 이번 실행은 character와 prop에 같은 portrait 파라미터를 썼지만 registry가 두 용도를 공용 지원한다고 선언하지 않는다. |
| Seed / LoRA | 8건 모두 seed `7725`; LoRA 없음. |
| Diffusion checkpoint | `anima-base-v1.0.safetensors`, SHA256 `bd43b7cffe1ed1153d9c41e7beb2f18cb1273eafbaa3af3edd6a173dc90a006e`. |
| Text encoder | `qwen_3_06b_base.safetensors`, SHA256 `cd2a512003e2f9f3cd3c32a9c3573f820bb28c940f73c57b1ddaa983d9223eba`. |
| VAE | `pixelateX4VAEForAnima_animaV10.safetensors`, SHA256 `9a27e059e2831d43fc441ff9d6381294be19a9449b6ead5ffab0f108182d067c`. |

실제 출력은 512×768이지만 project brief `constraints.resolution`은 null이고 코호트 `logical_canvas`는 `UNSPECIFIED`다. Pixel recipe도 `logical_resolution: PROJECT_SOT_REQUIRED`라고 명시한다. 이 설정으로는 512×768이 논리 픽셀 크기인지, 확대된 생성 크기인지 판정할 수 없다. Workflow의 X4 명칭만으로 4× 스케일이나 목표 논리 해상도를 추론하지 않았다.

위 모델 SHA256은 실행 기록에 보존된 로컬 파일 바이트 해시다. 모델 원본의 upstream 버전·배포본 재현·사용 권리를 증명하는 해시로 해석하지 않는다.

## 생성 단계와 후처리 단계

### 생성 단계에서 직접 확인한 것

- 같은 workflow/model/effective preset/seed 아래 스타일과 role brief가 달라진 8개 출력이 모두 수천 개의 RGB 색상과 HIGH gradient suspicion을 보인다. `limited_palette_pixel`조차 캐릭터 23,744색, 소품 7,821색이다.
- `limited_palette_pixel`이 아닌 두 후보의 실제 문구는 픽셀 용도와 충돌한다. `painterly_fantasy`는 `paint-defined edges`, `layered painted value shapes`, `brushwork`, `painting`; `storybook_gouache`는 `soft painted contours`, `opaque paint shading`, `dry-brush`, `gouache painting`을 포함한다.
- 스타일 catalog 정의가 공용으로 재사용된 흔적도 있다. `clean_anime_cel`의 style 문구는 Pixelate와 Anima Base NONPIXEL 샘플에서 동일하고, `storybook_gouache`의 묘사도 Pixelate와 Krea2 NONPIXEL 샘플에서 같다. Pixel workflow별 recipe 파일은 분리되어 있지만 동일한 style ID/문구를 그대로 공유하는 것은 pixel style을 독립적으로 정한 것과 다르다.
- 모든 샘플이 동일한 VAE variant를 사용했고, matched standard-Anima-VAE 대조군이나 독립 seed 반복은 없다. 따라서 현재 증거는 **이 8개 생성 조합의 Pixel Gate 실패**를 입증한다. Pixelate x4 VAE 단독의 보편적 실패나 성공을 입증하지 않는다. Registry의 `PRIOR_COMPARATIVE_VALIDATION`이 가리키는 `docs/anima_exp_elin_sprite_notes.md`는 이 checkout에 존재하지 않아 이 감사에서는 선행 증거로 검증하지 않았다.

### 후처리에서 직접 확인한 것

- 8개 Refiner는 모두 `binary_alpha_only`다. RGB 원본에 alpha가 없으므로 `changed_pixel_count=0`, `palette_pixels_changed=0`, `alpha_pixels_changed=0`이고 canvas 크기도 그대로다.
- 이 Refiner는 팔레트 제한, 색상 병합, gradient 정리, 논리 캔버스 resize를 하지 않는다. 이는 현재의 안전 범위이며, Pixel Gate를 우회할 근거가 아니다.
- Pixel Gate 실패 때문에 Resolution Gate와 Aseprite export는 8건 모두 `NOT_RUN_BLOCKED_BY_PIXEL_GATE`다. 실패한 입력을 크기 선택 또는 Aseprite review로 넘기지 않았다.

### 원인 분리와 수정 후보

| 구분 | 확인 사실 | 원인 해석 / 확신도 | 후보 수정 방향 |
|---|---|---|---|
| 논리 해상도 미지정 | 8/8 brief resolution null, `logical_canvas=UNSPECIFIED`, 출력은 portrait 512×768 | 해상도·밀도를 정의하지 못한 계약 결함은 확정. 이것이 색상 초과의 단독 원인이라는 증거는 없다. | 프로젝트 SOT에서 character와 prop 각각 논리 캔버스, 카메라/여백, 투명도와 팔레트 정책을 먼저 정한다. 생성 해상도와 논리 해상도를 별도 필드로 기록한다. |
| 스타일 문구 혼합 | Painterly/Gouache 문구가 pixel workflow에 실제 컴파일됨; clean anime 문구도 nonpixel 쪽과 공유됨 | 픽셀 가장자리·클러스터 목표와 상충할 가능성이 높다. 현재 단일 seed 자료로 기여도를 수치 인과화할 수는 없다. | Pixel style 사전과 prompt recipe를 NONPIXEL style 사전에서 분리한다. `limited_palette_pixel`을 유일한 직접 픽셀 후보로 보고, cel/painterly/gouache는 별도 pixel 변형을 만들기 전까지 NONPIXEL 후보로 둔다. |
| VAE / 생성 모델 | workflow graph와 generation.json은 x4 VAE를 사용했다고 기록; 8/8 색상·gradient gate 실패 | 현재 설정에서 출력이 Gate를 통과하지 못한 점은 확정. 표준 VAE 대조가 없어 VAE 영향은 미확인이다. | 동일 brief/prompt/해상도/seed/기타 모델을 고정하고 VAE만 바꾼 matched 대조 실험을 별도 승인받는다. |
| Refiner 범위 | 실제 변경 픽셀 0; 색상 및 크기 변화 없음 | 후처리 단계가 이번 두 실패 항목을 해결하지 못한 것은 확인됨. 생성 단계가 유일한 해결 경로라는 뜻은 아니다. | 기존 원본 보존 후, 명시적 palette+canvas가 정해진 경우에만 비생산 연구 분기에서 픽셀용 palette/nearest-neighbor 후처리 후보를 비교한다. 각 산출물에 동일 Pixel Gate를 적용하고 Gate가 실패하면 중단한다. |
| 용도와 preset | prop 표본에도 character portrait 파라미터를 사용했고 registry match tag는 없음 | 소품 framing/여백/픽셀 점유율은 검증되지 않았다. 색상 gate 실패와는 별도 품질 축이다. | Character/prop prompt, 캔버스, 팔레트와 QA를 분리한다. registry에 prop을 추가하거나 preset을 바꾸는 것은 별도 승인 후에만 한다. |

## 스타일 후보 분리안

| 후보 | 화풍 경계 | 픽셀 밀도 | 논리 해상도 | 팔레트 정책 | 용도 |
|---|---|---|---|---|---|
| `limited_palette_pixel` | 하드 엣지와 명시적 색상 클러스터를 목표로 하는 직접 픽셀 후보 | 현재 미정. 프로젝트가 고른 캔버스에서 coarse/medium/fine 중 하나를 명시하고 결과로 검증 | 프로젝트 SOT 필수; 자동으로 512×768 또는 VAE 이름에서 추론 금지 | 현 설정은 고정 팔레트가 아닌 32색 상한이다. 정본 팔레트가 있으면 exact palette로 명시하고, 없으면 승인 전까지 상한만 QA 정책으로 기록 | Character / prop recipe와 화면 점유 기준을 각각 분리 |
| `clean_anime_cel` | 현재 cel illustration 문구는 NONPIXEL 스타일 후보로 유지 | 픽셀 변형을 새로 승인할 때만 목표 캔버스 기준 지정 | 별도 pixel recipe에 명시 | flat shade/재료색 예산을 새로 정하고 nonpixel 정의를 그대로 상속하지 않음 | 기본은 NONPIXEL character/prop; 필요 시 별도 pixel-cel 후보 |
| `painterly_fantasy` | 붓질·paint edge/painted value를 쓰는 NONPIXEL 후보 | 해당 없음 | 해당 없음 | 모델 recipe의 비픽셀 정책 | NONPIXEL character/prop |
| `storybook_gouache` | gouache·dry-brush·soft painted contour를 쓰는 NONPIXEL 후보 | 해당 없음 | 해당 없음 | 모델 recipe의 비픽셀 정책 | NONPIXEL character/prop; 픽셀화 변형은 새로운 별도 후보 |

따라서 같은 subject brief를 써도 pixel/nonpixel compiled prompt를 같은 style 문구 하나로 단순 공유하지 않는다. Identity와 금지 조건은 같은 Brief에서 보존하되, rendering style, density, 논리 캔버스, palette와 role용 prompt recipe는 output class와 용도별로 따로 선언한다.

## 최소 재실험 제안 — 아직 승인·실행되지 않음

기존 이미지로 할 수 있는 0-generation 정적 분석은 이번 감사로 완료했다. 다음 generation은 새 예산 승인이 필요하다. 최소한 VAE 효과와 seed 의존성을 함께 관찰하려면 **총 8장 / 8 ComfyUI 요청**을 제안한다.

| 축 | 조건 |
|---|---|
| Subject | 코호트에 사용한 동일 character brief(Mira fox)와 prop brief(blue flask), 출력별 brief 고정 |
| Prompt | 하나의 pixel 전용 `limited_palette_pixel` prompt recipe. Painterly/gouache/cel NONPIXEL style 문구를 섞지 않는다. VAE 두 조건에서 role별 prompt는 byte-identical |
| Workflow 비교 | A: 현재 Anima + Pixelate x4 VAE. B: 같은 Anima checkpoint/text encoder/graph/settings의 통제된 표준 Anima VAE 대조군. 바뀌는 축은 VAE 하나 |
| 반복 | seed 7725 및 7726. 각 role×VAE 조건에서 seed당 한 요청, 같은 seed끼리 A/B 짝 비교 |
| 총량 | 2 roles × 2 VAE choices × 2 seeds = 8장. 재시도·fallback 금지 |
| 사전 조건 | 생성 전에 프로젝트 권한자가 character/prop 논리 캔버스, generation canvas, palette 또는 색상 예산, matte/alpha 요구를 SOT로 확정한다. 이 값이 없으면 실행하지 않는다. |
| 산출물·gate | 요청별 generation metadata와 모델/workflow hash, 원본 PNG/hash 보존. Analyzer → 현재 Refiner → Pixel Gate 유지; Pixel Gate PASS 전 Resolution Gate/Aseprite로 진행하지 않음. 사람 승인 없이 Master/Golden 승격 금지 |

추가로 후처리 기여도를 확인하려면 generation 예산과 분리하여 8개 기존 원본 또는 위 비교군 원본을 보존한 연구용 복사본으로만 비교한다. 현재 `binary_alpha_only`를 기준선으로 유지하고, SOT palette/canvas가 확정된 뒤에만 명시적 palette/nearest-neighbor 후보 분기를 시험한다. 변환 원본을 덮어쓰거나 Gate 조건을 완화하지 않으며, 이 분기에서 Gate PASS가 나와도 자동 승인하지 않는다. 본 감사에서는 이 변환도 실행하지 않았다.

## 보호된 상태

- Pixel Gate 임계값, Static Master 인간 승인, 기존 RGBA 회귀, M1 provider 규칙, M2 Visual SOT/style 승인 및 MCP 여섯 도구 계약을 변경하지 않았다.
- Golden Recipe 승인 수는 0, human approval은 0, game-ready 승격은 0이다. 이 문서는 원인 가설과 재실험 제안이며 품질·스타일 승인 증거가 아니다.
- Pixelate x4 VAE only는 이 cohort의 8개 특정 조합에서 Pixel Gate FAIL로 기록한다. VAE 일반의 성공/실패로 일반화하지 않는다.
