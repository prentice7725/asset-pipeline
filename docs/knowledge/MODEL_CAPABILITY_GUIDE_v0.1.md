# Model Knowledge Base — 사용법과 증거 수준 (v1)

> 상태: IMPLEMENTED_OFFLINE_INVENTORY / VISUAL_QUALITY_UNVERIFIED (2026-10-04)
>
> 이 자료는 모델 등록 현황을 **자동으로 읽고 대조**하기 위한 조사 계층이며 모델 선택을 자동 승인하지 않는다. 게임 프로젝트가 각자의 Drive ACTIVE/SOT에서 정한 아트 방향과 규격이 언제나 우선한다.

## 사용법

```powershell
# 생성/다운로드 없이 Git에 기록된 모델·워크플로·화풍·근거 전체 조회
assetpipe knowledge --output workspace/knowledge_snapshot.json

# 모델별 등록/제작사 주장/실험 근거 확인
assetpipe knowledge --model-id anima-base

# 스타일 카탈로그에 연결된 레시피 상태 확인
assetpipe knowledge --style-id clean_anime_cel

# 모델+스타일 교집합 근거만 조회
assetpipe knowledge --model-id krea2-turbo --style-id graphic-risograph

# Windows ComfyUI 모델 디렉터리에서 선언된 파일 이름 존재만 비교 (조사 대상 경로를 명시)
assetpipe knowledge --models-root "C:/Users/seung/AppData/Local/Comfy-Desktop/ComfyUI-Shared/models" --output workspace/local_inventory.json

# 위 선언된 모델 파일의 SHA256 계산 (실제 큰 safetensors 파일은 오래 걸릴 수 있음)
assetpipe knowledge --models-root "C:/Users/seung/AppData/Local/Comfy-Desktop/ComfyUI-Shared/models" --hash-models --output workspace/local_hash_inventory.json

# 현재 등록되지 않은 추가 모델형 파일명도 조사 (파일 내용은 읽지 않음)
assetpipe knowledge --models-root "C:/Users/seung/AppData/Local/Comfy-Desktop/ComfyUI-Shared/models" --discover-unregistered --output workspace/unregistered_candidates.json
```

파이프라인은 config/workflows에 존재하나 라우팅에 등록되지 않은 JSON 그래프도 `unregistered_workflow_graphs`로 별도 표시한다. 그래프 존재와 자동 사용 가능성은 다르다. `--discover-unregistered` 역시 해당 models 폴더 내 모델형 확장자의 **파일명만** 읽으며 신규 checkpoint를 자동 등록하지 않는다.

로컬 경로는 **이전 실험 기록의 사례**일 뿐 설치 경로를 확정하지 않는다. 실제 현재 사용 중인 ComfyUI 모델 디렉터리로 교체한다. 스캐너는 등록한 모델 파일의 위치와 바이트 해시만 검사하며 서버 연결, 모델 로딩, 다운로드, 생성 요청을 하지 않는다. GPU/ComfyUI 노드 호환성과 상업적 이용권은 별도 검사다. 출력물에 로컬 파일 경로가 포함되므로 외부 공개 전에 점검한다.

코드와 데이터:
- `src/assetpipe/knowledge/__init__.py` — 조회·교차 검증·읽기 전용 파일 스캔.
- `config/knowledge/model_catalog.yaml` — 등록된 모델 변형/제작사 주장(검증 점수와 분리).
- `config/knowledge/experiment_evidence.yaml` — 기존 실험 보고서와 한계 및 원본 재검증 여부.
- `config/workflow_registry.yaml`, `config/model_profiles.yaml` — 실제 **선언된** 런타임 사양.
- `config/styles/catalog.yaml`, `config/styles/model_recipes.yaml` — 스타일과 레시피의 원본 정의.
- `config/styles/recipes/*.yaml` — 오프라인 연구용 미승인 후보.
- `tests/unit/test_knowledge.py`, `.github/workflows/knowledge-integrity.yml` — 재현 가능한 구조 검증.

## 제작사 문서에서 확인한 표현 및 성능 주장 (아직 로컬 검증 아님)

| 모델 | 제작사가 설명하는 특징 | 현재 로컬 확인 필요한 항목 |
|---|---|---|
| Anima Base | 스타일 다양성/유연성, 태그 + 캡션 입력, 30–50 steps CFG4–5 기본 권장; er_sde의 flat/sharp 특성 안내 | 현재 24 steps 사용 이유, 다양한 장비·인체 연결·캐논 준수 및 스타일 지표 |
| Anima Aesthetic | 일관된 기본 화풍을 위한 조정 모델 | Tomohi LoRA 기여 및 미형 편향, 일반 NPC/전신 적합도 |
| Anima Turbo | 8–12 steps CFG1의 속도 최적화, 기본 화풍 편향 | 실제 설치 여부, 모델 등록, 품질/다양성 비교 |
| Krea2 Raw | 비증류 베이스, LoRA 학습/미세조정용으로 제작사 추천 | 실제 설치 여부, 학습·입출력 검증 및 권리 |
| Krea2 Turbo | 제작사가 8 steps 빠른 생성, 자연어 프롬프트를 권장 | 현재 FP8/ComfyUI 설정과 상이한 공식 CFG 정의가 있는지 모델 그래프 검증, 구조·장비·씬 비교 |
| Krea2 Pixel64+Refiner | 픽셀 격자 붕괴/팔레트 변환 기능 | 32px 독립 검증, 알파, LoRA `.magnitude` 적용 누락, 실제 게임 화면 |

**출처(제작사/작성자):**
- [Anima 모델 카드](https://huggingface.co/circlestone-labs/Anima) — Base/Aesthetic/Turbo, prompt 및 기본 설정.
- [Krea2 공식 추론 가이드](https://github.com/krea-ai/krea-2) — Raw/Turbo 및 추론 설정. **참고:** 공식 Turbo 명령은 CFG 0.0이며 현재 로컬 ComfyUI preset에는 CFG 1.0이므로 직접 비교 없이 동등하게 취급하지 않는다.
- [Krea2 공식 프롬프트 가이드](https://github.com/krea-ai/krea-2/blob/main/docs/prompting.md).
- [Krea2 커뮤니티 라이선스](https://github.com/krea-ai/krea-2/blob/main/docs/KREA-2-COMMUNITY-LICENSE).
- [Krea Pixel Art Refiner 문서](https://github.com/envy-ai/ComfyUI-Krea2-Pixel-Art-Refiner).

저작자의 소개 문구(예: '일관된 스타일', '고품질')는 **AUTHOR_CLAIM**이며 Asset-Pipeline 벤치마크 성공으로 둔갑시키지 않는다. 모델의 미술적 우열, 품목별 안정성, 특정 게임에 적합한 화풍은 원본 생성 출력과 사람이 확인한 비교 데이터가 있을 때만 기록한다.

## 등록·작동·품질 판단의 세 층

- **REGISTERED:** Git 설정에 이름·그래프·프로파일이 있다. `ACTIVE`는 실행 경로 상태이며 미술 검증이 아니다.
- **LOCALLY_PRESENT / HASHED:** 사용자 명시 모델 폴더에 이름이 있거나 SHA256을 계산했다. 이 사실만으로 model origin/버전/노드 호환이나 작동 성공이 아니다.
- **ART_REVIEWED / PROJECT_APPROVED:** 실제 후보 원본과 SOT를 대조하고 결과를 평가·승인한 기록이 있다. 이번 지식 기반에는 **그런 승인 기록이 없고 Golden Recipe는 0개**다.

오류가 발생하면 데이터 조용한 자동수정이나 추측 대신 종료한다. 특히 모델 워크플로 매핑 누락, 근거 파일 부재, style ID 불일치, 사람 검토를 허위 PASS로 바꾸는 변경은 테스트에서 실패한다.

## 알려진 기존 실험

| 레코드 | 무엇이 입증되었나 | 무엇이 입증되지 않았나 |
|---|---|---|
| `m2-graphic-risograph-pair` | Anima/Krea2의 특정 스타일로 2회 생성했다는 저장소 결과 기록 | 모델별 아트 품질 우열 및 선호도 |
| `m25-nonpixel-cohort` | 4회 기술 QA PASS **기록** | 캐논 준수·장비 연결·미술 완성 |
| `m25-anima-pixel-fail` | 8회 Pixel Gate FAIL **기록** | 32px로 완성 가능하다는 주장 |
| `krea2-pixel64-smoke` | 64px 두 회 Pixel Gate PASS **기록** | 32px, 알파, 로더 완전 호환, Golden 승인 |
| `m27-nonpixel-detached-clothing` | 기술 PASS지만 완전한 인물이 아닌 코스튬 생성 오류 관찰 **기록** | Subject-first 패치 효과 |
| `m1-cli-providers` | Codex/Grok CLI의 과거 E2E 성공 **기록** | 재현 가능한 모델 성능 등급 |

현재 위 증거는 **체크인된 보고서만 교차 조회**한다. 실제 로컬 무시 디렉터리의 원본 이미지/sha256을 새로 열람한 것처럼 표시하면 안 된다.

## Codex / Claude 공통 요청 규칙

1. 프로젝트 SOT를 먼저 읽어 아트 목적·색/실루엣/장비/해상도를 확정한다.
2. `assetpipe knowledge`로 **근거를 조회**하되 모델 태그·제작사 홍보문을 미술적 장점의 검증으로 사용하지 않는다.
3. 프로젝트에서 검증되지 않은 모델/화풍이면 해당 항목의 `art_quality=UNKNOWN`을 전달하고 비교 실험 대상이라고 기록한다.
4. 사용자가 지정한 model/workflow와 컴파일 제약을 기존 router/PromptSpec으로 검사한다. `knowledge`는 라우터를 대체하지 않는다.
5. 실물 생성은 **별도 승인된 예산** 및 기존 인간 리뷰/QA Gate를 지킨다. 실패·재시도·모델 변경을 숨기지 않는다.
6. 비교 실험 설계는 [MODEL_STYLE_BENCHMARK_PROTOCOL](../research/MODEL_STYLE_BENCHMARK_PROTOCOL_v0.1.md) 기준을 따른다. 현재 실행 승인으로 해석하지 않는다.

## 아직 남은 정확한 과제

1. 실제 Windows ComfyUI 모델 폴더 명시와 offline scanner 결과 확보. CHECKED_IN 설정과 모델의 진짜 버전·hash를 매칭해야 한다.
2. 성격이 다른 Anima Base/Aesthetic/Turbo, Krea Raw/Turbo의 통제된 품목별 비교.
3. 스타일별 일정 샘플수·다중 시드·실패 보존과 블라인드 실제 이미지 검토.
4. 별도 픽셀 32px native 실험/배경·애니메이션·모듈러 초상화 단계별 game-size gate.
5. 라이선스/모델 가중치·출력 이미지 권리를 프로젝트별로 검토.

이 남은 과제를 완료하기 전까지 **'모델별 화풍 특성 파악 완료'는 금지된 결론**이다.
