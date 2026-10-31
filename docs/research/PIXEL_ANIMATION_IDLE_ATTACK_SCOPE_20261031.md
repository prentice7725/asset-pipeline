# PIXEL_ANIMATION idle·attack 범위 조사 (2026-10-31)

hf-game-studio 설계 문서 10단계가 요청한 idle·attack 픽셀 애니메이션을 지금 구조에 넣을 수 있는지 조사했다.
결론은 **이번 PR 범위를 넘는다**는 것이다. 코드는 바꾸지 않았고 생성도 하지 않았다.

## 지금 walk만 되는 이유

walk 전용 가정이 한 곳이 아니라 경로 전체에 박혀 있다.

| 위치 | walk 전용 가정 |
| --- | --- |
| `src/assetpipe/pipelines/pixel_animation/__init__.py` `preflight` | `action == 'walk'`, 8개 보행 위상(`CONTACT_A`…`UP_B`), `frame_target` 8, 프로필 `blue_tunic_white_matte_v1` 고정 |
| `src/assetpipe/_ported/motion_extractor/keyframes.py` `plan_keyframes` | walk 외 action 거부, 보행 주기 추정(`_cycle_period`)으로 키프레임 선택 |
| `src/assetpipe/pixel/direct/ported.py` | 파란 튜닉·흰 배경 한 캐릭터에 맞춘 검증 프로필, 미리보기 이름도 `direct_walk_*` |
| `src/assetpipe/_ported/aseprite_bridge/runner.py` | 태그 이름 `walk` 고정(목록 확인·시트 내보내기·메타데이터) |
| `src/assetpipe/api.py` `capabilities` | `animation_actions.PIXEL_ANIMATION == ['walk']` |

`_ported` 아래 코드는 레거시 pixel-pipeline에서 옮겨 온 검증 알고리즘이라 AGENTS.md가 재작성을 막는다.

## idle·attack에 필요한 것

1. **동작별 위상 정의.** idle은 주기적이지만 진폭이 작아 보행 주기 추정이 맞지 않는다.
   attack은 비주기(준비 → 타격 → 복귀)라 루프 위상 대신 순서 있는 키포즈와 프레임별 지속 시간이 필요하다.
2. **모션 레퍼런스.** 지금 경로는 사람이 검토한 기존 영상과 의미 선택(`selection`)을 요구하고 새 모션을 만들지 않는다.
   idle·attack용 검토된 레퍼런스 영상이 없다. 만들려면 별도 생성 예산과 사용자 승인이 필요하다.
3. **범용 DIRECT 프로필.** `blue_tunic_white_matte_v1`은 한 캐릭터용이다.
   다른 캐릭터에 쓰려면 프로필 검증부터 다시 해야 하며, 이는 AGENTS.md의 "verified direct profile requires explicit compatibility; never infer it" 규칙에 걸린다.
4. **Aseprite 태그 일반화.** 레거시 runner의 `walk` 상수를 action 인자로 바꾸는 작업. 레거시 코드 수정이라 별도 승인이 필요하다.
5. **attack 판정.** 무기 궤적·타격 프레임은 기계로 확인할 수 없으니 사람 검토 항목이 늘어난다.

## 대안 경로

NONPIXEL 쪽 M3 모션 경로(`create --type nonpixel-animation --motion-job`)는 action 이름을 요청에서 받는다
(Godot `<action>.tres`, Phaser `<asset_id>_<action>`). 픽셀 idle·attack이 급하지 않다면
NONPIXEL 모션 후보 → 이번 PR의 팔레트 양자화를 프레임마다 적용하는 쪽이 레거시 코드를 건드리지 않는 길이다.
다만 프레임 간 팔레트 일관성(공통 팔레트 하나로 묶기)과 깜빡임 검사가 새로 필요하다.

## 제안

별도 요청으로 다음 순서를 권한다.

1. 사용자가 픽셀 idle·attack을 여는 결정과 레거시 코드 수정 범위를 정한다(AGENTS.md는 pixel 연구를 동결 상태로 둔다).
2. idle부터: 위상 정의와 레퍼런스 영상 한 개를 사람이 검토해 고정한다.
3. Aseprite 태그·`capabilities`를 action 인자로 일반화하고 walk 회귀 테스트를 유지한다.
4. attack은 비주기 키포즈 계약을 따로 설계한다.
