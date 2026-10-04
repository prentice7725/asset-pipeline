# 비픽셀 화풍 프롬프트 연구 v0.1 — Anima / Krea2

> **OFFLINE_PROMPT_STUDY / NOT_RUN** · 픽셀 연구 HOLD. 본 문서는 인터넷 자료를 바탕으로 한 **프롬프트 가설**이지, 실제 이미지 품질 검증/Golden 승인이 아니다. Source first: `docs/style_menu/NUMBERED_CANDIDATE_MENU_v0.1.md`, `config/style_menu/nonpixel_prompt_research_v0.yaml`, `config/workflow_registry.yaml`.

## 외부 공식 연구에서 확인한 차이

| 특징 | Krea2 Turbo | Anima Base |
|---|---|---|
| 주된 입력 | 일반 영어 문장으로 주제·장소·구도·빛·매체/질감 명시 | Danbooru형 태그 + 서술형 자연어 캡션 혼용 |
| 비픽셀 스타일 방향 | Krea Explorer 외부 미리보기 1,596개에서 서술형 스타일 축 추출 | 동일 스타일 목표를 Anima의 선·색·질감 태그와 자연어로 변환 |
| 등록된 실행 기본 | `krea2_base`, 1024×1024, 8 steps, CFG 1.0 | `anima_base`, 초상화 512×768 24 steps CFG 4.0 |
| 공식 예시와 차이 | Krea2 OSS Turbo 권장 8 steps·CFG 0.0·mu 1.15: 현재 그래프별 값/효과 **검증 필요** | Anima Base 공식 일반 30~50 steps CFG4~5: 초상화 24 steps의 적합성 **검증 필요** |
| 모델별 미학적 특성 | Krea 제작사의 미학 탐색·무드보드 전략은 참고 자료 | Anima 저작자의 Base 유연성·Aesthetic 일관성 설명은 참고 자료 |
| 현재 실제 결과 점수 | **UNKNOWN** | **UNKNOWN** |
| 네이티브 negative | 현재 krea2_base 미지원 | 현재 anima_base 지원 |
| LoRA | baseline 없음, Raw 학습/Turbo 사용 설명은 외부 가이드 | baseline 없음, Aesthetic+Tomohi는 다른 혼합 실험이므로 분리 |
| 공통 VAE | `qwen_image_vae.safetensors` | `qwen_image_vae.safetensors` |

Krea의 공식 프롬프트 안내는 자연어로 상세 묘사하는 것을 권장하지만, 각 이미지의 실제 모델 성능은 로컬 생성·검토해야 한다. Anima 저작자는 `er_sde`를 flat colors/sharp lines의 출발점으로 기술한다. 이는 실무 가설이지 Anima가 Krea보다 항상 cel에 좋다는 검증은 아니다.

공식 자료:
- [Anima official guidance](https://huggingface.co/circlestone-labs/Anima)
- [Krea prompt official](https://github.com/krea-ai/krea-2/blob/main/docs/prompting.md)
- [Krea inference official](https://github.com/krea-ai/krea-2)
- [Krea design guide](https://www.krea.ai/blog/krea-2-deep-dive-walkthrough)
- [Explorer images](https://kreastyles.thetacursed.com/)

## 비픽셀 11종 메뉴 연구 상태

| ID | 장르 활용 후보 | 목표로 한 시각 문법 | 모델 연구 레시피 | 결과 |
|---|---|---|---|---|
| `STYLE-001` | SF 사이버펑크 | 레드/차콜, 큰 명암, 네온 림라이트 | Krea 자연어 / Anima 사이버 누아르 태그 | NOT_RUN |
| `STYLE-002` | SF 인물, 현대 스릴러 | 앰버/블루 이중 조명, 얼굴 집중 | Krea 자연어 / Anima 초상화 태그 | NOT_RUN |
| `STYLE-003` | 고딕 판타지 | 90년대 셀, 인디고/마젠타, 배경 수채 텍스처 | Krea 자연어 / Anima 셀 태그 | NOT_RUN |
| `STYLE-004` | 판타지 SD·치비 **비픽셀** | 구아슈 색면, 둥근 덩어리, 따뜻한 명암 | Krea 자연어 / Anima 동화책 태그 | NOT_RUN |
| `STYLE-006` | 중세 판타지 | 선묘·해칭·드문 스티플 | Krea 자연어 / Anima engraving 태그 | NOT_RUN |
| `STYLE-007` | 다크 판타지 | 임파스토, 적색 초점, 키아로스쿠로 | Krea 자연어 / Anima 페인터리 태그 | NOT_RUN |
| `STYLE-008` | 현대 일상물 | 평면 만화색, 강한 외곽선, 소수 명암 | Krea 자연어 / Anima 망가 태그 | NOT_RUN |
| `STYLE-009` | 복고 그래픽/코미디 | 굵은 라인, 포스터, 제한된 리소 질감 | Krea 자연어 / Anima 그래픽 태그 | NOT_RUN |
| `STYLE-010` | 복셀풍 미니어처 | 3/4 등각, 박스형 실루엣 | Krea 자연어 / Anima 등각 태그 | NOT_RUN (2D 렌더룩만) |
| `STYLE-011` | 클레이풍 SD | 매트한 둥근 체적, 차분한 파스텔 | Krea 자연어 / Anima 클레이 태그 | NOT_RUN |
| `STYLE-012` | 펑크 SF·현대 인쇄물 | 흑백 포토카피, 제한된 하프톤 | Krea 자연어 / Anima 펑크 태그 | NOT_RUN |

**`STYLE-005`는 의도적으로 표에서 제외**. 출처는 픽셀풍이므로 32px 원화 검증이 전혀 되지 않은 현재는 HOLD이며, 비픽셀 실험으로 우회하지 않는다.

## Codex와 Claude가 바로 조회하는 방식

```powershell
# 모든 모델별 연구 레시피/잠금 규칙과 live workflow 대조
python scripts/nonpixel_research.py check

# 비픽셀 STYLE-004를 Krea2용 연구 패킷으로 작성 (실제 생성 없음)
python scripts/nonpixel_research.py export --style STYLE-004 --workflow krea2_base --subject "Exactly one adult scout wearing a blue coat and holding a brass compass in the left hand." --output workspace/style_menu/style004_krea2_study.json

# 같은 요구사항으로 Anima 별도 컴파일 연구 (실제 생성 없음)
python scripts/nonpixel_research.py export --style STYLE-004 --workflow anima_base --subject "Exactly one adult scout wearing a blue coat and holding a brass compass in the left hand." --output workspace/style_menu/style004_anima_study.json
```

이 export는 **기존 생산용 `PromptSpec` 대신 사용할 수 있는 문서가 아니다**. 실제 에이전트는 프로젝트 ACTIVE/SOT를 먼저 읽고 대상/캐릭터/장비/해상도 등을 유지하며 기존 PromptSpec을 작성한 다음 적합성·실제 결과 검토 후 운용한다.

## 실험으로 채워야 할 정확한 필드

모델 차이를 측정할 때 미술적 우위를 추정하지 말고 아래 항목을 **샘플마다** 기록한다: `menu_id`, `model_id`, `workflow_graph_sha`, checkpoint/encoder/VAE/LoRA 실제 hash, prompt/adapter version, sampler/steps/CFG/seed, 대상 명세, 원본 출력, anatomy/장비 연결/실루엣, 의도 화풍 색·선·질감, 배경 위계, 기술 QA, 사람 아트 리뷰, 실제 게임 표시 크기, 생성 소요 시간과 수정 비용. 실패와 중단도 결과에 포함한다.

**공통 시험:** SF STYLE-001, 판타지 STYLE-004, 중세 STYLE-006, 현대 STYLE-008 네 후보를 동일 synthetic 전신 캐릭터·배경 2종에서 Anima/Krea2로 비교. `python scripts/style_menu.py plan`은 16-cell 계획만 준비하며 실제 이미지 생성은 현 예산 정책의 승인 절차를 통과한 경우에만 수행한다.

## CLI providers 범위 축소

`docs/m2/STATUS.json`의 `m1_prior_real_e2e`는 2026-10-01 Codex ImageGen과 Grok Imagine 모두 `REAL_GENERATION_VERIFIED` 및 각 이미지 경로와 hash를 기록한다. 이를 생성 경로 성공의 **과거 보고**로 다루고 원본이 남아 있으면 해시를 대조한다. 이미지가 편집·재생성되거나 CLI 버전이 달라졌다면 단일 smoke와 현재 컨디션만 다시 확인한다. 두 CLI의 11개 화풍 전수 비교, 품질 랭킹, LoRA/다중시드 시험을 수행하지 않는다.

## 최종 목표

Codex/Claude는 프로젝트별 SOT와 **이미지가 있는 번호형 메뉴판**을 읽고, 검증된 경우에만 `STYLE-ID → 모델/워크플로 → LoRA/VAE → 적용 레시피 → 변형 허용 항목 → 실제 사례와 실패 사례`로 추적해 제작한다. 지금의 가이드에는 검증된 조합이 없으므로 후보를 **추천 확정**하지 않는다. `docs/style_menu/CODEX_NONPIXEL_WORK_ORDER_v0.1.md`를 사용해 Windows 로컬 Codex에서 실제 시각실험을 수행한다.
