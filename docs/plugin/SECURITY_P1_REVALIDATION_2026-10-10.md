> Historical report (2026-10-10), published for traceability. Its BLOCKED result belongs to that snapshot; the follow-up is [release blockers](SECURITY_RELEASE_BLOCKERS_2026-10-10.md). It is not a current runtime assessment or activation request.

# SECURITY-P1-REVALIDATION — 2026-10-10

판정: **BLOCKED**. P1 별칭 차단은 통과했으나 현재 운영 스냅샷을 기반으로 한 전체 회귀에 11개 실패가 남아 활성화할 수 없다. 기존 운영 런타임은 교체하지 않았다.

## 검토와 후보 구성

P1 diff는 `51854d6^..51854d6`를 검토했다. 공통 `session_scope`는 신뢰하는 부모를 정규화하고 세션 엔트리를 `lstat`으로 검사한다. symlink, Windows reparse point/junction, canonical 경로 불일치와 비디렉터리를 이미지 scan/metadata 접근 전에 `OUTPUT_UNCORRELATED`로 거부하며 수집 후 재검사한다. 누락 세션과 기존 QA/해시/리뷰 게이트는 유지한다.

새 후보는 실제 `workspace/mcp_runtime/revision.txt`가 가리키는 `5d6353f-portrait-delivery-359e12c9f693`를 새로 복사하여 구성했다. 오래된 main이나 이전 후보 전체로 덮어쓰지 않았다. `e7a5551^..51854d6`의 보안 diff를 적용하되, 운영 스냅샷에 이미 있는 Grok 작업별 세션 경로와 `snapshot_roots`는 그대로 보존하고 `harvest`만 공통 `correlated_images(... session_parent=state['roots'][0])`에 연결했다. 일반 diff의 Grok hunk가 맞지 않아 최초 `git apply --check`는 실패했으며, 이 게이트를 무시하지 않고 별도 호환 diff를 검토했다.

이 적응은 `grok_snapshot_security.patch`에, 적용 가능한 나머지는 `compatible_security.patch`에 보존했다. 합성 Grok fixture만 작업별 부모 경로를 사용하도록 고친 `fake_fixture.patch`와 Windows 재검증 테스트 22개를 포함했다. production 알고리즘, workflow 설정, 모델 기본값, SOT와 portrait 구현을 재작성하지 않았고 전역 이미지 fallback을 복구하지 않았다. 처음 봉인한 중간 후보도 보존한 채 Windows 전용 테스트의 다른 OS skip 표시를 보완한 최종 복사본을 별도로 만들었다.

## 수정 전·후 및 회귀 결과

| 검증 | 결과 |
| --- | --- |
| P1 수정 전, Codex/Grok × symlink/junction × scan/explicit | 8 FAIL, 31 deselected: scan 이전 거부 조건 위반 재현 |
| P1 수정 후 동일 8개 | 8 PASS |
| 기존 보안/P2 게이트 + 새 Windows 검증 | 61 PASS, 0 FAIL, 0 SKIP |
| 최종 후보 전체 pytest | 426 PASS, 11 FAIL, 1 SKIP, 0 ERROR — 438개 |
| 같은 스냅샷의 P1 수정 전 트리에서 실패 원인 재검증 | 44 PASS, 동일 11 FAIL — 55개 |
| portrait/project 계약 | 13 PASS |
| MCP initialize/tools/list 및 정확한 6개 schema 비교 | PASS, 현재 운영 스냅샷과 schema 동일 |
| MCP 여섯 도구 안전 dispatch·root/traversal·nested reference·symlink 거부 | PASS |
| CLI help 및 격리 import 경로 확인 | PASS |
| 보존 전후 파일 SHA 비교 | PASS, 변경 0개 |

Windows 검증은 부모·세션 ID·명시 파일 경로 대소문자 변형, sibling session alias, 세션 하위의 2단계 reparse chain을 통한 sibling/외부 루트 접근, 같은 세션 내부의 정상 링크, 정상 이미지 scan/explicit 수집을 포함한다. 기존 transitive provenance/source manifest/resolution/evidence/candidate/export/master 경로, approved_export 일관성, hash/pixel 실패 게이트, 다른 세션·누락 상관관계·ambiguous output·동시 작업·fallback 차단 회귀도 유지됐다. Grok 전체 provider 회귀는 아래 경로 실패 때문에 PASS로 선언하지 않는다.

전체 실패는 다음과 같다.

1. Grok provider 합성 회귀 9개: 작업 경로를 URL-encoding한 session parent 생성에서 Windows `winerror=3 / FileNotFoundError`. P1 전 트리에서도 268자 경로 및 API-key 격리 모드의 301자 경로에서 재현됐다. 유료 CLI 호출 이전에 실패하며 예상 오류 코드/manifest가 생성되지 않는 후속 assertion도 함께 실패한다.
2. knowledge 개수 회귀 1개: runtime recipes 기대 91, 실제 92.
3. style override 오류 메시지 회귀 1개: 기대 `No style-compatible recipe`, 실제 `No compatible workflow: Recipe style fingerprint mismatch`. 차단 자체는 유지됐으나 테스트 계약은 실패한다.

SKIP 1개는 격리 복사본에서 로컬 migration benchmark 데이터를 찾을 수 없는 기존 legacy 비교 테스트다. 해당 외부 benchmark 동등성을 통과했다고 주장하지 않는다.

최종 복사본의 초기 재실행에서는 이전 봉인의 읽기 전용 속성이 임시 테스트 fixture로 복사돼 60개 PermissionError와 추가 실패가 났다. 이 시도는 `pytest_readonly_fixture.log/xml`로 보존했다. 아직 봉인 전인 새 복사본의 속성만 바로잡고 콘텐츠 SHA가 그대로인 상태에서 전체 테스트를 다시 실행한 결과가 위 최종 438개 결과다. 최종 봉인은 모든 검증이 끝난 뒤 적용했다.

## 최종 immutable candidate

- ID: `security-p1-revalidation-20261010-0230a56bb034`
- 위치: `workspace/security/p1-revalidation-20261010-final/candidate`
- 파일 수: 895
- tree SHA-256: `0230a56bb034938fca4d40c1585395dc3b537d444df46cb1243776a059da2684`
- zip SHA-256: `79e3d45ccfaa307d9605fc3f6245f5b4a190c088d01ccd3a28e2c33b2da97641`
- zip: `workspace/security/p1-revalidation-20261010-final/security-p1-revalidation-20261010-0230a56bb034.zip`

tree hash는 경로→개별 파일 SHA-256 manifest를 정렬 키·공백 없는 canonical JSON으로 직렬화한 바이트의 SHA-256이다. ZIP의 모든 entry 내용 해시가 manifest와 일치함을 확인했고, candidate 파일과 ZIP은 검증 후 읽기 전용으로 표시했다. 기존 봉인 artifact는 덮어쓰지 않았다. 이는 no-overwrite 운영 규칙과 읽기 전용 속성·해시 봉인이며 OS 관리자도 변경할 수 없는 WORM 저장소나 서명된 attestation은 아니다.

## 보존과 실행 경계

기존 미커밋/미추적 파일 54개, 운영 runtime 파일 946개, `launch.py`, `revision.txt`, `adapter.yaml` 3개를 전후 SHA 비교했다. 모두 변경 0개이며, 이전 검증의 운영 보존 manifest와 이번 시작 manifest도 내용 변경 0개다. 이전 후보와 현재 운영 스냅샷의 코드 차이를 운영 runtime의 새 mutation으로 해석하면 안 된다.

portrait 구현·전용 테스트·프로젝트 SOT·handoff 문서는 바이트 그대로 유지됐고, 비캐시 파일 삭제는 없다. 보호 파일과 실제 diff 목록은 `portrait_preservation.json`에 보존했다. 이것은 offline 계약 검증이며 portrait 실생성이나 이미지 품질 승인이 아니다.

MCP는 테스트 소유 별도 stdio 프로세스에서 현재 스냅샷과 새 후보를 각각 실행했다. capability는 과금/외부 readiness probe를 막은 offline stub이며 생성 provider 및 생성용 child process 경로는 금지 guard가 차단한다. 두 서버 모두 stdin EOF 후 exit 0을 관찰했다. 기존 활성 MCP 프로세스는 종료하지 않았다. 테스트 Python 3.11.9의 별도 venv에서 candidate source import를 확인했고 운영 dependency 디렉터리는 읽기만 공유한다. 의존성 재설치나 운영 pointer 변경은 없다.

실제 Codex/Grok/ComfyUI 생성·과금 요청 0건, 실제 Golden/Aseprite 승인 0건, provider ACTIVE 승격·SOT 변경 0건이다. 합성 fixture를 실제 승인이나 실제 provider 인증/생성 증거로 인정하지 않는다.

## 남은 위험과 활성화 조건

현재 전체 회귀의 11개 실패를 해결하고 새 후보로 재검증하기 전에는 **BLOCKED**다. 이전 main/이전 후보의 PASS를 이번 운영 스냅샷에 그대로 대입해서는 안 된다.

경로 검증은 atomic handle-based read/copy가 아니므로 검사 사이에 디렉터리가 교체되는 TOCTOU 위험은 남는다. 부모 디렉터리는 configured/trusted root로 취급하며 CLI가 보고한 세션 ID의 진위를 암호학적으로 증명하지 않는다. 로컬 파일시스템/CLI를 동시에 장악한 공격자에 대한 완전한 방어를 주장하지 않는다. Windows 정상 세션 대소문자 테스트는 통과했지만 모든 파일시스템 종류·네트워크 드라이브·reparse tag를 검증한 것은 아니다.

실제 generation E2E, approved-master E2E, live provider readiness, 독립적인 dependency 설치, 공식 Plugin Creator 검증은 수행하지 않았다. 별도 승인 후 활성화 단계에서도 session/job 소유권과 in-flight 작업을 다시 확인해야 하며, 실패 시 서비스 연결을 중단하고 전역 fallback이 있는 runtime으로 자동 되돌리지 않는다. 이 보고서는 runtime 교체 승인이나 production readiness/SOT promotion 근거가 아니다.

기계 판독 증거는 같은 final 폴더의 `verification_summary.json`, `sealed_candidate.json`, `candidate_provenance.json`, `preservation_before/after.json`, `portrait_preservation.json`, `diff_review.json`, `pytest.xml`, `p1_before.xml`, `baseline_regressions.xml`, `protocol_summary.json`, 두 protocol trace와 `import_probe.json`에 있다. 이번 재검증 자료와 새 테스트는 로컬에 보존했으며 자동 commit/push는 하지 않았다.
