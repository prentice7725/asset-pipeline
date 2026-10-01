# Asset Pipeline 로컬 플러그인

프롬프트, 레퍼런스 이미지, 프로젝트 기획문서를 바탕으로 등록된 로컬 생산 workflow를
사용해 검증된 게임용 애셋을 만듭니다.

```text
Codex 또는 Claude Code 호스트 → 플러그인 지침 + MCP 도구 6개 → assetpipe → 로컬 프로바이더
```

이 패키지에는 지침·참고 문서와 MCP 연결 설정만 들어 있습니다. 엔진은 따로 설치해야 하며,
생산 코드·모델·벤치마크 결과는 복사하지 않습니다.
[로컬 설치 안내](../docs/plugin/LOCAL_SETUP.md)와 [도구 계약](../docs/plugin/MCP_TOOL_CONTRACT.md)부터 읽으세요.

## 호스트별 매니페스트

| 호스트 | 매니페스트 | 공유 구성 요소 |
| --- | --- | --- |
| Codex | `.codex-plugin/plugin.json` | `skills/`, `.mcp.json` |
| Claude Code | `.claude-plugin/plugin.json` | `skills/`, `.mcp.json` |

두 매니페스트는 이름·버전·공유 경로가 같아야 하며 `scripts/package_plugin.py`가 이를 검사합니다.
Claude Code 마켓플레이스 정의는 저장소 루트의 `.claude-plugin/marketplace.json`에 있습니다.

stdio MCP 명령은 호스트 `PATH`에 `assetpipe-mcp`가 있고 `ASSETPIPE_MCP_CONFIG`가 신뢰할 수 있는
로컬 어댑터 설정을 가리킨다고 가정합니다. 설정이 없으면 실행을 거부합니다.

## 검증 상태

- 로컬 SDK/MCP 실행: 검증 완료
- Claude Code: Linux에서 `claude plugin validate`, 로컬 마켓플레이스 설치, MCP 서버 연결 확인
- Codex: 공식 Creator 검증과 실제 플러그인 호스트 설치 미검증. Creator를 쓸 수 없어 M0 전체 PASS는 보류
- ChatGPT 웹 원격 등록은 이 로컬 전용 패키지 범위가 아니며, 공개 엔드포인트나 앱 ID를 만들지 않습니다.

측정된 게이트는 [상태 기록](../docs/plugin/STATUS.json)을 확인하세요. 공개 제출이나 배포는 하지 않습니다.
MCP 스모크 근거가 통과한 뒤 `scripts/package_plugin.py`가 Git 추적 제외 폴더인 `workspace/` 아래에 ZIP을 만듭니다.
