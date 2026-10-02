# P3 directional pixel recovery — offline benchmark

상태: **QUALITY_VALIDATION_FAILED** / 기존 4개 생성 원본 보존 / Comfy PixelOE 노드 호출 실패 / 공식 Torch API 1개 프레임 recovery 실행 후 Gate FAIL / ART_QA_PENDING. 승인된 후보는 없다.

## 생성 결과

로컬 ComfyUI에 4회 요청했고 4장 모두 완료했다. 별도 4회 한도는 소진됐으며 재시도나 대체 생성은 하지 않았다. 원본은 각 generated/G##/ 아래에 그대로 보존했다.

| ID | 대상 | VAE | Seed | 원본 RGB 색 수 | SHA-256 |
|---|---|---|---:|---:|---|
| G01 | Human Archer | 표준 Anima VAE | 202610021 | 10,359 | 3ad21be81240b861db9c839268d349b3c6f7f3eb1ea39752858a0981f072f7b8 |
| G02 | Human Archer | Pixelate x4 VAE | 202610021 | 3,822 | e69d5b942fe7d1cc93d10f013084f4326caea7414a2f4e9883f2f02a34a98091 |
| G03 | Orc Soldier | 표준 Anima VAE | 202610022 | 15,799 | bd977116a45e87b889526b57281d5226ba80a1be86a38c4ed45d0916bdad9f8f |
| G04 | Orc Soldier | Pixelate x4 VAE | 202610022 | 9,202 | 24fcc603312e878dd790398ab2c88c8d7f79ee29bdce61bc717c8a5f449d0ef6 |

모두 512×512 RGB이고 원본 알파 채널은 없다. 각 VAE 쌍은 prompt hash, seed, steps, CFG, sampler, scheduler, 해상도, diffusion 모델, text encoder가 일치한다. 쌍 안에서 의도된 변경 축은 VAE뿐이다. SHA와 전체 프롬프트/모델 메타데이터는 generated/G##/generation.json에 기록했다.

모델 SHA-256:
- Anima Base: BD43B7CFFE1ED1153D9C41E7BEB2F18CB1273EAFBAA3AF3EDD6A173DC90A006E
- Qwen text encoder: CD2A512003E2F9F3CD3C32A9C3573F820BB28C940F73C57B1DDAA983D9223EBA
- 표준 qwen_image_vae: A70580F0213E67967EE9C95F05BB400E8FB08307E017A924BF3441223E023D1F
- Pixelate x4 VAE: 9A27E059E2831D43FC441FF9D6381294BE19A9449B6EAD5FFAB0F108182D067C

## 방향 충족 여부

실패했다. 프롬프트는 남쪽 정면, 서쪽 측면, 북쪽 후면을 요청했지만 네 시트 모두 세 캐릭터가 사실상 정면을 반복한다. 3개 배치가 생성됐다는 이유로 3방향 성공이라고 판정하지 않았다.

32×32 1× 확인에서 궁수의 활은 몸 옆에서 식별 가능했고, 오크의 넓은 어깨와 몸통 덩어리도 유지됐다. 다만 이 결과는 방향 다양성을 만족하지 않으므로 사용 가능한 3방향 세트가 아니다.

## 32×32 변환 및 Pixel Gate

각 생성 이미지의 3개 캐릭터 영역을 분리해 비율을 유지하고 중앙 정렬했다. 원본 영역을 임의로 자르지 않았다. NN 축소와 MedianCut 순서를 바꿔 16/32색 정책을 적용했다. 각 후보는 흰색 불투명 배경과 이진 알파 마스크 버전으로 저장했다.

기존 Pixel Gate analyzer를 max_colors=32, gradient threshold=0.18, target=32×32로 실행했다. 총 96개 NN+MedianCut 후보에서 88 PASS, 8 REVIEW_REQUIRED, 0 FAIL이었다. **88/96 기술 Gate PASS는 생산 성공이나 Static Master 승인이 아니다.** 모든 결과는 사람 검토와 원본 방향 품질 실패의 영향을 받는다.

| 처리 순서 | 배경 | 후보 | Pixel Gate | Gate 표시 색 수 |
|---|---|---:|---|---:|
| NN → MedianCut 16 | 흰색 불투명 | 12 | 10 PASS, 2 REVIEW_REQUIRED | 16 |
| NN → MedianCut 16 | 이진 알파 | 12 | 12 PASS | 11–16 |
| MedianCut 16 → NN | 흰색 불투명 | 12 | 10 PASS, 2 REVIEW_REQUIRED | 15–16 |
| MedianCut 16 → NN | 이진 알파 | 12 | 12 PASS | 12–16 |
| NN → MedianCut 32 | 흰색 불투명 | 12 | 10 PASS, 2 REVIEW_REQUIRED | 31–32 |
| NN → MedianCut 32 | 이진 알파 | 12 | 12 PASS | 25–31 |
| MedianCut 32 → NN | 흰색 불투명 | 12 | 10 PASS, 2 REVIEW_REQUIRED | 31–32 |
| MedianCut 32 → NN | 이진 알파 | 12 | 12 PASS | 23–32 |

모든 후보의 Pixel Gate gradient 및 AA heuristic은 LOW다. 흰색 불투명 버전의 8개 REVIEW_REQUIRED는 G03 오크 측면/후면 슬롯에서 검출된 작은 분리 실루엣 군집 때문이다. 이진 알파 버전에서는 해당 군집이 Gate상 사라졌지만, RGB≥235의 테두리 연결 배경 flood fill로 만든 휴리스틱 마스크이므로 흰 장식이나 가장자리 픽셀을 잘못 투명하게 했는지 사람이 확인해야 한다.

같은 팔레트 크기에서 NN→MedianCut과 MedianCut→NN은 12프레임 중 평균 약 298–300픽셀(RGB 차이 기준)이 다르다. 순서는 실제 결과에 영향을 줬다. 전체 후보별 hash, 색 수, 클러스터, edge/isolated pixel, Pixel Gate JSON은 post/offline_prepared.json 및 각 후보 디렉터리의 qa_*.json에 있다.

## PixelOE 실행 상태 및 원인 수정 조사

원래 P3 ComfyUI PixelOE 노드 작업은 thickness 2에서 `ModuleNotFoundError: No module named 'pixeloe.pixelize'`로 실패했다. 실행한 1건에는 출력이 없고 나머지 11건은 보내지 않았다. 이 과거 결과는 **ComfyUI 노드 미실행**으로 보존했다.

후속 로컬 조사에서 원인을 확인했다. 실제 ComfyUI venv에는 `pixeloe 1.0.0`이 이미 설치되어 있었다. `comfyui_essentials 1.1.0`의 `image.py:888`이 구형 top-level `pixeloe.pixelize`를 import하지만 설치된 패키지는 `pixeloe.legacy.pixelize`와 `pixeloe.torch.pixelize`를 제공한다. 라이브 노드 스키마의 thickness 범위도 1–16이라 0을 받을 수 없다. 패키지 설치/업데이트 또는 Comfy 노드 수정은 하지 않았다.

같은 기존 G01 남쪽 정면 프레임 입력에 설치되어 있던 공식 `pixeloe.torch.pixelize` API를 직접 실행해 별도 recovery 증거를 남겼다. 실제 32×32 RGB PNG가 생성됐으나 두 결과 모두 현재 Gate에서 FAIL이다.

| 후보 | RGB 색 수 | Gradient / AA | Pixel Gate |
|---|---:|---|---|
| PixelOE Torch thickness 0 | 238 | HIGH / HIGH | **FAIL** |
| PixelOE Torch thickness 2 | 226 | HIGH / HIGH | **FAIL** |
| 기존 NN → MedianCut 32 불투명 흰색 baseline | 32 | LOW / LOW | PASS (해당 프레임의 기술 결과만) |

공식 API 호출, input/output SHA-256, 환경 버전, 출력 PNG와 동일 analyzer의 JSON은 `post/pixeloe_api_recovery/`에 있다. 기존 Gate 임계값과 Refiner는 바꾸지 않았다. P1 한 장의 Gate PASS와 PixelOE 코드 실행 PASS는 모두 생산 승인과 다르다. 두 PixelOE 결과, bow/몸통 의미, 실루엣 및 흰색 matte 경계는 사람 검토가 필요하다.

DPID/PIA는 NOT_AVAILABLE이며 이번 복구 조사에서도 외부 탐색이나 설치를 하지 않았다. 기존 초기 노드 실패와 schema는 `post/pixeloe_runtime.json`에 보존했다.

## contact sheet

Contact sheet는 화면 확인용이며 원본 측정에는 사용하지 않았다.

- 네이티브 1× 흰색 배경: post/gallery_native1x_opaque.png
- 네이티브 1× 알파/체커보드: post/gallery_native1x_rgba_checker.png
- Nearest 4× 흰색 배경: post/gallery_nearest4x_opaque.png
- Nearest 4× 알파/체커보드: post/gallery_nearest4x_rgba_checker.png
- PixelOE recovery native 1× candidate comparison: post/pixeloe_api_recovery/comparison_native_1x.png
- PixelOE recovery 4× nearest candidate comparison: post/pixeloe_api_recovery/comparison_nearest_4x.png (display-only)

## 승인 및 다음 실험

Human review는 PENDING이다. Static Master 승인 0건, Golden Recipe 승인 0건, 프로젝트 SOT 승격 없음. Aseprite roundtrip과 Godot 인게임 검증도 실행하지 않았다. 기존 Pixel Gate, Refiner, M1/M2 계약은 변경하지 않았다.

추가 생성 예산은 **0**이며 별도 승인 전에는 요청하지 않는다. 최소 후속 VAE 비교는 캐릭터 1종의 단일 방향·단일 캐릭터 PNG를 표준 Anima VAE와 Pixelate x4 VAE로 각각 1장씩 생성하는 2장 쌍이다. 두 요청은 prompt/seed/settings를 고정하고 VAE만 바꾼다. 원화는 중앙 정렬, 화면 대부분을 차지하는 캐릭터, 단순 배경으로 제한하며 3방향 시트 프롬프트는 쓰지 않는다. 같은 32×32 후처리 후보 비교 → native 1×/NN 4× 및 변경하지 않은 Pixel Gate → 국소 픽셀 수정 → 실제 사람 검토 순서로 진행한다. 오크까지 포함한 확장 비교는 총 4장이지만 1차 쌍 결과 이후 별도 승인받는다.

전체 pytest 회귀 테스트: PASS — 207 passed, 0 failed (91.78s). `.venv/Scripts/assetpipe.exe --help`: PASS. 저장소 지침의 `pip install -e '.[dev,motion]'`는 build isolation 단계에서 `setuptools>=68`을 configured package sources에서 찾지 못해 실패했으며 패키지는 설치되지 않았다. 이 제한은 별도 실험 복구 보고서에도 기록했다.
