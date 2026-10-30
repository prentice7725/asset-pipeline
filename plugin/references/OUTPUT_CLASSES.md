# Output classes

| Class | Contract |
| --- | --- |
| PIXEL_STATIC | Candidate generation, safe refinement, Pixel Gate, Resolution Gate, Aseprite review/export. |
| PIXEL_ANIMATION | Approved static master + existing reviewed motion → verified direct pixelization → Pixel Gate → Aseprite sheet. |
| NONPIXEL_IMAGE | Registered provider generation (ComfyUI workflow, or explicitly requested Codex/Grok CLI) → shared basic image QA → visual-review candidate. |
| NONPIXEL_ANIMATION | SUPPORTED_EXPERIMENTAL contract only; execution blocked in v0.1. |

The MCP builder accepts an output type or uses a prepared brief's type. If neither
is supplied it returns BLOCKED instead of guessing. Derive the type from the user's
stated intent when clear; ask if choosing it would change the requested asset.
# SFX 출력 확장

`SFX`는 텍스트 기반 게임 효과음 후보를 생성한다.
`audio.duration_seconds`는 1–30초이며 생략하면 5초다.
`asset_build_brief`에서도 `duration_seconds`를 전달할 수 있다.
등록된 ACTIVE workflow는 `audio_stable_audio_3_medium`이다.
기본 오디오 QA를 통과해도 청취 검토가 필수이며 자동 승인하지 않는다.
원본 FLAC과 PCM WAV를 프로젝트별 실행 폴더에 보존한다.

# BGM 출력 확장

`BGM`은 YuE2 기반 게임 배경음악 후보다. `bgm.duration_seconds`는 10–300초(기본 60),
기본은 연주곡(`instrumental: true`, 빈 `lyrics`)이고 루프(`loop: true`)다.
`audio_yue2_bgm`은 EXPERIMENTAL이라 `workflow_id`와 experimental 허용을 명시해야 한다.
보컬 유무·분위기·루프 이음매는 청취 검토 항목이며 자동 승인하지 않는다.
