# Pinned MCP 보안 패치 반영 준비 — 2026-10-10

상태: **PREPARATION_COMPLETE / ACTIVATION_BLOCKED**.
운영 교체·재시작·프로세스 종료·실생성·Golden 승인·provider ACTIVE 승격·SOT 변경은 수행하지 않았다.
추가 보안 리뷰 실패 때문에 승인만으로 바로 활성화할 수 없다. 아래 결함 수정과 재검증이 먼저 필요하다.

## 보존 및 준비한 candidate

- 보안 커밋: `e7a5551b4db94ae29277a77fd74d6b0bd6e1d0bc`.
- 운영 스냅샷: `workspace/mcp_runtime/5d6353f-portrait-delivery-359e12c9f693`.
  정체성은 base commit `5d6353ffa58a05e80a1821d402ca29fdf67da6cf` + 기존 portrait delivery 로컬 패치이다.
- 작업 저장소의 오래된 main 전체를 배포하지 않았다. 운영 스냅샷 복사본에 보안 diff만 적용했으며,
  `git apply --check` 후 13개 변경 파일이 적용됐다. 기존 portrait 기능과 설정을 보존하고 파일을 삭제하지 않았다.
- candidate: `workspace/security/runtime-prep-e7a5551/candidate`.
- candidate 트리 해시: `e749108d97d04a0f4ab65ee78fc4ebbba5d39e880d68fa5691a2afb9dcfc80e1`.
- 봉인 zip: `workspace/security/runtime-prep-e7a5551/candidate_runtime.zip`, 875개 파일.
  SHA-256: `a49b3f8d7d158cc42e1513f916e09e769fef0d6a9113b0cf3a7e21199e533a0e`.
  이는 보존용 검증 artifact이며 **활성화 승인 artifact가 아니다**.
- 원본 백업: 같은 준비 폴더의 `backup/pinned_runtime.zip`, 929개 파일.
  SHA-256: `825092a0fedf04e232e4a38b3ddf912dcfbf43b863fc876034e15101f6d8412c`.
  zip 각 파일의 해시를 원본과 비교했다. `launch.py`, `revision.txt`, `adapter.yaml`도 별도로 백업했다.
- 최종 보존 검사에서 운영 런타임, 세 host 파일, 기존 미커밋 파일, 테스트 중 candidate 변경 모두 0개였다.
  현재 작업에서 새로 만든 이 문서 외에는 저장소 source를 수정하지 않았다.

## 실행 파일·인터프리터·import 식별

Host 등록: `C:/Users/seung/.codex/config.toml`의 `mcp_servers.asset_pipeline`.
등록 command는 `C:/workspace/asset-pipeline/.venv/Scripts/python.exe`, args는
`C:/workspace/asset-pipeline/workspace/mcp_runtime/launch.py`이며 startup timeout은 30초다.
Host 설정은 읽기만 했다. 런타임 README의 오래된 revision 설명 대신 실제 `revision.txt`를 기준으로 확인했다.

Python은 3.11.9, base interpreter는
`C:/Users/seung/AppData/Local/Programs/Python/Python311/python.exe`다.
Launcher가 pinned runtime의 `src`와 루트를 `sys.path`와 `PYTHONPATH`에 앞세우고 cwd를 옮긴다.
동일 import 경로를 별도 `-B` 프로세스에서 재현해 api, CLI, MCP server/adapter,
Codex/Grok provider와 approval 모듈이 해당 pinned 폴더에서 로드됨을 파일 경로·해시로 확인했다.
운영 프로세스 메모리에 주입하거나 live `sys.modules`를 직접 읽은 것은 아니다.

확인된 의존성: MCP 1.30.0, Pillow 12.2.0, PyYAML 6.0.3, jsonschema 4.26.0,
NumPy 2.4.6, OpenCV 5.0.0.93, pytest 9.1.1, rembg 2.0.69, package metadata 0.1.0.
Package version 0.1.0과 MCP SDK의 server version 1.30.0만으로 코드 revision을 식별할 수 없어
별도 트리 해시와 보안 커밋을 기록했다. candidate 안의 기존 `runtime_provenance.json`은
원본 스냅샷 출처이며, 새 candidate의 권위 있는 출처는 준비 폴더의 `candidate_provenance.json`이다.

## 운영 세션·작업 관찰

2026-10-10 16:08 JST 전후 읽기 전용 관찰:

| Launcher PID | Interpreter child PID | 부모 app-server PID | Windows session |
| --- | --- | --- | --- |
| 9808 | 29168 | 9588 | 11 |
| 46100 | 3508 | 9588 | 11 |
| 49888 | 29692 | 9588 | 11 |

각 체인의 command line, executable, creation time, parent creation time을 기록했다.
3개의 MCP 실행 체인을 관찰했으나 각각의 대화 소유권·잔류 여부를 확정하지 않았다.
세션 11은 Windows session이며 MCP 대화/session ID가 아니다. 어떤 기존 프로세스도 종료하지 않았다.

기존 generation receipt 4개가 참조하는 PID 31904, 37708, 41584, 24716은 관찰 시점에 없었다.
manifest는 3개 FAILED, 1개 AUDIO_CANDIDATE_READY_REVIEW_REQUIRED였다.
receipt의 STARTING은 stale 값이며 수정하지 않았다.
Assetpipe create/Codex exec/Grok prompt-file 생성 프로세스는 관찰되지 않았다.
로컬 ComfyUI `/queue` GET에서 실행·대기 큐가 모두 비어 있었다. Queue에 새 작업을 제출하지 않았다.
이 결과는 관찰 시점의 스냅샷이며 교체 직전 재확인해야 한다.

## 격리 검증 결과

검증 source/process/config/output은 운영과 분리했다. `test-env`는 별도 venv이며,
누락된 MCP·pywin32 의존성 preflight 실패를 해결한 후 검증했다.
운영 site-packages를 읽기 전용으로 공유하고 bytecode 쓰기를 비활성화했다.
운영 패키지를 설치·교체하지 않았으며 네트워크 패키지 다운로드도 하지 않았다.
따라서 완전히 독립된 dependency installation 검증은 아니다.

- 전체 회귀: **407 passed, 1 skipped**, 143.23초, 실패·오류 0개. 신규 보안 31개 테스트는 모두 실행됐다.
- Skip: `tests.unit.test_assetpipe.test_direct_frames_are_identical_to_verified_legacy`.
  격리 위치에 로컬 migration benchmark data가 없어 건너뛰었다. 픽셀 동등성 증거로 대신하지 않는다.
- 실제 stdio initialize/tools-list와 exact six/strict schema 통과.
  원본 pinned server와 candidate의 6개 tool 정의 전체가 같았다.
- 6개 도구의 안전한 분기 호출, 외부 경로·traversal·잘못된 타입·추가 인자 거부,
  nested source_manifest·inspection evidence·symlink escape 거부 통과.
- 운영과 같은 `C:/workspace` source root에서도 그 밖의 임시 fixture 접근 거부를 확인했다.
- CLI help exit 0. 테스트 서버들은 stdin EOF 후 exit 0. 기존 운영 프로세스는 건드리지 않았다.
- capability 호출은 offline readiness stub이며 실제 provider 인증·가용성 검증이 아니다.
  테스트 서버는 provider 생성과 `-m assetpipe` child generation을 추가 차단했다.
  실제 Codex/Grok/ComfyUI 생성 요청 0회, 모델 자동 전환·재시도·fallback 0회.

## 보안 리뷰 결함 — 활성화 차단

**P1: 동일 공유 루트 내부의 세션 디렉터리 alias를 다른 세션 출력으로 구분하지 못한다.**
`src/assetpipe/providers/cli_runner.py`의 `correlated_images`는
`scope = session_parent / reported_session`을 공유 부모 안에 resolve되는지만 확인한다.
보고된 세션 디렉터리 자체가 sibling `other_session`으로 향하는 symlink라면 이 검사를 통과하고,
scan 기준도 그 sibling으로 resolve된다. 새 `other_session/other.png`가 보고된 세션 결과로 수집된다.
Codex와 Grok 모두 합성 fixture로 ACCEPTED를 재현했다.
근거: `workspace/security/runtime-prep-e7a5551/session_alias_review.json`의 review_gate FAIL.
기존 31개 보안 테스트는 외부-root escape를 검증하지만 shared-root 내부의 session alias는 놓쳤다.

수정 전 candidate를 운영에 활성화하지 않는다. 세션 이름과 실제 세션 디렉터리 정체성을 묶고,
해당 디렉터리의 symlink/junction alias를 fail closed로 거부하는 보완이 필요하다.
Codex/Grok 양쪽에 sibling alias 회귀를 추가하고 전체 테스트·MCP 계약·원본 보존을 재검증한 뒤
새 해시·새 봉인 archive를 만들어야 한다. 전역 이미지 fallback을 복구하는 해결은 금지한다.
이번 준비 작업에서는 source 보안 패치를 추가 수정하지 않았다.

## 별도 승인 후 실행할 설치·교체 계획

1. 먼저 P1 수정·새 candidate 검증·재봉인을 완료한다. 현재 FAIL gate를 건너뛰지 않는다.
   승인 대상은 수정된 정확한 archive SHA-256, tree SHA-256, target runtime ID와 적용 config이다.
2. 사용자 승인 후 새 immutable directory를 `workspace/mcp_runtime/<새-검증-ID>`에 만든다.
   기존 디렉터리·백업을 덮어쓰지 않는다. Zip 경로 containment와 파일별 해시를 검증한다.
   `.venv`와 dependency versions는 이번 계획에서 그대로 유지한다. 의존성 변경은 별도 검증 대상이다.
3. 실제 설치 위치에서 isolated import·CLI help·MCP schema/denial smoke를 재실행한다.
   test stub/guard wrapper를 운영 launcher에 포함하지 않는다. 실생성 E2E는 별도 과금 승인 없이는 하지 않는다.
4. 작업 제출을 사용자 관리 하에 잠시 멈추고 receipt/프로세스/ComfyUI 큐를 다시 확인한다.
   진행 중 작업이 있거나 세션 소유권을 확인할 수 없으면 전환을 보류한다.
   각 MCP client는 소유자가 정상적으로 연결을 닫게 한다. 임의 PID kill/taskkill은 사용하지 않는다.
5. Quiescence가 확인된 창에서 `adapter.yaml`의 core_root만 새 runtime으로 설정하고,
   source_roots `C:/workspace`, 기존 output_root는 유지한다. 이어 revision.txt를 새 ID로 바꾼다.
   각각 temp file 작성 후 동일 파일시스템 atomic replace를 사용한다.
   두 파일의 전환은 한 번에 atomic하지 않으므로 그 사이 launcher가 시작되지 않게 해야 한다.
   기존 `launch.py` 및 사용자 host 등록은 변경할 필요가 없다.
6. 사용자 관리 하에 정상 재연결하고 executable/import hash·initialize·6개 계약·denial을 확인한다.
   전체 gate 통과 전 generation 재개를 승인 완료로 간주하지 않는다.

## 백업·롤백 절차

- 전환 전에 다시 포인터/config/launcher 해시와 현재 스냅샷을 백업하고 위 기존 백업과 차이를 확인한다.
- 전환 gate 실패 시 새 생성 요청을 받지 않고 연결을 닫아 둔다. 자동 retry나 다른 provider로 전환하지 않는다.
- 사용자 관리의 quiescence 아래 백업 `revision.txt`와 `adapter.yaml`을 복구할 수 있다.
  손상된 source 복원이 필요하면 검증된 backup zip을 **새 복구 디렉터리**에 안전하게 풀고 해시를 검사한다.
  기존 런타임·미커밋 checkout·산출물은 삭제/덮어쓰기하지 않는다.
- 이전 런타임에는 제거 전 global fallback 코드가 있으므로 **파일 복원과 서비스 재개를 분리한다**.
  이전 버전을 자동 재활성화하지 않는다. fallback 차단이 유지된 검증 버전을 확보할 때까지 MCP는
  비활성/미연결 상태로 두는 것이 fail-closed 롤백이다. 과금 요청을 재전송하지 않는다.

## 미해결 제한 및 근거 위치

P1 session alias, 체크/사용 간 파일 변경 race, truthful unique CLI session ID 의존,
운영 source root가 넓은 `C:/workspace`라는 점, 허용 루트 밖 historical provider source_path가 있으면
inspect/provenance가 fail closed로 차단될 수 있다는 호환성 위험이 남는다.
실제 CLI correlation E2E와 독립 dependency install, legacy pixel benchmark, live process memory import,
여러 운영 client의 종료/재연결까지 검증한 것은 아니다. 어떤 항목도 passing pytest로 대체하지 않는다.

준비 근거는 `workspace/security/runtime-prep-e7a5551/`에 보존했다:
`preservation_before/after.json`, `backup_verified.json`, `patch_check.json`,
`candidate_provenance.json`, `sealed_candidate.json`, `operational_import_probe.json`,
`candidate_import_probe.json`, `process_inventory.json`, `job_inventory.json`, `comfy_queue.json`,
`protocol_summary.json`, 각 protocol report, `production_equivalent_path_test.json`,
`pytest.log/xml`, `session_alias_review.json`.

최종 결정: **운영 교체는 미실행, P1 수정·재검증과 별도 사용자 승인 전 활성화 금지**.
