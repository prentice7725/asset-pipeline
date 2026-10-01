# Asset Pipeline M1 — NONPIXEL Multi-Provider

기준: prentice7725/asset-pipeline, main HEAD를 실제 확인. AGENTS.md와 bootstrap directive를 읽고 기존 정본·QA 계약을 유지한다.

목표: NONPIXEL_IMAGE에 comfyui, codex_cli, grok_cli 세 생성 provider를 추가한다.

1. 공통 Provider 인터페이스를 정의하고 기존 ComfyUIProvider를 연결한다. Pixel/SFX 경로는 변경하지 않는다.
2. Codex CLI의 imagegen과 Grok CLI의 image_gen/image_edit 실제 가용성을 독립적으로 검사한다. 가용하지 않으면 BLOCKED 또는 UNAVAILABLE로 반환하며 가짜 이미지·무단 API 우회를 금지한다.
3. Workflow Registry를 엔진별 backend 설정 구조로 확장한다. CLI provider에는 ComfyUI JSON workflow를 요구하지 않는다. 초기 등록 상태는 EXPERIMENTAL 및 explicit_only로 한다.
4. PromptSpec으로부터 provider별 프롬프트를 컴파일하되 canonical_traits, visual_traits, style, silhouette, forbidden_elements를 모두 보존한다. 네이티브 negative prompt와 자연어 금지 지시 기능을 구분한다.
5. brief/route preflight를 모든 진입 경로에서 공유하며 문서 정본 특징 미확정 시 생성 차단을 유지한다.
6. CLI 작업은 격리된 job directory와 허용 경로에서 실행한다. 프로젝트 전체 문서·환경변수·시크릿 전달은 금지하며 비밀정보 로그 노출을 방지한다. Codex 재귀 실행과 무한 호출을 차단한다.
7. 원본 출력과 프롬프트, provider ID, 모델, 인증 방식(비밀 제외), 실행 상태, 소요 시간, 지원 시 요청 ID/usage 정보를 manifest에 기록한다. 지원하지 않는 seed/정확한 재현성은 기록상 미지원으로 표시한다.
8. ComfyUI에서 사용 중인 이미지 QA를 공유하고 해상도·투명도·정본 제약 불충족 결과는 자동 통과시키지 않는다. 모든 생성물은 CANDIDATE_READY_REVIEW_REQUIRED를 유지한다.
9. provider 장애 시 암묵적 fallback 및 중복 유료 요청을 금지한다. 사용자가 명시한 provider를 우선한다.
10. 단위 테스트(라우터·인증 미설정·거절·타임아웃·출력 누락·재귀 차단·manifest)와 실제 E2E 이미지 생성 1장씩을 수행한다. 실제 검증되지 않은 provider를 ACTIVE로 올리지 않는다.
11. 기존 테스트, CLI 및 MCP 6도구 계약의 호환성을 유지한다. README에 로컬 설치·사용량·실패 모드를 기재한다.

완료 조건: 기존 회귀 PASS, 세 provider의 상태 진단 정상, CLI provider 실제 이미지 생성 검증, 공통 QA·manifest·승인 게이트 통과. 테스트 실패나 외부 도구 미가용은 그대로 보고하고 완료로 선언하지 않는다.
