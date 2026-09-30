# 공통 프롬프트와 모델별 어댑터 사용 안내

Asset Brief의 `prompt_spec`에 모델과 무관한 애셋 요구사항을 작성합니다.
입력은 `schemas/prompt-spec.schema.json`으로 검증하며, 모델별 문법은 컴파일 단계에서 적용합니다.

| 설정 키 | 의미 |
| --- | --- |
| `subject` | 주제 또는 캐릭터 설명. 필수 항목 |
| `appearance` | 외형 특징 목록 |
| `pose` | 자세 또는 동작 |
| `composition` | 구도와 시점 |
| `environment` | 배경과 환경 |
| `lighting` | 조명 |
| `mood` | 분위기 |
| `style` | 표현 스타일 목록 |
| `constraints` | 반드시 지켜야 할 조건 목록 |
| `negative` | 제외할 요소 목록 |
| `textInImage` | 이미지에 표시할 글자 목록 |
| `aspectRatio` | 화면 비율. 예: `1:1`, `3:2` |
| `styleSources` | 선택한 스타일 문구와 출처 URL 목록 |

`masterpiece`, `score_7` 같은 모델 전용 품질 태그나 workflow 노드 ID는 공통 요구사항에 넣지 않습니다.
모델 전용 설정은 프로파일에서 관리합니다. 기존 `prompt` 문자열 입력도 지원하며,
컴파일할 때 공통 형식으로 변환합니다. Asset Brief에 명시된 캐릭터의 정본 특징과 금지 요소는 보존합니다.

## 모델 선택과 컴파일

현재 `config/model_profiles.yaml`에 Anima와 Krea2 어댑터가 연결돼 있습니다.

- Anima는 소문자 설명 태그로 컴파일합니다.
- Krea2는 자연어 문장으로 컴파일하며, 짧게 줄이기 위해 필수 특징을 생략하지 않습니다.

모델 기본값과 품질 접두어는 프로파일에 둡니다. 현재 픽셀 프로파일은 기존 `pixel art, chibi`
접두어를 유지합니다. 성별, 작가, 장비, 품질 점수는 자동으로 추정하지 않습니다.

workflow registry의 `model_profile`이 사용할 프로파일을 지정합니다.
`config/workflows/`의 기존 노드 연결 설정을 재사용해 positive/negative prompt,
가로·세로 크기, seed와 샘플러 설정을 주입합니다.

`aspectRatio`는 실제 생성 크기로 변환합니다. 명시한 해상도와 비율이 충돌하면 실행을 중단합니다.
Negative prompt와 이미지 속 글자 요구도 workflow 선택 조건에 포함합니다.
해당 workflow에서 검증되지 않은 기능은 사용할 수 없습니다.

이미지를 생성하지 않고 컴파일 결과만 확인하려면 다음을 실행합니다.

```powershell
assetpipe compile-prompt --brief examples/prompt_spec_courier.yaml --output workspace/compiled.json
```

실제 생성은 다음과 같이 실행합니다. 예제는 Krea2 workflow를 지정합니다.

```powershell
assetpipe create --brief examples/prompt_spec_courier.yaml --seed 20260930
```

생성 시 `010_generation/compiled_prompt.json`에 공통 요구사항, 어댑터·프로파일 ID,
프로파일 해시를 기록합니다. 실행 manifest에도 이 정보와 실제 프롬프트, 생성 파라미터를 남깁니다.
픽셀 검증과 Static Master 승인 절차는 그대로 적용합니다.

Qwen, Flux, SDXL 어댑터와 workflow는 아직 연결하지 않았습니다.
사용하려면 검증된 프로파일과 실제 workflow 기능 검증 근거를 추가해야 합니다.

## Krea 스타일 사이트 활용

[Krea 공식 저장소](https://github.com/krea-ai/krea-2/blob/main/docs/prompting.md)는 자연어 프롬프트와
상세한 설명을 권장합니다. 웹 제품 가이드에서는 큰 아이디어부터 시작해 스타일을 좁혀가는 방법도
설명합니다. 따라서 이 컴파일러는 프롬프트가 반드시 짧아야 한다는 규칙을 적용하지 않습니다.

[ThetaCursed의 Style Explorer](https://kreastyles.thetacursed.com/)는 Krea 2 Turbo용 커뮤니티
스타일 갤러리입니다. 원하는 표현을 고르는 참고 자료로 사용하되, 현재 설치된 모델에서 같은 느낌이
나오는지는 생성 결과를 보고 검토해야 합니다. 갤러리 전체를 수집하거나 스타일 예제의 캐릭터 설정을
정본으로 확정하지 않습니다.

선택한 스타일 문구를 다음처럼 출처와 함께 기록합니다.

```yaml
prompt_spec:
  subject: fantasy courier  # 만들 캐릭터의 설명
  styleSources:
    - url: https://kreastyles.thetacursed.com/
      description: "<선택한 스타일 설명 문구>"
```

프롬프트에는 직접 입력한 `description`만 들어갑니다. URL은 출처 기록으로 보존하며,
생성할 때 사이트를 내려받거나 URL만 보고 스타일을 자동 해석하지 않습니다.

레퍼런스 이미지 입력은 실제 workflow가 지원하는 기능에 한해 사용할 수 있습니다.
텍스트 기반 workflow에 이미지·스타일 레퍼런스 노드를 임의로 추가하지 않습니다.

Anima 프롬프트 참고 자료: [공식 모델 카드](https://huggingface.co/circlestone-labs/Anima).
