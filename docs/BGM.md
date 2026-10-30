# Codex/CLI에서 BGM 만들기 (오프라인 계약)

`BGM` 출력 유형은 로컬 ComfyUI의 YuE2 text-to-music 모델로 게임 배경음악 후보를 만듭니다.
상태: **OFFLINE_CONTRACT_PASS / GENERATION_NOT_RUN**. 실제 생성 실행은 아직 한 번도 하지 않았고,
별도 요청과 예산 승인이 필요합니다. workflow `audio_yue2_bgm`은 `EXPERIMENTAL`이므로 자동 라우팅되지
않으며 workflow id와 experimental 허용을 명시해야 합니다.

```powershell
assetpipe create --type bgm --project game-a --asset-id forest_loop --duration 60 --mood calm --tempo-bpm 90 --workflow audio_yue2_bgm --allow-experimental --prompt "Gentle fantasy forest exploration theme, harp, flute, soft strings, warm pads."
```

MCP에서는 기존 `asset_build_brief`에 `requested_output_type: BGM`, `duration_seconds`,
`workflow_id: audio_yue2_bgm`을 전달하고, 다른 BGM 설정은 prepared brief의 `bgm` 객체로 넘깁니다.
새 MCP 도구나 인자를 추가하지 않았습니다(`duration_seconds`가 SFX와 BGM에 함께 쓰입니다).

## Brief `bgm` 설정

| 필드 | 기본값 | 설명 |
| --- | --- | --- |
| `duration_seconds` | 60 | 10–300초. YuE2의 `max_duration`(최대값)으로 전달. 모델이 더 일찍 끝낼 수 있으며 QA가 길이를 검사 |
| `instrumental` | true | 기본은 연주곡. `lyrics`가 있으면 false여야 하며 CLI `--lyrics`는 자동으로 false |
| `lyrics` | `""` | 보컬 곡에서만. 연주곡에서 가사가 있으면 차단 |
| `tempo_bpm` | 없음 | 40–240, 스타일 텍스트에 힌트로 추가 |
| `mood` | 없음 | 스타일 텍스트에 힌트로 추가 |
| `loop` | true | 게임 루프 BGM. CLI `--no-loop`은 일회성 큐 |

프롬프트는 YuE2 `style` 입력으로 들어갑니다. 연주곡이면 "no vocals", 루프면 "no intro, no fade-out"
문구를 덧붙이지만 모델 준수를 보장하지 않습니다. negative prompt는 지원하지 않으며 지정 시 라우팅이 차단됩니다.
SFX `audio` 객체와 BGM `bgm` 객체는 서로 섞을 수 없습니다.

## Workflow

`config/workflows/audio_yue2_bgm.json`은 ComfyUI 0.42.4의 `audio_yue2_text2music` 템플릿
(templates 0.11.94)을 평탄화한 것입니다. `CheckpointLoaderSimple(yue2_3b_int8_convrot.safetensors)` →
`YuE2GenerateMusic` → `EmptyYuE2LatentAudio(seconds=생성 길이)` → `KSampler(32 steps, dpm_2, sgm_uniform)`
→ `VAEDecodeAudio` → `SaveAudio`(FLAC). ABC 계획(`YuE2GenerateABC`)은 비활성(빈 `abc`)으로 단일 경로를
유지합니다. 같은 seed를 음악 생성과 샘플러에 바인딩합니다. 노드 입력은 ComfyUI `object_info`를
읽기 전용으로 캡처한 `tests/fixtures/comfy_object_info_yue2_bgm.json`에 대해 테스트로 검증합니다.

## 저장 결과와 QA

SFX와 같은 구조로 `010_generation/`(원본 FLAC·workflow·파라미터), `020_audio/`(16-bit PCM WAV,
`audio_qa.json`, `bgm_receipt.json`)에 저장합니다. 한 번만 시도하며 재시도·fallback은 없습니다.

기술 QA(실패 시 FAILED, 청취 검토 차단):

- 디코딩, 무음, 요청 길이 대비 ±max(1초, 10%)
- 피크·RMS·클리핑 비율 기록, 클리핑 샘플 1% 초과 시 실패
- FFmpeg EBU R128 통합 라우드니스·LRA·true peak 기록(−30~−8 LUFS 밖이면 경고만, 노멀라이즈 없음)
- `loop: true`: 파일 전체 루프 지점(`loop_start_sample=0`, `loop_end_sample=길이`)을 receipt에 기록하고
  끝→처음 이음매의 샘플 점프(클릭), 앞뒤 0.25초 레벨 차이(6 dB), 인트로/페이드 무음 간격(본문 대비 24 dB)을 검사

자동 트리밍·루프 지점 탐색·보컬 판별은 하지 않습니다. 통과해도 `AUDIO_CANDIDATE_READY_REVIEW_REQUIRED`,
`game_ready: false`입니다.

## 청취 검토

`listening_review_template.json`의 항목: 의도한 분위기, 원치 않는 보컬 없음, 잡음 없음, 들리는 클리핑 없음,
루프 이음매가 들리지 않음(루프일 때만), 게임 맥락 적합성. 직접 들은 뒤 true/false와 PASS/HOLD/REJECT를 기록합니다.

```powershell
assetpipe --root C:/workspace/asset-pipeline bgm-review --run workspace/game-a/runs/forest_loop/<run_id> --review workspace/bgm_observations.json --listened
```

기록은 덮어쓸 수 없고 PASS여도 `game_ready: false`입니다. Factory 라인(`factory plan`)은 아직 BGM을 지원하지 않습니다.
