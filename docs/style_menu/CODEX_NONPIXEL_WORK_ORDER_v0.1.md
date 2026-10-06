> **DEPRECATED AS PRODUCTION ENTRYPOINT / RESEARCH HISTORY ONLY.** 현재 운영 선택 계약은 [Agent Guide v1](AGENT_RECIPE_SELECTION_GUIDE_v1.md) 및 [STYLE MENU v1](STYLE_MENU_v1.md)이다. 아래 과거 내용은 증거 보존용이며 새 생성 승인이나 production defaults가 아니다.

# CODEX WORK ORDER — NONPIXEL STYLE MENU RESEARCH / REPRODUCTION

> READY_FOR_LOCAL_CODEX — **작업 실행 여부: NOT_STARTED**. 이 Markdown은 Codex CLI에 직접 제공할 실행 지시서다. GitHub issue만 작성하는 것은 Codex가 실행됐다는 뜻이 아니다.
>
> 대상: `prentice7725/asset-pipeline`. 준비 브랜치 `feat/visual-style-menu-from-explorer` (PR #7), 조사 기반 PR #6은 별도 Draft. SOT: 모델 기술 조건은 현재 Git workflow/manifest, 각 게임의 아트 정본은 Drive ACTIVE/SOT. 로컬 ComfyUI 모델은 Windows에서만 검사할 수 있다.

## 0. 작업 목표

**번호가 달린 실제 화풍 메뉴판을 완성한다.** 프로젝트별로 먼저 외부 스타일 미리보기를 살펴본 후, 실제 Anima/Krea2 원본 생성·검토까지 마쳐 검증된 모델별 성격과 파라미터 조합/실패 조건을 추천 메뉴 카드로 만든다. 디렉터리 관리·품질 상태 나열 자체가 목표가 아니다.

픽셀 신규 생성·변환·Pixel Gate ablation은 현재 **HOLD**. 스타일 `STYLE-005`는 검색용으로만 남기고 비픽셀 실험에 절대 포함하지 않는다. Pixel64/PixelOE/Anima Pixelate x4 VAE 연구와 혼합하지 않는다.

Codex ImageGen과 Grok Imagine은 2026-10-01 `docs/m2/STATUS.json`의 `m1_prior_real_e2e`에 둘 다 `REAL_GENERATION_VERIFIED`의 원본 경로·hash가 있다. 우선 이 기록과 실제 보존 원본의 존재/해시를 확인할 것. **모델별 화풍 실험에 두 CLI를 쓰지 않는다**. 실행 경로 회귀가 의심되어 별도 승인된 단일 smoke만 의미가 있다. 원본이 온전하면 불필요한 유료 생성 반복 금지.

## 1. SOURCE FIRST

1. 실제 `main`과 작업 브랜치 HEAD 및 PR #7을 fetch하고 Git 더티 상태를 보존한다. 이어 `docs/style_menu/NUMBERED_CANDIDATE_MENU_v0.1.md`, `config/style_menu/candidates_v0.yaml`, `config/style_menu/nonpixel_prompt_research_v0.yaml`, `scripts/nonpixel_research.py`, `scripts/style_menu.py`, `docs/research/MODEL_STYLE_EVIDENCE_AUDIT_20261004.md`, `docs/research/MODEL_STYLE_BENCHMARK_PROTOCOL_v0.1.md`, `config/workflow_registry.yaml`, `config/model_profiles.yaml`, `docs/style/M27_SUBJECT_FIRST.md`, `plugin/references/AGENT_PROMPT_WORKFLOW.md`를 **실제 읽는다**.
2. 인터넷 원전: `https://kreastyles.thetacursed.com/` → `https://github.com/ThetaCursed/Krea2-Style-Explorer` 고정 커밋 `eb690aa57bc6974af6b4b3b8c5a780195bcadf78`의 `app/data.js`, 개별 WebP. `https://github.com/krea-ai/krea-2/blob/main/docs/prompting.md`와 공식 Raw/Turbo README, `https://huggingface.co/circlestone-labs/Anima`의 Base/Aesthetic/Turbo, 태그/자연어·sampler·steps. 소스 주장과 자체 실험을 구별한다.
3. 로컬 Windows ComfyUI `8188` 연결·node graph·model inventory·checkpoint + text encoder + VAE + LoRA(있으면) hash·설정·노드 지원 범위 확인. 현재 `krea2_base`는 `qwen_image_vae.safetensors`, LoRA 없음, 8 steps CFG1; 공식 Turbo inference CFG0과 다름. `anima_base` portrait preset 24 steps CFG4; 공식 Base 30–50 권장이므로 차이를 기록한다. 비교 cohort에서 파라미터를 임의로 고치지 말 것.
4. 상업 권리: 모델 가중치 vs 생성물 vs 제3자 LoRA/이미지 각각 조사. 모델/LoRA 미설치 시 허락 없이 설치하거나 타 모델로 fallback하지 않는다.

## 2. 최초 목표 4개 스타일 (모두 NONPIXEL_IMAGE)

| 메뉴 | 장르 | 본문 |
|---|---|---|
| `STYLE-001` | SF cyberpunk | 고대비 실루엣, 레드 네온+메탈, 배경 잡음/유광으로 얼굴 묻히는지 |
| `STYLE-004` | 판타지 SD / 치비 **비픽셀** | 구아슈/둥근 덩어리, 신체·장비·의상 보존, 과도 모델화 주의 |
| `STYLE-006` | 중세 판타지 / 기록물 | 잉크 각인·해칭, 명암 덩어리, 소품 인식 및 질감 과밀 |
| `STYLE-008` | 현대 / 만화 | 평면 색, 또렷한 윤곽, 장비 관계, 불필요한 말풍선/문구 |

나머지 7개 **비픽셀 연구 레시피**(002,003,007,009,010,011,012)는 source/research packet만 먼저 검토하고, 실험 결과를 바탕으로 비교 우선순위를 조정한다. `STYLE-005` 픽셀은 제외.

## 3. 프롬프트 실험법

- 먼저 `python scripts/style_menu.py check`, `python scripts/nonpixel_research.py check` 및 `python scripts/style_menu.py plan --output workspace/style_menu/nonpixel_pilot_plan.json` 실행 (이 세 작업 자체는 이미지 생성 0건).
- 기본 후보: `config/style_menu/nonpixel_prompt_research_v0.yaml`에서 Krea2는 자연어 장면·주제 뒤에 스타일 지시 구문, Anima는 호환 태그 + 2문장 이상 의미 설명의 조합. 원 사이트 스타일 프롬프트를 주제의 정본으로 복사하지 않고 *스타일 형태 표현*만 추출한다.
- Synthetic fixture 2개: (a) 완전한 한 명 전신 캐릭터+장비 부착 관계, (b) 전경/중경/배경이 나뉜 풍경 장면. 같은 **의미 명세**를 사용하고 모델별 문법을 변환한다. 게임 SOT 캐릭터/역사 설정을 섞거나 생략하지 않는다.
- 첫 제안 matrix = 4 styles × 2 fixtures × 2 모델 = **16 결과**. 이는 기존 `docs/research/MODEL_STYLE_BENCHMARK_PROTOCOL_v0.1.md`의 실험 설계 수치일 뿐 **생성 승인 예산이 아니다**. 만약 해당 16개 cohort에 대한 명시적인 허가와 런타임 예산 reservation이 이미 없다면, 이 단계는 준비만 하고 generation을 보내지 말 것. `codex exec` 자체를 예산 승인으로 해석하지 않는다.
- 승인 후 한 번 요청한 생성은 임의 재시도·추가 시드·선택적 샘플 삭제 없이 전부 보존. 실험 결과가 1장 잘 나왔다고 Golden 승격하지 않음.
- 비교 가능한 속성: 동일 subject facts/target role/composition/seed list/source refs; 모델별 native sampler & prompt dialect는 동등하지 않으므로 표에 기록; Krea2 CFG0↔CFG1 비교는 모델 최적화 phase에서만 따로.
- 최소 검사: 원본 이미지 PNG/JPG integrity, 누락/추가 인물, 손-장비 연결, anatomy, silhouette, style line/shadow/color/texture fidelity, background dominance, subject leakage, thumbnail/readability. 인간 승인과 기술 QA 별개.
- 실패 시: 소재 과다·분리 의상·중복 인물·부자연스러운 장비·기존 SOT 충돌·모델 기본 미술 문법 우세·예상과 다른 LoRA/VAE 변화 등 원인 분류; 여러 변수 동시 변경 금지.

## 4. 에이전트가 만들어야 할 실제 산출물

1. `docs/style_menu/NUMBERED_CANDIDATE_MENU_v0.1.md`를 실험 이력이 보이는 **이미지 기반 메뉴판**으로 개선(원본 외부 미리보기/로컬 생성 예시 분리). 검증 결과가 없는 경우 후보로 표시.
2. 독립 `workspace/style_menu/experiments/{cohort}/{STYLE-ID}/{workflow}/{fixture}/`에 source fixture hash, PromptSpec, model graph hash, seed, exact prompts, 원본 output sha256, 기술 검사, 의미/미술 리뷰, 실패 포함한 run manifests. CI ignore/큰 파일 Git 정책에 따라 원본 이미지는 필요한 경로에만 보관하고 대용량 무단 커밋 금지.
3. `docs/style_menu/NONPIXEL_COMPARISON_REPORT_v0.1.md`: 스타일별/모델별 실제 **좋은 점·나쁜 점**, 장면/인물 교차 전이, 제작 시간/후처리 비용, 주의해야 할 모델특성. 실험이 없으면 UNMEASURED로 기입.
4. 후보가 충분히 반복 검증된 경우에만 **별도** `docs/style_menu/VERIFIED_STYLE_MENU_v0.1.md`에 사용자 리뷰/승인 없이 자동 Golden 선언하지 말고, 생산 레시피는 단계적으로 승격. 구성: 메뉴 ID, Before/After 이미지, 장르, 모델/워크플로 ID, LoRA/VAE/파라미터, 정본 제약, 실패·수정 레시피, 국소 변경 가능 필드.
5. Codex/Claude 프로젝트별 선택 흐름 문서: 프로젝트 Drive ACTIVE/SOT 확인 → 메뉴 이미지 선택 → 스타일&캐릭터 구분 → 모델별 recipe patch → 소량 변형 시험 → 검토 → 최종 프롬프트. 일반적인 예시는 프로젝트 SOT를 덮어쓰면 안 됨.
6. `docs/m2/STATUS.json`의 CLI 기존 성공 이력은 확인만 하고, 다른 아트 모델 우열과 섞지 않는다.

## 5. 완료 조건

- 픽셀 실험 새 생성 **0**, 기존 경로/승인 로직 불변.
- Krea2/Anima 두 모델의 프롬프트 연구가 **구분 가능하고** 11개 비픽셀 메뉴에 출처가 남는다.
- 최소 pilot은 생성 허가/실행이 있는 범위에서만 이미지 원본과 실패 비율까지 기록.
- Codex/Grok는 필요한 경우에만 CLI smoke 한 번; 스타일마다 반복하지 않는다.
- Git tests 및 CI GREEN, 변경사항/실패·미완료와 **실제 이미지 시각 리뷰**를 PR에 보고. 예술적 품질 미검증이면 화풍을 '추천'하지 않는다.
- `main`으로 무단 merge하지 않는다. 게임별 SOT/Notion에 임의 전파하지 않는다.

## 6. Codex 로컬 실행 방법

사용자 Windows PC에서 ComfyUI가 실행 중인 상태라면 저장소 루트에서 다음과 같이 **현재 파일을 실제 읽을 수 있는 Codex CLI 대화**에 전달한다.

```powershell
cd C:\workspace\asset-pipeline
codex
# Codex 대화에 그대로 붙이기:
# "docs/style_menu/CODEX_NONPIXEL_WORK_ORDER_v0.1.md를 실제 읽고,
#  Source First로 PR #7과 현재 리포를 재검토한 다음
#  비픽셀 화풍 연구 및 승인된 예산 범위의 재현 실험을 수행하라.
#  픽셀은 HOLD, Codex/Grok는 기존 실물 생성 증거 점검만."
```

주의: GitHub PR/Issue 작성은 로컬 Windows Codex CLI를 **실행하거나 GPU 실험을 실제로 시작하지 않는다**. 이것은 Codex 작업용 읽기 쉬운 핸드오프 문서이며, 실행은 해당 환경에서 명시적으로 트리거해야 한다.
