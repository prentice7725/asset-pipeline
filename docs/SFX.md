# Codex에서 SFX 만들기

`audio_stable_audio_3_medium`을 `SFX` 출력 유형의 ACTIVE workflow로 등록했습니다.
현재 설치된 체크포인트와 텍스트 인코더를 사용합니다. 기존 템플릿의 생성 노드는
유지하고 선택적인 Qwen 프롬프트 확장·카테고리 분기를 제외한 직접 입력 경로입니다.
원래 갤러리 템플릿을 그대로 실행하는 것과는 다릅니다.

Codex MCP를 연결한 뒤 앱을 재시작하고 다음처럼 요청하세요.

> game-a 프로젝트에 칼 충돌 효과음을 3초로 만들어줘. 짧은 금속 충돌과 잔향, 음악과 목소리는 없이.

Codex는 `asset_build_brief`에 `requested_output_type: SFX`, `project_id: game-a`,
`duration_seconds: 3`을 전달한 뒤 기존 `asset_route`, `asset_generate`,
`asset_inspect_run`을 사용합니다. 새 MCP 도구를 추가하지 않았습니다.

CLI에서도 사용할 수 있습니다.

```powershell
assetpipe create --type sfx --project game-a --asset-id sword_hit --duration 3 --prompt "A single metallic sword impact, sharp clang with a short ringing decay, dry close recording, no music, no speech."
```

준비된 Brief 예제는 `examples/sfx_sword_hit.yaml`입니다.
길이는 1–30초를 지정할 수 있으며 생략하면 5초입니다.
현재는 텍스트 기반 SFX만 지원합니다. 이미지·오디오 레퍼런스, 음악 생산 경로,
음성 합성, 자동 청취 승인, 자동 무음 제거·노멀라이즈는 지원하지 않습니다.

이 workflow는 별도 negative prompt를 지원한다고 가정하지 않습니다.
제외 요구는 예제처럼 본문에 명시하세요. 별도 negative 입력이 있으면 라우팅을 차단합니다.
프롬프트 준수 여부는 생성 후 반드시 직접 들어보고 판단해야 합니다.

## 저장 결과와 검증

MCP 결과는 `output_root/프로젝트ID/runs/애셋ID/실행ID/`에 저장합니다.

- `010_generation/`: 원본 FLAC, 실제 주입한 workflow, 프롬프트·seed·생성 파라미터
- `020_audio/`: 16-bit PCM WAV와 `audio_qa.json`
- `run_manifest.json`: workflow 모델·해시, 실행 상태와 결과 파일 목록

기본 검증은 디코딩, 길이, 무음 여부를 확인하고 채널·샘플레이트·피크·RMS·클리핑 비율을 기록합니다.
실패하면 실행을 FAILED로 남기고 승인하지 않습니다. 통과해도
`AUDIO_CANDIDATE_READY_REVIEW_REQUIRED`이며 `game_ready`는 false입니다.
음색·의도·잡음·클리핑·실제 게임에서의 적합성은 청취 검토가 필요합니다.
ComfyUI와 FFmpeg가 준비돼 있어야 합니다.

기반 템플릿: `audio_stable_audio_3_medium` (Comfy-Org/workflow_templates).
모델 참고: [Stable Audio 3 공식 저장소](https://github.com/Stability-AI/stable-audio-3).
