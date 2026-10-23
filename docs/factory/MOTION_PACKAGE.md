# 기존 영상의 오프라인 모션 리뷰 패키지

`motion-package`는 별도로 준비한 영상의 원본 보존 → FFmpeg RGB 프레임 →
기존 Motion Extractor 정렬/분석 → 스프라이트 아틀라스를 연결한다.
Factory 공통 I2V 실행과 legacy `NONPIXEL_ANIMATION` 차단은 유지된다.
정지 이미지/SFX 경로와 여섯 MCP 계약은 바뀌지 않는다.

```powershell
assetpipe --root C:/path/to/asset-pipeline motion-package --request workspace/motion_request.json --video workspace/source.avi --video-sha256 <exact-sha256> --output workspace/motion_child_001
```

요청은 기존 Factory v1 IMAGE_TO_SPRITE이며 NONPIXEL/REFERENCE_MOTION의
EXISTING_RUN 또는 EXTERNAL_IMAGES를 사용한다. 기존 문서·이미지·parent 해시와
역할/경로 검사를 재사용한다. 입력 roots는 `--allowed-root`로 지정하며 출력은
root의 `workspace/` 안의 새로운 디렉터리만 허용한다. 기존 출력은 덮어쓰지 않는다.
연관 이미지가 실제 영상 생성에 쓰였는지는 **NOT_VERIFIED**로 명시한다.

범위는 단일 CFR 비디오 스트림, 최대 10초·240프레임·2048x2048·60fps다.
FFprobe가 FPS·크기·프레임 timestamp를 검사하며, request FPS/duration과
target_frames가 맞지 않으면 중단한다. 자동 재샘플링/재시도/모델 전환은 없다.
기존 `decode_direct_reference`를 재사용하지만 픽셀 direct 알고리즘은 호출하지 않는다.
추출기의 blur/중복 후보 필터는 참고 기록이며, export는 모든 프레임을 시간 순서대로
보존해 정지 포즈의 재생 시간을 줄이지 않는다. keyframe 선택으로 포즈·루프를
자동 승인하지 않는다. 아틀라스는 최대 32M pixels다.

알파 정책은 PRESERVE_OR_REVIEW만 지원한다. 비디오 배경은 불투명으로 보존하며
크로마키를 추측하지 않는다. EXPLICIT_ALPHA_REVIEW/PIXEL64는 이 명령에서 차단한다.
기존 bottom-center 정렬의 offset과 canvas bottom-center 피벗을 기록하지만
의미적 발 위치/피벗 안정성/루프/캐릭터 정체성은 사람 검토 대상이다.
이 출력은 production-ready sprite나 승인된 animation이 아니다.

산출물: `original.*`, `decoded/`, `extraction/`(raw/sampled/aligned/selected와
contact sheets), `sprites.png`, `atlas.json`, `review.json`, `run_manifest.json`.
원본/정렬 프레임/최종 출력 hash, decode command/version, 정확한 FPS 분수,
프레임 순서·duration·피벗·정렬 offset·source plan을 기록한다.
실패는 FAILED로 보존하고 이후 단계로 진행하지 않는다. parent 파일을 쓰지 않는다.
기술적 패키징 성공도 OFFLINE_PACKAGE_REVIEW_REQUIRED / game_ready=false다.
review template에는 관찰/승인 값을 채우지 않는다.

변경 파일: `motion/package.py`, CLI의 추가 명령, `tests/unit/test_motion_package.py`.
새 알고리즘 대신 기존 decoder/extractor/RootResolver/Factory plan/manifest writer를 재사용한다.
합성 영상의 실제 FFmpeg codec·RGBA pack 일치와 실패 보존을 검사하며,
실제 모델 생성·인간 미술 품질 개선·Godot/Phaser import는 NOT_RUN이다.
로컬 신뢰 소유권을 전제로 하며 경로 확인과 파일 읽기 사이 경쟁 상태는 기존 한계다.

롤백: 이 변경 commit을 revert하고 추가 CLI 명령을 사용하지 않는다.
보존된 run·원본·예산 디렉터리는 지우지 않는다. registry/운영 runtime은 변경하지 않았다.
