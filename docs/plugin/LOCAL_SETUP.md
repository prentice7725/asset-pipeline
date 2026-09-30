# 로컬 설치 및 연결 안내

Python 3.11 이상을 사용해 `asset-pipeline` 저장소 폴더에서 설치합니다.
아래 명령은 `.venv` 가상환경이 이미 준비돼 있다고 가정합니다.

```powershell
.venv/Scripts/python.exe -m pip install -e ".[dev,motion,mcp]"
Copy-Item config/mcp_adapter.example.yaml config/mcp_adapter.local.yaml
```

## 접근 경로 설정

복사한 로컬 설정 파일의 다음 항목을 환경에 맞게 수정합니다.

| 설정 키 | 의미 |
| --- | --- |
| `core_root` | Asset Pipeline 저장소의 루트 경로 |
| `source_roots` | 도구가 읽을 수 있는 프로젝트 소스·승인된 애셋 폴더 목록 |
| `output_root` | 실행 결과를 저장할 폴더 |

상대 경로는 설정 파일이 있는 폴더를 기준으로 해석합니다.
`source_roots`에 지정한 폴더는 미리 존재해야 하며, `output_root`는 자동으로 생성합니다.
이 설치에서 필요한 소스·승인된 애셋 폴더만 허용하세요.
로컬 설정 파일과 생성된 실행 결과는 Git 추적에서 제외합니다.

예제 설정은 `examples/`와 `tests/fixtures/`만 소스로 허용합니다.
기존 `pixel-pipeline`의 벤치마크 폴더는 허용하지 않으므로,
그 데이터를 로컬 검증에 사용하려면 필요한 폴더를 직접 추가해야 합니다.

## 프로젝트별 결과 저장

`output_root`는 공통 결과 폴더 하나로 지정합니다. 각 요청의 Asset Brief에
`project_id`를 지정하면 프로젝트 폴더 아래에 실행 결과와 요청 기록을 저장합니다.

```yaml
project_id: game-a
asset_id: courier
```

```text
output_root/
  game-a/
    runs/courier/<실행ID>/
    requests/
  game-b/
    runs/courier/<실행ID>/
    requests/
```

Codex에는 “game-a 프로젝트로 이 캐릭터를 만들어줘”라고 요청하면 됩니다.
`asset_build_brief`의 `project_id` 또는 준비된 Brief의 `project_id`로 전달합니다.
애니메이션을 이어서 만들 때도 기존 Brief의 프로젝트를 유지합니다.
프로젝트를 생략하면 `default` 폴더에 저장하며, 소스 경로로 프로젝트를 추측하지 않습니다.
프로젝트 ID는 영문·숫자로 시작하고 영문·숫자·하이픈·밑줄만 사용하며 최대 64자입니다.
기존 실행 결과도 실행 ID로 계속 조회할 수 있습니다.

CLI는 `assetpipe create --project game-a ...`로 지정할 수 있습니다.
CLI의 기본 저장 위치는 `workspace/game-a/runs/애셋ID/실행ID/`이며,
명시적인 `--output`은 사용자가 지정한 경로를 그대로 사용합니다.

## 서버 실행

서버를 직접 실행하려면 다음 명령을 사용합니다.

```powershell
.venv/Scripts/assetpipe-mcp.exe --config config/mcp_adapter.local.yaml
```

서버는 표준 입출력(stdio)으로 JSON-RPC 메시지를 주고받습니다.
따라서 실행 후 콘솔에 별도 안내 없이 대기하는 것은 정상입니다.
실제 사용 시 MCP 클라이언트가 서버의 표준 입력과 출력을 연결합니다.

연결을 닫거나 입력을 종료(EOF)하거나 `Ctrl+C`를 누르면 서버를 종료합니다.
이미 시작한 `assetpipe` 생성 작업은 계속 실행되며, 재연결 후 상태를 조회할 수 있습니다.

## 플러그인에서 연결

포함된 플러그인의 연결 설정을 사용하려면 MCP 호스트를 시작하기 전에 다음을 준비합니다.

1. 가상환경의 `Scripts` 폴더를 호스트의 `PATH`에 추가합니다.
2. `ASSETPIPE_MCP_CONFIG` 환경변수를 로컬 설정 파일의 절대 경로로 지정합니다.

이 환경변수가 적용된 프로세스에서 MCP 호스트를 시작해야 합니다.
플러그인은 모델이 제공한 실행 인자 없이 `assetpipe-mcp`를 실행합니다.

다른 방법으로는 Codex의 로컬 MCP 설정에 실행 파일의 절대 경로와
`args = ["--config", "<로컬 설정 파일의 절대 경로>"]`를 지정할 수 있습니다.
설정 후 클라이언트를 다시 시작해 연결 설정을 불러옵니다.

ComfyUI는 로컬에서 실행하고 Aseprite와 FFmpeg도 설치해 두세요.
`asset_capabilities` 도구로 환경 준비 상태를 확인할 수 있습니다.
모델이나 노드가 빠져 있으면 실제 생성이 실패할 수 있으며,
실패 내용은 코어의 실행 manifest에 기록합니다.

## 패키지 형식과 남은 검증

패키지는 OpenAI가 지원하는 `.codex-plugin/plugin.json`과 `.mcp.json` 호환 구조를 사용합니다.
[공식 패키징 문서](https://developers.openai.com/plugins/build/plugins)에서는
Plugin Creator를 통한 로컬 마켓플레이스 연결과 등록된 ChatGPT 앱 연결을 설명합니다.
현재 환경에서는 Creator를 사용할 수 없어 마켓플레이스나 계정 설정을 변경하지 않았습니다.

로컬 MCP SDK 실행 검증은 실제 호스트에 플러그인을 설치했다는 의미가 아닙니다.
ChatGPT의 원격 개발자 모드 연결에는 접근 가능한 지원 MCP 연결이 필요합니다.
M0 범위에서는 클라우드 서비스 추가나 원격 배포를 하지 않으며,
앱 ID나 ChatGPT 연결 정보를 임의로 만들지 않습니다.

공식 Plugin Creator와 실제 대상 호스트 환경이 준비되면 해당 검증을 완료해야 합니다.
현재 로컬 실행 검증과 Creator·호스트 검증 상태는 `STATUS.json`에 구분해 기록합니다.
