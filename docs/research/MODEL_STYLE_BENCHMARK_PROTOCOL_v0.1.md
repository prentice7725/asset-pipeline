# MODEL / STYLE BENCHMARK REBUILD PROTOCOL v0.1

상태: PROPOSAL_ONLY — NOT_AUTHORIZED_TO_GENERATE
작성일: 2026-10-04

이 문서는 통제 비교 실험을 설계한다. 이미지 생성·모델 다운로드·체크포인트 교체·자동 재시도·workflow 기본값 변경은 승인하지 않는다. 실험 이전 모든 런타임·프로젝트 SOT·승인 게이트 유지.

## 1. 목표

등록된 모델과 스타일이 어떤 게임 애셋을 실제로 잘 만드는지 확인한다. 세 가지를 구분한다.

- CONFIGURED: model/workflow/style ID가 저장소에 존재한다.
- EVIDENCE: 원본 이미지, 정확한 모델/LoRA/VAE 해시, PromptSpec 및 컴파일 프롬프트, 시드와 그래프 해시, 기술 QA가 확인된다.
- ART: 동일 시각 요구를 실제 출력에서 얼마나 일관되게 충족하는지 독립적인 이미지 검토가 있다.

이 셋이 모두 없는 모델의 '장점'은 가설이다.

## 2. 사전 단계 A — 생성 요청 0

1. 실제 ComfyUI 설치 모델 및 파생 checkpoint, LoRA, VAE, text encoder, custom node, 원 출처, 버전, 라이선스, SHA256 재조사. 설치 경로와 Git registry 비교. 파일명만으로 model hash/공식버전/LoRA 적합성을 추정하지 않음.
2. workflow 9개 등록 항목 전수 검사: 실제 graph/CLI, 입력 negative/image reference/i2i/alpha, seed, size, sampler/steps/CFG, 양자화 및 후처리의 진짜 지원 여부. ACTIVE는 사용 준비 상태이지 품질 PASS가 아님.
3. 모델 패밀리 구분: Anima Base/Aesthetic/Turbo, Krea2 Raw/Turbo, Anima Pixelate, Krea2 Pixel64 LoRA를 별도로 등록/분류. Raw/Turbo가 등록되지 않았으면 AVAILABLE이라고 쓰지 않음. 기존 등록 모델 이외의 모델 설치도 임의로 수행하지 않음.
4. 공식/커뮤니티 주장, 실제 생성, QA, 사람 평가, 승인 근거를 데이터 구조상 서로 다른 필드에 둠.
5. 아래 공통 synthetic fixtures의 정본 사실을 먼저 잠금. 실제 게임의 설정이나 미완성 프로젝트 문서에서 캐릭터를 임의 생성하지 않음.
6. PromptSpec·프롬프트 의미 비교만 먼저 수행. 속성 누락/중복, 개수·장비 착용/휴대·공간 관계, 카메라 및 금지요소 충돌이 있는 후보는 BLOCK.
7. 사전 실험 선언, 반복 횟수, 중단 조건, 동일 평가 기준, 독립 리뷰 담당, 생성 예산의 **별도 승인**을 받아야 후속 실험 실행 가능.

## 3. 비교 대상 Fixture

| 분류 | 필수 통제 속성 | 핵심 실패 지표 |
|---|---|---|
| CHARACTER_SINGLE | 성인 전신, 색상, 정해진 복장과 손-장비 관계 | 몸 분리·크롭·장비 누락·실루엣 혼동 |
| CHARACTER_MULTI | 인물 2명, 각 위치, 휴대 장비의 소유자 | 사람/장비 주인 바뀜, 공간관계 실패 |
| PROP_ISOLATED | 1개 소품의 실루엣·재질·색채 | 중복·재질 바뀜·불필요한 배경 |
| ENVIRONMENT | 명시된 전경/중경/배경 랜드마크 | 공간 연결성·랜드마크·시선 집중 |
| PORTRAIT_MODULAR | 공유 캔버스, 파트/알파/접합 | 얼굴 정체성·파츠 경계·투명도 |
| PIXEL_NATIVE_32 | 실제 32x32 final, 기준 앵커, 팔레트 | pixel cluster, 1x 판독, 장비 식별 |
| PIXEL_NATIVE_64 | 실제 64x64 final, 별도 QA | 동일 32px 성공으로 간주하지 않음 |

초기 Anima/Krea2 T2I 비교 pilot는 CHARACTER_SINGLE, CHARACTER_MULTI, PROP_ISOLATED, ENVIRONMENT 네 종만. PORTRAIT_MODULAR과 PIXEL_NATIVE_32/64는 출력 특성이 달라 별도 실험으로 분리한다.

## 4. 실험 단계 B — 생성 전 별도 승인 필요

제안하는 소규모 pilot 크기는 네 fixture × 두 workflow (anima_base / krea2_base) × 두 반복으로 **총 최대 16 요청**이다. 이는 비용 검토용 예시일 뿐 승인된 예산이 아니다.

조건:
- 동일하게 고정할 것은 명세된 **의미적 요구사항**과 결과물 평가 기준이다. Anima 태그와 Krea2 자연어를 같은 raw prompt로 강제하지 않는다.
- 두 모델 모두 PromptSpec에서 고유 adapter로 컴파일하고, 최종 prompt를 원본으로 기록한다. 필수 negative를 지원하지 않는 workflow 셀은 UNSUPPORTED로 기록하고 자연어로 바꿔 대체하지 않는다.
- workflow의 모델 네이티브 파라미터를 기록하고 동일 cohort 중 임의로 바꾸지 않는다. Anima 공식 30–50 steps와 등록 24 steps의 차이는 **별도 파라미터 ablation 필요** 항목으로 둔다.
- 같은 정수 seed를 써도 서로 다른 모델의 latent noise가 같지 않다. 동일 seed가 공정한 동일 무작위성 통제를 의미한다고 주장하지 않는다.
- input SOT snapshot, fixture/PromptSpec, prompt compiler/recipe hashes, 모델/graph hashes, 실제 출력 전체, human review, 생성 실패와 재시도 0을 run manifest에 보존한다.
- 생성 결과를 사람이 실제 저장된 해상도로 검토한다. 축소 contact sheet 단독 판정 불가.

## 5. 평가 지표 및 블라인드 검토

기술 PASS / 내용 PASS / 미술 PASS / 게임 실제 배치 PASS를 분리한다.

- TECH: 파일 손상·크기·RGBA/알파·Pixel Gate·framing·앵커·팔레트 등 기계적 수치 (지원할 때만).
- SEMANTIC: 신체 일체성, 대상/개수/장비 위치/관계/랜드마크/SOT와의 일치.
- ART: 선의 일관성, 명도 그룹, 실루엣 식별, 색상/재료 충실성, 캐릭터/배경 시각적 위계, 고유 미술 문법.
- IN_GAME: 실제 32px native 또는 해당 게임 크기에서의 식별, 배경/줌/파트 합성/전투 및 UI 연동.

ART/SEMANTIC 각 축은 0=필수 조건 위반, 1=일부 충족·불명확, 2=명확히 충족, NOT_REVIEWED=실제 평가 없음으로 기록한다. 모델명은 가능한 블라인드 처리한 동일 규격 contact sheet와 실제 크기 원본을 함께 확인한다. AI 리뷰와 인간 미술 승인을 서로 대체하지 않는다. 소규모 pilot만으로 범용 모델 순위를 확정하지 않는다.

## 6. 실험 단계 C — 원인 격리

Pilot 이후 **한 축만 변경**하는 ablation을 설계한다. 예: body lock만 적용, 장비 정보 중복만 제거, style description만 변경. 모델·시드·VAE·후처리·프롬프트를 한꺼번에 바꾸는 실험은 원인 분석에 사용할 수 없다.

PIXEL_NATIVE_32는 실제 32x32 전달값을 기준으로 독립적으로 테스트한다. Krea2 Pixel64의 두 성공 사례, Pixelate VAE의 실패, 1024에서 Nearest 256으로 변환한 결과는 서로 다른 루트다. AI 원화를 단순 축소한 후 크기만 맞는다고 통과시켜서는 안 된다. 실제 게임 화면에서 구분되는 실루엣 및 장비와 투명도/접지 앵커까지 검증한다.

모델·파라미터·소스 버전 변경이 있을 때 기존 성능 근거를 조용히 승계하지 않는다.

## 7. 데이터와 종료 조건

실험별 카드에 반드시 기록:
model family/variant/checkpoint hash; LoRA/VAE/node versions; prompt adapter/PromptSpec; workflow/preset/hash; style ID/status; fixture; seed; exact generation resolution; final resolution; raw output hash; QA result; semantic/art review with evidence and reviewer/date; actual game-size result; license/rights; remaining blockers.

상태 용어는 REGISTERED, CAPABILITY_VERIFIED, GENERATED, SEMANTIC_REVIEWED, ART_REVIEWED, PROJECT_APPROVED, GAME_READY_VERIFIED를 **연구용 설명 필드**로만 쓰며 기존 runtime approval state를 바꾸지 않는다.

- 이 문서 자체로 새 이미지 생성 0건.
- 실험 예산 승인 0건.
- 자동 승인 0건 / Golden 승격 0건.
- 현재 M2의 결측된 미술 점수는 UNKNOWN 그대로 둔다.
- 목표는 성공한 사례만 모은 이미지 갤러리가 아니라, 실패 비율과 원인이 재현되는 **신뢰도 있는 제작 매뉴얼**이다.
