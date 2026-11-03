# rfxgen 합성 SFX (오프라인 계약)

`SFX` 출력 유형 안에 [rFXGen](https://github.com/raysan5/rfxgen)으로 짧은 합성 효과음을 만드는
선택지를 추가했습니다. 새 출력 유형이나 새 MCP 도구는 없습니다.
상태: **OFFLINE_CONTRACT_PASS / GENERATION_NOT_RUN**. 실제 rfxgen 실행은 아직 하지 않았고,
테스트는 가짜 rfxgen으로만 했습니다. workflow `sfx_rfxgen`은 `EXPERIMENTAL`·`explicit_only`입니다.

## 언제 쓰는가

| 필요한 소리 | 경로 |
| --- | --- |
| UI 클릭·확정·취소·경고음, 레트로 탄환·피격·아이템 획득음 | `sfx_rfxgen` |
| 사실적인 금속 충돌·기계·생물·환경음 | 기존 `audio_stable_audio_3_medium` |
| 합성음과 다른 음원을 섞는 소리 | 지원하지 않음. 각 경로 결과를 따로 만들어 청취 검토에서 판단 |

rfxgen은 AI 모델이 아니라 sfxr 계열 파라미터 합성기입니다. 자연어를 해석하지 않으므로
프롬프트는 의도 기록일 뿐 생성에 쓰이지 않습니다.

## 입력: 사람이 만든 `.rfx`만 렌더링

- 생산 경로는 rfxgen GUI에서 만들고 들어본 `.rfx`를 `--input`으로 렌더링하는 방식만 씁니다.
- `--generate <preset>`은 쓰지 않습니다. CLI가 프리셋 결과를 `.rfx`로 저장하지 못해(출력은
  `.wav/.qoa/.raw/.h`뿐) 파라미터가 남지 않고 같은 소리를 다시 만들 수 없기 때문입니다.
- `.rfx`(104바이트: `rFX ` + 버전 200 + 길이 96 + 파라미터 24개)는 렌더링 전에 직접 검사합니다.
  rfxgen은 잘못된 파일을 받아도 경고만 내고 빈 파라미터로 렌더링하기 때문입니다.
- Brief에는 `synth: {engine: rfxgen, params_path, params_sha256}`로 경로와 해시를 고정합니다.
  길이는 `.rfx`가 정하므로 `audio.duration_seconds`와 함께 쓸 수 없습니다.

```powershell
assetpipe create --type sfx --project game-a --asset-id ui_confirm --rfx sfx_library/ui_confirm.rfx --prompt "Short bright UI confirm blip"
```

`--rfx`는 해시를 계산해 Brief에 넣고 `sfx_rfxgen`과 experimental 허용을 지정합니다.
MCP에서는 prepared brief에 같은 `synth` 객체와 `workflow_preferences.id: sfx_rfxgen`을 넣습니다.
`params_path`는 다른 입력처럼 허용 루트 안의 파일이어야 합니다.

## 실행과 기록

- 실행 파일: `config/pipeline.yaml`의 `rfxgen.executable`, 비어 있으면 PATH의 `rfxgen`.
  찾지 못하면 `RFXGEN_UNAVAILABLE`로 출력 폴더를 만들기 전에 멈춥니다.
- 한 번만 실행합니다(`--input params.rfx --output <clip>.wav --format 44100,16,1`). 재시도와
  다른 엔진으로의 대체는 없습니다. 출력 형식은 registry의 16-bit PCM 값만 허용합니다.
- 파라미터와 WAV를 같은 폴더(`010_generation/`)에 두고 파일 이름만 넘깁니다. 긴 경로나 한글 경로를
  rfxgen 인자로 넘기지 않기 위해서입니다.
- `010_generation/`: `params.rfx`(Brief 해시와 같아야 함), `<clip>.wav`,
  `rfxgen_invocation.json`(실행 파일 SHA-256, `--help`에서 읽은 버전, 종료 코드, 로그 일부).
- `020_audio/`: `clip_receipt.json`(`engine: rfxgen`, 파라미터 값과 `randSeed`), `audio_qa.json`,
  통과 시 `listening_review_template.json`.

## QA와 리뷰

- 기본 오디오 QA(디코딩·무음·클리핑 비율 기록)를 그대로 씁니다.
- 길이는 요청값과 비교하지 않고 0.02–10초 범위를 확인합니다. 텍스트 SFX의 1–30초 계약과 분리했습니다.
- 샘플레이트·채널이 요청 형식과 다르면 실패입니다.
- 통과해도 `AUDIO_CANDIDATE_READY_REVIEW_REQUIRED`, `game_ready: false`입니다.
  청취 기록은 기존 `sfx-review`를 그대로 쓰며, 기록 전에 `.rfx`·WAV·QA 해시를 다시 확인합니다.

## 재생성 동일성

`.rfx`에는 난수 시드가 저장되고 rfxgen은 렌더링할 때 그 시드로 난수를 초기화합니다(소스 확인).
따라서 같은 `.rfx`와 같은 빌드면 같은 WAV가 나올 것으로 보지만, 실제로 두 번 렌더링해 해시를 비교하기
전까지 `exact_reproduction: NOT_VERIFIED`로 기록합니다.

## 남은 단계

1. 실제 실행 검증(별도 요청): 사용자 PC의 rfxgen 바이너리로 같은 `.rfx`를 두 번 렌더링해 해시 비교,
   Windows에서 창 없이 종료 코드가 정상인지 확인, 바이너리 해시·버전을 증거로 남깁니다.
   그 전에는 ACTIVE로 올리지 않습니다(registry가 증거 없는 ACTIVE를 거부합니다).
2. 승인 프리셋 라이브러리: UI 확정·취소·경고, 레이저, 피격 `.rfx`를 GUI에서 만들고 청취 승인합니다.
   `.rfx`는 작아 git으로 관리할 수 있고, WAV는 `workspace/`에만 둡니다.

라이선스: rFXGen은 zlib 라이선스입니다.
