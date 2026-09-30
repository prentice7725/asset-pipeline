# Production instructions

1. Source First: read the relevant project sources and follow the project's source-of-truth rules.
2. Build a validated Asset Brief with `asset_build_brief` before generation.
3. For PROJECT_SOURCES, pass source paths and a source-extracted prepared brief.
   Classify facts as EXPLICIT, DERIVED, or UNSPECIFIED. Never invent missing canon.
4. Check `asset_capabilities`; registry and actual readiness govern available operations.
5. Use `asset_route`; prefer ACTIVE workflows and honor compatible user-selected workflows.
6. Call `asset_generate` only when required capabilities and production inputs are present.
7. Poll `asset_inspect_run` after a long run; an accepted launch is not completion.
8. Never bypass QA or convert REVIEW_REQUIRED, BLOCKED, or FAILED into PASS.
9. Pixel output must pass Pixel Gate and still retain any required identity/Aseprite review.
10. Pixel animation requires a hash-approved Static Master, reviewed existing motion,
    and semantic selection. CHARACTER_LOCAL_DIRECT remains the primary path.
11. Never use experimental recovery automatically. Do not create workflows or redesign character identity.
12. Return run ID, output references, QA, failure reasons, and review-required items clearly.

Examples: a sword warrior request becomes a PIXEL_STATIC brief; an existing
character walk request first checks approved master/motion inputs; a project
protagonist request extracts canon from sources; a Krea2 request explicitly selects
`krea2_base` and validates capabilities. Missing inputs block rather than being fabricated.
# 프로젝트별 결과 저장

효과음 요청은 출력 유형 `SFX`를 사용한다. `asset_build_brief`의
`duration_seconds`로 길이를 지정하고 기존 생성·조회 도구를 사용한다.
기본 오디오 QA 통과는 청취 승인과 다르다. 음악·음성·잡음이 없는지 직접 검토한다.

요청받은 프로젝트 ID를 Asset Brief의 `project_id`에 명시한다.
`asset_build_brief`에도 `project_id`를 전달할 수 있다.
결과는 `output_root/프로젝트ID/runs/애셋ID/실행ID/`에 저장되며,
소스 경로에서 프로젝트를 추측하지 않는다. 생략된 요청은 `default`에 저장한다.
기존 실행을 이어갈 때는 원래 프로젝트 ID를 유지한다.
