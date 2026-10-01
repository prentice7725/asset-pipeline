# 매니페스트 출처

런타임 매니페스트는 호스트별로 두 개이며, MCP 연결 설정 `../.mcp.json`과 스킬 폴더 `../skills/`를 함께 사용합니다.

- Codex: `../.codex-plugin/plugin.json`. OpenAI가 문서화한 호환 구조를 따릅니다.
  [Package your plugin](https://developers.openai.com/plugins/build/plugins)
- Claude Code: `../.claude-plugin/plugin.json`. Claude Code 플러그인 형식을 따르며
  `claude plugin validate`로 검증했습니다.

이 세션에서는 공식 Plugin Creator를 사용할 수 없었습니다. Codex 패키지는 가져온 공식 매니페스트
예제를 바탕으로 작성했으며, 로컬 구조·스킬 검증은 Creator 검증과 별개입니다. 등록된 ChatGPT 앱 ID나
.app.json 매핑을 임의로 만들지 않았습니다. ../../docs/plugin/STATUS.json을 참고하세요.
