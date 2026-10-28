# git 이력 재작성 기록 — 2026-10-28

사용자 요청으로 저장소 용량을 줄이기 위해 `git filter-repo`로 전체 이력에서
`research/style_catalog/style_menu_v1/evidence/`(227개 파일, 약 90.6MB)를 제거했다.

## 결과

- git pack 크기: 약 87MB → 약 22MB
- 원본 파일은 사용자의 로컬 클론에 보관한다. 경로·크기·SHA256은
  [external_evidence_manifest.json](../../research/style_catalog/style_menu_v1/external_evidence_manifest.json)에,
  기존 판정·연결 정보는 변경 없는 `evidence_archive.json`에 남아 있다.
- 코드·테스트·CI는 이 폴더를 읽지 않으며, 운영 설정이 참조하는 `previews/`는 유지했다.

## 커밋 해시 변경

이력 재작성으로 대부분의 커밋 해시가 바뀌었다. 문서·체인지로그에 기록된 옛 해시는 원문 그대로 두고,
[커밋 대응표](HISTORY_REWRITE_20261028_commit_map.txt)(`old_sha new_sha`)로 새 해시를 찾는다.
커밋 메시지 안의 해시는 filter-repo가 자동으로 바꿨다.

실행에 쓰이는 고정 해시만 새 값으로 갱신했다.

| 위치 | 옛 해시 | 새 해시 |
| --- | --- | --- |
| `scripts/local_mcp/windows/deploy.py`, 같은 폴더 README | `12c2109` | `ebef495` |
| `scripts/anima_family_pipeline.py` R1/R2 증거 커밋 | `2675298` / `b756483` | `737a303` / `fb93650` |

`config/styles/projects/isekai_examiner/visual_sot.yaml`의 출처 URL(`5d6353f`, 새 해시 `d95e48e`)은
Visual SOT 잠금 해시에 포함되므로 바꾸지 않았다. 출처 표시용이며 옛 커밋은 기존 PR 기록으로 GitHub에서 열린다.

이미 설치된 로컬 MCP 런타임(옛 해시 이름의 폴더)은 그대로 동작한다. 다시 배포하면 새 해시 폴더가 만들어진다.

## 기존 클론 처리

이력이 바뀌었으므로 기존 클론은 새로 클론하는 것이 가장 안전하다. 그 전에 `evidence/` 폴더를
저장소 밖에 복사해 둔다. 새 이력에 맞추면 작업 트리에서 이 폴더가 사라진다.
