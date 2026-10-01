# M1 provider 상세: Codex CLI · Grok CLI

사용법과 실패 모드는 [README](../../README.md#nonpixel-이미지-provider-comfyui-codex-cli-grok-cli)에 있습니다.
이 문서는 **무엇을 직접 확인했고 무엇을 확인하지 못했는지**와 설계 결정의 이유를 기록합니다.

## 1. 직접 확인한 사실

설치한 버전: `codex-cli 0.159.3`, `grok 1.0.46`. 둘 다 npm 패키지(`@openai/codex`, `@xai-official/grok`)로 격리된 폴더에 설치해서 확인했습니다.

| 항목 | 확인 방법 |
| --- | --- |
| `codex exec`가 stdin 프롬프트(`-`), `--json`, `-o`, `-C`, `--skip-git-repo-check`, `--ignore-user-config`, `--ignore-rules`, `--sandbox`를 지원 | `codex exec --help` |
| Codex에 `image_generation` 기능이 `stable true`로 존재 | `codex features list` |
| 미로그인 시 `codex login status`가 `Not logged in` 출력 | 직접 실행 |
| Grok의 `--prompt-file`, `--output-format json`, `--cwd`, `--tools`, `--no-subagents`, `--no-plan`, `--disable-web-search`, `--max-turns`, `--permission-mode`, `--allow` | `grok --help` |
| 미로그인 시 `grok models`가 `You are not authenticated.` 출력, 헤드리스 실행은 `Not signed in`과 `XAI_API_KEY` 안내로 종료 | 직접 실행 |
| Grok에 `image_gen`, `image_edit` 도구가 있고, `aspect_ratio` 허용값·`image_edit`의 레퍼런스 이미지 필수 조건·저장 경로 반환(세션 폴더의 `images/N.jpg`)이 도구 설명에 있음 | 바이너리 문자열 분석 (실행 확인 아님) |
| 환경변수 `GROK_HOME`, `XAI_API_KEY`, `GROK_CLAUDE_{AGENTS,HOOKS,MCPS,RULES,SKILLS}_ENABLED` 존재 | 바이너리 문자열 분석 |
| `GROK_CLAUDE_*_ENABLED=0`은 Claude에서 가져온 스킬을 끄지만, 설치된 **플러그인의 MCP 서버는 계속 로드됨** | `grok inspect` 전후 비교 |

마지막 항목이 재귀 호출 가드가 필요한 근거입니다. 사용자 환경에 이 저장소의 플러그인이 설치돼 있으면, Grok이 그 MCP 서버를 띄워 다시 `asset_generate`를 호출할 수 있는 경로가 실제로 존재했습니다. 자식 프로세스의 `ASSETPIPE_PROVIDER_DEPTH`가 그 경로를 막습니다.

## 2. 문서로만 확인한 사실 (직접 실행하지 못함)

- Codex의 내장 `image_gen` 도구가 결과를 `$CODEX_HOME/generated_images/` 아래에 저장한다는 점, ChatGPT 로그인으로 별도 API 키 없이 동작한다는 점. 공개 문서·블로그 설명이며 이 환경에서는 로그인할 수 없어 실행하지 못했습니다.

## 3. 검증되지 않은 가정 (E2E에서 확인 필요)

실제 계정으로 생성해 봐야 알 수 있는 항목입니다. 틀렸다면 **조용히 잘못된 결과를 내는 대신** `OUTPUT_MISSING`, `REFUSED`, `CLI_EXIT_NONZERO` 등으로 실패합니다.

| provider | 가정 | 틀렸을 때 |
| --- | --- | --- |
| Codex | `--sandbox read-only`에서도 `image_gen`이 동작하고 `generated_images`에 저장됨 | `OUTPUT_MISSING`. 필요하면 샌드박스 정책을 조정 |
| Codex | `-c project_doc_max_bytes=0`이 유효한 설정 키(`login`에는 `--strict-config`가 없어 검증 불가). 알 수 없는 키는 무시되므로 해롭지 않고, 작업 폴더가 프로젝트 트리 밖이라 1차 격리는 그쪽이 담당 | 영향 없음 |
| Codex | JSONL 이벤트의 `thread_id`, `usage`, `model` 키 이름 | 값이 비어 `usage_support: NOT_REPORTED`로 기록될 뿐 생성에는 영향 없음 |
| Grok | `--permission-mode dontAsk --allow image_gen` 조합으로 도구 호출이 승인됨 | 도구가 거부돼 `OUTPUT_MISSING`/`REFUSED`. registry의 `backend.cli_args`로 조정(격리를 약화하는 인자는 로더가 거부) |
| Grok | 출력 JSON에 저장 경로가 들어 있거나 `~/.grok/sessions/` 아래에 파일이 생김 | 두 방법 모두 실패하면 `OUTPUT_MISSING` |
| Grok | `image_edit` 경로(레퍼런스 이미지 복사본의 절대경로 전달) | 이 경로는 E2E 범위에 포함하지 않았음 |

## 4. 설계 결정

**이미지 수집은 실행 전 스냅샷과의 비교로 합니다.** 처음에는 "실행 시각 ±2초 안에 만들어진 파일"을 썼는데, 직전 실행이 방금 만든 이미지를 다음 실행이 자기 결과로 오인하는 결함을 테스트에서 발견했습니다. 지금은 실행 전에 저장 폴더의 이미지 목록을 기록하고, 실행 후 새로 생겼거나 갱신된 파일만 후보로 봅니다(`test_previous_runs_image_is_never_mistaken_for_a_new_result`). 다른 프로세스가 같은 폴더에 동시에 이미지를 만들면 구분할 수 없으므로 하나보다 많이 발견되면 고르지 않고 `OUTPUT_AMBIGUOUS`로 멈춥니다.

**작업 폴더는 프로젝트 트리 밖의 임시 폴더입니다.** 프로젝트 안에 만들면 CLI가 상위 폴더의 지침 파일(`AGENTS.md` 등)을 자동으로 읽을 수 있어서 프로젝트 문서가 모델에 전달됩니다. 감사용 기록(프롬프트, 마스킹된 로그, 원본 이미지)은 실행 폴더로 복사해 남깁니다.

**자동 재시도·fallback이 없습니다.** 타임아웃된 요청은 계정에서 이미 처리됐을 수 있고, 실패한 요청을 다른 provider로 넘기면 사용자가 고른 provider와 다른 결과가 나옵니다. 둘 다 중복 과금이나 의도하지 않은 결과로 이어질 수 있어서 한 번 실행하고 멈춥니다.

**ACTIVE 승격은 코드로 막혀 있습니다.** 로더가 증거 파일(`provider_id`와 `result: REAL_GENERATION_VERIFIED`)이 없는 CLI provider의 `ACTIVE`를 거부합니다. 문서의 약속이 아니라 로딩 시점의 검사입니다.

## 5. 테스트가 검증하는 것과 못 하는 것

`tests/unit/test_cli_providers.py`는 `tests/fakes/`의 가짜 CLI로 provider 코드의 동작을 검증합니다.

- 검증함: 진단 상태 분류, 인증 미설정·거절·타임아웃·출력 누락·모호한 출력·비정상 종료 처리, 환경변수·작업 폴더 격리, 프롬프트 stdin 전달, 비밀 마스킹, 재귀 차단, 재시도·fallback 없음, manifest 기록, QA 게이트, 라우터·registry 규칙.
- 검증하지 못함: **실제 CLI가 실제로 이미지를 만드는지**, 실제 출력 형식, Windows 실행. 가짜 CLI의 통과는 E2E를 대신하지 않습니다.
