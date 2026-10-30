# M3 factory planning index

**Current priority (2026-10-27):** build the nonpixel still/animation pipeline;
pixel paths remain a research workstream. See the
[current production plan](NONPIXEL_PRODUCTION_PLAN_20261027.md).
Explicit still/audio dispatch and opt-in Factory motion jobs are implemented.
Existing-video replay and native engine imports have dated evidence; generic
Factory motion dispatch, new-coordinator real generation, human quality acceptance
and production activation remain blocked/unverified. See
[motion integration evidence](MOTION_JOB_VALIDATION_20261027.md).

**Same-character variants (2026-10-28):** [expression/pose edit from one selected base](IDENTITY_VARIANT.md). [Project portrait reference-edit validation, 2026-10-30](PROJECT_REFERENCE_EDIT_VALIDATION_20261030.md) records actual experimental Grok edits and the explicit local RGBA delivery boundary; identity/art approval remains separate.

[Portrait source/alpha validation, 2026-10-29](PORTRAIT_SOURCE_ALPHA_VALIDATION_20261029.md): separate opaque source generation from transparent delivery, reuse alpha matting while preserving source RGB, and retain explicit human review.
Its 2026-10-30 follow-up records source-connected white-gap removal, opaque color preservation with translucent-edge unmatting, explicit headroom trials and the remaining human review boundary.

Implementation references: [M3.0 contract](M30_OFFLINE_CONTRACT.md), [M3.1 SFX](M31_SFX_OFFLINE.md).

Execution boundary: [explicit still/audio dispatch](FACTORY_EXECUTION.md).

## Read in order

1. [Factory Architecture v1](FACTORY_ARCHITECTURE_V1.md) — four lines, conditional IMAGE_ONLY vs IMAGE_TO_SPRITE, versioned request envelope, multi-image role and provenance policy, child run isolation, release boundaries.
2. [M3 Factory Workplan](M3_FACTORY_WORKPLAN.md) — main-branch inventory, phased implementation M3.0..M3.6, proposed PR order, negative tests, E2E gates and definition of done.
3. [Project reorganization, 2026-10-11](PROJECT_REORGANIZATION_20261011.md) — integrated main, preserved local work, actual runtime boundaries and stabilization-first backlog. No M3 implementation or generation is authorized by this inventory.

## Decision register (2026-10-11)

| Decision | Value |
| --- | --- |
| A NONPIXEL | IMAGE_ONLY or explicitly requested IMAGE_TO_SPRITE |
| B REFERENCE_MOTION | 1..3 explicit existing image inputs; IMAGE_TO_SPRITE |
| C SFX | AUDIO_ONLY |
| D PIXEL64 | 64x64 IMAGE_ONLY or explicitly requested IMAGE_TO_SPRITE |
| 32px native pixel art | ON_HOLD_RESEARCH |
| Model/style selection | Keep existing 24-style menu, project SOT and model limitations |
| Motion generation | Shared A/B/D backbone only after verified ComfyUI backend support |
| Paid generation and deployment | Not authorized by design document; distinct gates |
| Approvals | All machine-generated output stays REVIEW_REQUIRED until actual review |
| Existing six MCP tools | Preserve compatibility; do not expand in planning PR |

The D PIXEL64 row is the historical factory design. The 2026-10-27 priority
decision defers its production work to research and makes it independent of
nonpixel delivery; it does not remove code or activate/deactivate a registry.

No runtime files, registry entries, workflow graphs, operational status, SOT documents, or approved masters are changed by this planning package.

Current preservation review: [uncommitted-work triage, 2026-10-14](../maintenance/UNCOMMITTED_TRIAGE_20261014.md). Historical inventories below do not supersede current execution contracts.

## 모션·Factory 작업 기록 (2026-10-23 ~ 10-27)

이전 README 상단에 있던 진행 기록을 옮겼습니다. 각 문서는 해당 날짜의 실행 근거이며 현재 승인 상태가 아닙니다.

현재 개발 우선순위는 **넌픽셀 정지 이미지·애니메이션 생산 경로**입니다.
픽셀 경로는 연구과제로 보존하며 넌픽셀 완성의 선행 조건으로 두지 않습니다.
[현재 구현 순서와 수용 기준](NONPIXEL_PRODUCTION_PLAN_20261027.md)을 참고하세요.

기존 정지 이미지의 명시적 모션 후속 작업은
`assetpipe create --type nonpixel-animation --motion-job ... --motion-plan-sha256 ... --output ...`으로
실행할 수 있습니다. [작업 파일·예산·리뷰 경계](MOTION_JOB.md)를 먼저 확인하세요.
프롬프트만으로 영상을 자동 생성하거나 완성품을 승인하는 명령은 아닙니다.

[Factory 모션 작업 흐름](MOTION_JOB.md)은 명시적 작업 파일로 기존 영상 재처리,
승인된 단일 영상 실행 위임, 레시피와 Godot·Phaser 리소스 출력을 연결합니다.
[여우·토끼 재현 검증](MOTION_JOB_VALIDATION_20261027.md)은 새 생성 없이 기존 RGBA 결과와
동일함을 확인했습니다. 일반 Factory 모션 차단·기본 비활성·사람 승인 경계는 유지합니다.

M3 현재 상태는 [2026-10-23 코드 재감사](M3_REAUDIT_20261023.md)를 참고하세요.
기존 영상의 [오프라인 모션 리뷰 패키지](MOTION_PACKAGE.md)를 추가했습니다.
기본 Factory I2V 실행은 여전히 BLOCKED_BACKEND_NOT_VERIFIED이며 기술적 패키징은
애니메이션 품질·Golden·게임 투입 승인을 뜻하지 않습니다.
[모션 사전검증·입력 보존](MOTION_PREFLIGHT.md)은 참조 역할·순서·해시와
설치 상태를 확인하며, 미검증 입력 지원이나 생성 승인을 자동으로 확정하지 않습니다.
참조 1장의 [연구용 단일 시도 실행기](MOTION_EXECUTOR.md)도 추가했습니다.
기본 비활성이며 별도 1회 예산·모델 해시·입력 검증 없이는 실행되지 않습니다.
참조 1장의 연구 경로는 [실제 영상→프레임→스프라이트 E2E](MOTION_REAL_E2E_20261026.md)를
1회 완료했습니다. 결과는 REVIEW_REQUIRED이며 참조 역할·루프·미술 품질 승인은 남아 있습니다.
[동작 검토](MOTION_ADVISORY_REVIEW_20261026.md)에서 루프 경계와
머리 여백·피벗 검토 항목을 기록했습니다. 자산 수정·사람 승인은 수행하지 않았습니다.
후속 [13~32번 루프 후보](MOTION_LOOP_CANDIDATE_20261027.md)는
20프레임을 무손실 재패킹한 별도 결과입니다. 원본은 보존하며 후보도 REVIEW_REQUIRED입니다.
[투명화 비교](MOTION_ALPHA_CANDIDATE_20261027.md)에서는 학습 마스크의
흰 털 손실을 확인했습니다. 테두리 연결 방식도 밝은 테두리·그림자 정리가 필요해 미승인입니다.
후속 [국소 알파 정리](MOTION_ALPHA_CLEANUP_20261027.md)에서 사용자가 요청한
다리 사이 흰 영역과 발밑 그림자를 제거했습니다. 나머지 경계·사람 리뷰는 계속 필요합니다.
[Godot·Phaser 실제 임포트 검증](MOTION_ENGINE_IMPORT_20261027.md)에서
20프레임·24fps 설정, 정상상태 반복 재생, 피벗 매핑과 실제 렌더 화면을 확인했습니다.
초기 타이밍·발 접지·얇은 외곽선·사람 승인은 별도 검토 대상입니다.
[명시적 모션 리뷰 레시피](MOTION_REVIEW_RECIPE.md)로 프레임 구간과
알파 수정 조건을 해시에 묶어 재실행할 수 있습니다. 계획→적용→무결성 점검을 제공하며
사람 리뷰·Golden 승인을 자동으로 통과시키지 않습니다.
[두 번째 캐릭터 검증](MOTION_SECOND_CHARACTER_20261027.md)에서는 토끼 참조를
1회 생성한 뒤 발견한 스타일 바인딩 충돌은 [참조 스타일 의미 연결](MOTION_SOURCE_STYLE_20261027.md)로
보완했습니다. 원본 정지 워크플로·스타일 계약을 재검증하며 영상 품질 승인은 별도로 남깁니다.
토끼도 승인된 영상 1회로 56프레임·스프라이트 패키지까지 완료했습니다.
후속 [토끼용 루프·투명화 후보](RABBIT_MOTION_RECIPE_20261027.md)는
14~41번 28프레임을 선택하고 낮은 흰 배경 허용 오차를 명시한 v2 레시피로 처리했습니다.
얼굴·흰 가방 손실을 일으킨 기존 기준은 채택하지 않았으며 사람 리뷰는 남아 있습니다.
[토끼의 Godot·Phaser 실제 임포트](RABBIT_ENGINE_IMPORT_20261027.md)도 확인했습니다.
28프레임·순서·3회 반복·실제 렌더와 부츠 하단 기준선 간격 1~2px를 확인했으며,
Godot 초기 반복에서 측정 편차가 있었으며 해부학적 발 접지·사람 리뷰는 미승인입니다.
후속 [Godot 시작 시점 진단 보정](GODOT_STARTUP_TIMING_20261027.md)에서는
로딩 델타가 첫 업데이트에 섞이는 검증 도구의 문제를 확인했습니다. 처리 시점과 준비 상태를
분리한 6조건은 첫 반복부터 60Hz 허용 범위 안에 들었으며, 실제 게임의 로딩 정책은 별도 검증 대상입니다.
[2026-10-26 실생성 전 점검](MOTION_LIVE_PLAN_20261026.md)에서
실제 참조 후보 1장, 필수 노드 15개, 모델 5개 파일 해시와 56프레임 계획을 확인했습니다.
해당 사전 점검은 생성·업로드·예산 예약 0건입니다. 이후 승인된 1회 실생성 시험을
완료하고 연구 설정을 비활성으로 복원했습니다.
Windows 예산 예약에서 간헐적으로 발생한 확장 경로 표기 오류는
[원인·수정·보안 검증 기록](../maintenance/FACTORY_ROOT_NAMESPACE_RACE_20261025.md)을 참고하세요.
공통 JSON 기록은 호출별 독립 임시 파일을 사용합니다.
[동시 기록·Windows 잠금 검증](../maintenance/MANIFEST_STAGING_20261026.md)에
실패 시 증거 보존과 남은 제한을 기록했습니다.
