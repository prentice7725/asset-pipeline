> Historical report (2026-10-10), published for traceability. ACTIVATION_READY_FOR_APPROVAL describes that tested candidate only; it is not a fresh seal, current runtime integrity claim, or deployment approval. See the later [canonical Grok collection fix](../m1/GROK_SESSION_COLLECTION_20261012.md). No candidate is rebuilt by publishing this note.

# SECURITY-RELEASE-BLOCKERS — 2026-10-10

판정: **ACTIVATION_READY_FOR_APPROVAL**. 운영 스냅샷 기반 최종 후보에서 전체 필수 테스트 실패 0건, P1/P2 보안 게이트 PASS, MCP 계약 일치, portrait/project 보존, 새로운 후보 검증·봉인을 확인했다. 운영 활성화와 실제 모델 생성은 수행하지 않았다. 이 판정은 운영 교체 승인, provider ACTIVE 승격, 이미지 품질 승인 또는 SOT 승인이 아니다.

## 원인과 최소 수정

### Grok Windows 경로

기존 9개 실패의 공통 최초 예외는 `GrokCliProvider.child_env`의 session parent `mkdir`였다. 설정된 home 아래에 `sessions / quote(str(job.work), safe='')`를 만들면서 cwd의 경로 전체를 다시 포함했고, `%3A/%5C` 인코딩으로 길이가 늘었다. 이전 baseline에서 일반 모드 268자와 API-key 모드 301자 경로의 `WinError 3`를 기록했다. 후속 manifest/오류 코드 assertion 실패는 이 최초 예외의 결과였다.

새 구현은 Windows `GetShortPathNameW`로 **같은 실제 디렉터리**의 기존 8.3 이름을 얻고, `resolve(strict=True)`로 동일성을 확인한다. `--cwd`와 저장 부모의 인코딩에는 정확히 같은 이름을 쓴다. 임의 문자열 절단이나 digest를 native CLI의 cwd 대신 사용하지 않는다. API-key의 빈 격리 홈은 기존 configured job root 내부의 `h`로 단축했으며 사용자 인증 홈/플러그인을 복사하지 않는다. 기존 API-key 격리 assertion을 유지했다.

Windows 디렉터리 생성 한계 248자, 파일 경로 한계 260자, 인코딩된 단일 component 255바이트를 사전 검사한다. 8.3을 얻지 못하거나 길이 예산을 만족하지 못하면 `SESSION_PATH_UNAVAILABLE` 또는 `SESSION_PATH_TOO_LONG`으로 생성 전에 차단한다. 짧은 이름이 제공되지 않는 볼륨에서도 원래 이름이 예산 내라면 사용할 수 있다. 어떤 경우도 shared home scan이나 provider fallback으로 전환하지 않는다.

각 job에 새로운 UUID를 발급해 실제 CLI의 문서화된 `--session-id`에 전달한다. 보고된 ID가 해당 job과 다르면 `OUTPUT_UNCORRELATED`로 차단한다. 설치된 Grok의 실제 `--help` 실행으로 이 옵션의 신규 세션 UUID 계약을 확인했으며, 생성 요청은 보내지 않았다. NTFS의 디렉터리 동일성 검증과 job별 UUID를 함께 사용하고, 네 작업의 부모·ID·이미지가 각각 고유함을 합성 동시 테스트로 확인했다.

8.3 경로를 canonical 경로로 확장할 때 다시 길어지는 문제와 Windows 일반/extended namespace 표현 차이는 공통 CLI 파일 검증 함수에서 해결했다. 비교와 scan에 일관된 resolved Windows namespace를 쓰되 일반 길이 반환 경로의 기존 표현을 유지하고, 실제 long-path 읽기에 필요한 namespace는 보존한다. before snapshot의 공개 key 형식도 유지했다. P1 `lstat` 기반 symlink/junction 거부, 수집 후 재검사, freshness, containment, ambiguity, hash/review/pixel 게이트는 통과했다.

### Recipe 개수와 Style 오류

91→92의 추가분은 portrait가 아니라 공통 `model_recipes.yaml`에 들어간 `STYLE-103/grok_imagine` 한 개였다. 원본에 `SKY-only user-selected project-primary overlay`라고 적혀 있고 상태는 `UNTESTED`였다. Explorer 출처 claim과 해당 프로젝트의 style fingerprint가 들어 있어 공통 STYLE-103 fingerprint와 맞지 않았다. 원본 내용과 hash는 `recipe_scope_audit.json`에 보존했다. 이 출처 claim을 실제 작품/승인 증거로 인정하지 않는다.

원본 recipe를 같은 파일의 `project_recipes/SKY_RENDEZVOUS/STYLE-103/grok_imagine`으로 옮겼다. 선택기는 정확히 그 project ID의 scoped index에서만 이를 읽으며, 기존 SOT/Style Pack recipe가 우선한다. 기존 version/status/fingerprint/prompts/sources를 유지했고 SOT 파일은 변경하지 않았다. 실제 recipe 출처를 `recipe_file`에 기록하도록 했다. 공통 inventory는 원래 **91개: TESTED 2, UNTESTED 89**이며, project recipe는 여전히 UNTESTED이고 자동 선택/다른 프로젝트 사용은 차단된다. 승인 상태를 승격하지 않았다.

공개 오류 계약은 `RoutingBlocked`(ValueError 하위 클래스)의 메시지와 `details.rejected_candidates`이며, 이 경로에 별도의 stable error code는 없었다. 잘못된 공통 등록 때문에 원래 absent-recipe 조건이 fingerprint-mismatch 조건으로 바뀐 것이 원인이었다. 범위를 바로잡아 공통/다른 프로젝트에서는 원래 `No style-compatible recipe` 차단을 복구했다. 실제 bad fingerprint는 계속 `Recipe style fingerprint mismatch`로 거부한다. 기대값 91이나 기존 오류 assertion을 바꾸지 않았고, 두 조건의 public details를 추가 검증했다.

## 최종 검증

| 항목 | 결과 |
| --- | --- |
| 전체 pytest | **446 PASS, 0 FAIL, 1 SKIP, 0 ERROR / 총 447개** |
| 보안 회귀: 기존 P1/P2, nested provenance, Windows case/reparse, release blockers | **70 PASS, 0 SKIP** |
| P1 identity gate 제거한 격리 공격 baseline | sibling alias 8 FAIL, 31 deselected |
| 최종 P1: Codex/Grok × symlink/junction × scan/explicit | 같은 8개 PASS |
| 긴 경로/격리/동시 작업/세션 출처/recipe 범위 추가 회귀 | 9 PASS |
| 기존 portrait/project 계약 | 13 PASS |
| MCP initialize/tools/list | PASS |
| 정확히 6개 도구의 전체 schema 비교 | 운영 스냅샷과 동일 |
| 여섯 도구 safe dispatch 및 traversal/nested reference/symlink 거부 | PASS |
| CLI help 및 실제 import 경로 검사 | PASS |
| 운영·미커밋·기존 immutable 후보·최종 후보 무결성 | PASS, 변경 0개 |

SKIP 1개는 격리 복사본에 로컬 migration benchmark 데이터가 없는 기존 legacy 직접 프레임 비교다. 이 benchmark 동등성 검증은 여전히 미완료이며 PASS로 바꾸지 않았다. 새 무조건 skip이나 테스트 삭제는 없다. Windows 전용 8.3 테스트의 platform 표시는 이 Windows 실행에서 skip을 만들지 않았다.

MCP capability readiness는 외부 호출을 막은 offline stub이다. provider 및 생성용 child process는 guard로 차단하고, negative calls가 guard 이전에 거부됨을 확인했다. 테스트 소유 stdio 서버는 EOF 후 exit 0을 관찰했다. 기존 활성 MCP는 종료하지 않았다. 기존 timeout 테스트가 종료하는 것은 직접 생성한 synthetic CLI worker뿐이다. 반복 MCP 검증의 fixture 재사용 오류는 별도로 보존하고 고유한 새 fixture 디렉터리에서 최종 PASS를 얻었다.

Python 3.11.9의 기존 격리 test venv에서 candidate source/import를 확인했다. 운영 dependency 디렉터리는 읽기만 공유하며 설치/재설치를 하지 않았다. 실제 provider 인증, 모델 실행, 과금 또는 live readiness를 확인했다는 뜻은 아니다.

## 출처·최종 봉인

- 운영 출처: `workspace/mcp_runtime/5d6353f-portrait-delivery-359e12c9f693`.
- 원본 provenance: base commit `5d6353ffa58a05e80a1821d402ca29fdf67da6cf`, source hash `359e12c9f6930f4d5d0daaabf582d658ea6fec98f1ef801bcc92766eaeb9a3af`와 기존 로컬 portrait 패치. 실제 시작 파일 manifest를 별도 기록했다.
- 보안 source commit: `51854d66ef4300fce5e802b06032e7e6587eca50`(기존 `e7a5551` 포함), 게시된 merge `abd7fe246b36be3d79a8ea1ed9d7a022339f16d0`.
- 그 보안 diff를 운영 스냅샷에 맞게 적용한 뒤 release 수정 6개 파일을 반영했다. 오래된 main 전체로 운영 source를 덮어쓰지 않았다.
- Review diff: `workspace/security/release-blockers-20261010/release_blockers.patch`.
- Review diff SHA-256: `6b04db6699bab9751de5520a99de1cd520b5337ef9943e7854556d53782b93d0`.
- Candidate ID: **`security-release-20261010-572b76ffe1e4`**.
- Candidate 위치: `workspace/security/release-blockers-20261010/candidate`, **896개 파일**.
- Tree SHA-256: **`572b76ffe1e456da42568c890bb94d101c0e1693c0e506c4396b5b0349ac0873`**.
- ZIP SHA-256: **`a0beb2bda1c62ea0589addb0b51917817b2519d53aac61decb888f9295a96f02`**.
- ZIP: `workspace/security/release-blockers-20261010/security-release-20261010-572b76ffe1e4.zip`.

Tree hash는 sorted compact JSON `relative path → file SHA-256` manifest 바이트의 SHA-256이다. ZIP 모든 entry의 실제 content hash를 manifest와 대조했다. 후보와 ZIP은 검사 후 읽기 전용으로 표시하고 이전 immutable 후보를 덮어쓰지 않았다. 이는 no-overwrite 정책과 파일 속성/해시 봉인이며 관리자도 변경할 수 없는 WORM이나 서명 attestation은 아니다.

Review용 text diff에는 LF/CRLF 정규화가 있으므로 Git의 EOL 변환 후 bytes가 봉인 후보와 같다고 가정하지 않는다. 정확한 6개 변경 파일의 `release_overlay.zip`을 별도로 만들고, 원본 manifest가 같은 새 복사본에 적용하여 **전체 tree가 tested manifest와 byte 단위로 동일함**을 확인했다. 그 hash와 재현 증거는 `release_overlay_verified.json`에 있다. 배포 승인 단계에서는 authoritative full ZIP/manifest를 사용한다.

운영 946개 파일, 기존 dirty/untracked 56개 파일, host `launch.py/revision.txt/adapter.yaml` 3개, 이전 immutable 후보 895개 파일과 ZIP을 전후 비교했다. 모두 변경 0개다. 모든 프로젝트 SOT와 portrait 구현·handoff·기존 테스트는 내용 그대로 보존됐다. 새 production 변경은 이번 후보 안에만 있으며, 기존 작업 트리의 Grok/fake 미커밋 변경을 덮어쓰지 않았다. 이번 release 자료는 로컬에 보존했고 자동 commit/push는 하지 않았다.

## 잔여 위험과 승인 경계

1. 경로 검사는 atomic handle-based read/copy가 아니므로 디렉터리를 검사 사이에 바꾸는 TOCTOU 위험은 남는다. CLI 및 신뢰하는 parent/root 자체를 장악한 공격자까지 완전히 방어한다고 주장하지 않는다.
2. Windows 8.3 가용성은 볼륨/설정에 의존한다. 예산을 만족하지 못하면 호출 전 차단하며 경로 단축을 위해 폴더 공유나 전역 scan으로 전환하지 않는다. 모든 filesystem/reparse tag를 검증한 것은 아니다.
3. 실제 Grok의 8.3 cwd에 대한 저장 동작, Codex/Grok 유료 generation E2E, approved-master E2E 및 live provider readiness는 미검증이다. CLI 옵션 help와 offline fixture 성공은 실제 image generation 증거가 아니다. 실제 native 구현의 cwd canonicalization이 예상과 다르면 출력 상관관계가 거부될 수 있으며 fallback으로 복구하지 않는다.
4. 테스트 venv는 운영 의존성을 읽기 공유한다. 독립 dependency 설치 검증과 공식 Plugin Creator 검증은 수행하지 않았다. legacy benchmark SKIP도 별도로 해결해야 한다.

운영 활성화에는 별도 승인이 필요하다. 그 단계에서 active session/job 소유권과 in-flight 작업을 다시 확인하고, 검증한 immutable ZIP을 새 runtime 디렉터리로 설치한 뒤 소유하는 연결만 전환해야 한다. 실패 시 생성 연결을 차단하고 전역 이미지 fallback이 있는 버전으로 자동 rollback하지 않는다. Golden 승인·provider ACTIVE 승격·SOT promotion은 이번 결과로 허용되지 않는다.

기계 판독 증거: 같은 release 폴더의 `sealed_candidate.json`, `candidate_provenance.json`, `preservation_before/after.json`, `portrait_project_preservation.json`, `recipe_scope_audit.json`, `pytest.xml`, `p1_before.xml`, `p1_baseline_provenance.json`, `protocol_summary.json`, 최종 protocol traces, `cli_help.log`, `import_probe.json`, `release_overlay_verified.json`.
