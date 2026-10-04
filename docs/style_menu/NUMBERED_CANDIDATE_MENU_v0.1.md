# 화풍 번호 메뉴판 v0.1 — Krea2 Style Explorer 후보

> **EXTERNAL_PREVIEW_ONLY / 실험 미완료 / 승인 0**. 이 이미지들은 원저작자가 공개한 Krea2 예시다. 현재 Asset-Pipeline에서 새로 생성하거나 재현·인게임 검증한 결과가 아니다.

> 카드 번호는 고정 ID다. Codex/Claude는 프로젝트 SOT를 실제로 읽은 뒤 후보를 비교할 수 있지만, 미검증 카드를 생산 기본값으로 자동 승격해서는 안 된다.

**참고 사이트:** https://kreastyles.thetacursed.com/ · **출처:** https://github.com/ThetaCursed/Krea2-Style-Explorer · **고정 커밋:** `eb690aa57bc6` · **원본 목록:** 1,596종

**2026-10-04 우선순위:** STYLE-001 SF, STYLE-004 판타지 SD 비픽셀, STYLE-006 중세판타지, STYLE-008 현대 만화를 **Anima/Krea2 비교 후보**로 먼저 연구한다. STYLE-005 픽셀아트의 로컬 신규 실험은 **HOLD** (검색용 카드만 유지).

**[비픽셀 11종 모델별 프롬프트 연구](NONPIXEL_PROMPT_RESEARCH_v0.1.md)** · **[Codex 로컬 재현 실행 지시서](CODEX_NONPIXEL_WORK_ORDER_v0.1.md)**. 이미지로 비교할 수 있는 '검증 완료 메뉴'는 아직 없으며, 외부 제작자 미리보기 이미지로만 시작한다.

## 장르 검색 색인

- **COMEDY:** `STYLE-008` · `STYLE-009`
- **COZY:** `STYLE-004` · `STYLE-005` · `STYLE-006` · `STYLE-010` · `STYLE-011`
- **DARK FANTASY:** `STYLE-003` · `STYLE-007`
- **FANTASY CHIBI SD:** `STYLE-004` · `STYLE-005` · `STYLE-009` · `STYLE-010` · `STYLE-011`
- **HISTORICAL:** `STYLE-006`
- **MEDIEVAL FANTASY:** `STYLE-003` · `STYLE-004` · `STYLE-006` · `STYLE-007`
- **MODERN:** `STYLE-002` · `STYLE-008` · `STYLE-009` · `STYLE-012`
- **NOIR:** `STYLE-001`
- **PIXEL:** `STYLE-005`
- **PUNK:** `STYLE-012`
- **SF CYBERPUNK:** `STYLE-001` · `STYLE-002` · `STYLE-009` · `STYLE-012`
- **SF FANTASY:** `STYLE-003`
- **SLICE OF LIFE:** `STYLE-008`
- **TACTICAL:** `STYLE-010`
- **THRILLER:** `STYLE-002`

---

## STYLE-001 — Neon Industrial Cyberpunk

![외부 생성 미리보기 STYLE-001](https://raw.githubusercontent.com/ThetaCursed/Krea2-Style-Explorer/eb690aa57bc6974af6b4b3b8c5a780195bcadf78/images/1/aaea31dc325f.webp)

**장르:** [SF_CYBERPUNK, NOIR]  
**애셋 역할 가설:** [BACKGROUND, CHARACTER, PROP]  
**외부 스타일 ID:** `aaea31dc325f`  
**실험 상태:** 외부 샘플 있음 / 우리 Krea2 재현 NOT_RUN / Anima 변환 NOT_RUN / 사람 리뷰 NOT_RUN / 게임 적용 NOT_RUN

**출처 스타일 표현:**

```text
saturated red neon lighting, high-contrast noir, futuristic cyberpunk aesthetic, glossy metallic surfaces, deep shadows, cinematic low-key photography, industrial synthwave atmosphere
```

**후보 조합:** Krea2 Turbo · 현재 `krea2_base` · 현재 `qwen_image_vae.safetensors` · LoRA 없음. **이 조합은 아직 원본 샘플의 실제 재현을 검증하지 않았음.**

---

## STYLE-002 — Amber/Blue Cybernetic Noir

![외부 생성 미리보기 STYLE-002](https://raw.githubusercontent.com/ThetaCursed/Krea2-Style-Explorer/eb690aa57bc6974af6b4b3b8c5a780195bcadf78/images/1/ab4ac0c75e48.webp)

**장르:** [SF_CYBERPUNK, MODERN, THRILLER]  
**애셋 역할 가설:** [PORTRAIT, CHARACTER]  
**외부 스타일 ID:** `ab4ac0c75e48`  
**실험 상태:** 외부 샘플 있음 / 우리 Krea2 재현 NOT_RUN / Anima 변환 NOT_RUN / 사람 리뷰 NOT_RUN / 게임 적용 NOT_RUN

**출처 스타일 표현:**

```text
cybernetic portraiture, chiaroscuro lighting, futuristic eyewear, cinematic 35mm film grain, high contrast composition, minimalist cyberpunk, saturated amber and blue palette
```

**후보 조합:** Krea2 Turbo · 현재 `krea2_base` · 현재 `qwen_image_vae.safetensors` · LoRA 없음. **이 조합은 아직 원본 샘플의 실제 재현을 검증하지 않았음.**
**피사체 누출 주의:** 외부 스타일 문장 자체에 인물/물체/장르 묘사가 포함되어 있을 수 있으므로 SOT 고정 요소에 섞지 않는다.

---

## STYLE-003 — Twilight Gothic Anime

![외부 생성 미리보기 STYLE-003](https://raw.githubusercontent.com/ThetaCursed/Krea2-Style-Explorer/eb690aa57bc6974af6b4b3b8c5a780195bcadf78/images/1/2dfd01bda89f.webp)

**장르:** [MEDIEVAL_FANTASY, DARK_FANTASY, SF_FANTASY]  
**애셋 역할 가설:** [BACKGROUND, CHARACTER]  
**외부 스타일 ID:** `2dfd01bda89f`  
**실험 상태:** 외부 샘플 있음 / 우리 Krea2 재현 NOT_RUN / Anima 변환 NOT_RUN / 사람 리뷰 NOT_RUN / 게임 적용 NOT_RUN

**출처 스타일 표현:**

```text
90s retro anime style, hand-painted watercolor background, deep indigo twilight, ethereal magenta bioluminescence, high-contrast moody lighting, gothic fantasy atmosphere, cel-shaded 2D illustration
```

**후보 조합:** Krea2 Turbo · 현재 `krea2_base` · 현재 `qwen_image_vae.safetensors` · LoRA 없음. **이 조합은 아직 원본 샘플의 실제 재현을 검증하지 않았음.**

---

## STYLE-004 — Cozy Gouache Storybook

![외부 생성 미리보기 STYLE-004](https://raw.githubusercontent.com/ThetaCursed/Krea2-Style-Explorer/eb690aa57bc6974af6b4b3b8c5a780195bcadf78/images/1/b0c422916b0d.webp)

**장르:** [FANTASY_CHIBI_SD, MEDIEVAL_FANTASY, COZY]  
**애셋 역할 가설:** [CHARACTER, BACKGROUND, PROP]  
**외부 스타일 ID:** `b0c422916b0d`  
**실험 상태:** 외부 샘플 있음 / 우리 Krea2 재현 NOT_RUN / Anima 변환 NOT_RUN / 사람 리뷰 NOT_RUN / 게임 적용 NOT_RUN

**출처 스타일 표현:**

```text
children's book illustration, textured gouache painting, whimsical character design, vibrant saturated colors, soft painterly textures, expressive simplified features, warm dappled lighting
```

**후보 조합:** Krea2 Turbo · 현재 `krea2_base` · 현재 `qwen_image_vae.safetensors` · LoRA 없음. **이 조합은 아직 원본 샘플의 실제 재현을 검증하지 않았음.**
**피사체 누출 주의:** 외부 스타일 문장 자체에 인물/물체/장르 묘사가 포함되어 있을 수 있으므로 SOT 고정 요소에 섞지 않는다.

---

## STYLE-005 — Pastel Chibi Pixel Candidate

![외부 생성 미리보기 STYLE-005](https://raw.githubusercontent.com/ThetaCursed/Krea2-Style-Explorer/eb690aa57bc6974af6b4b3b8c5a780195bcadf78/images/1/6d67e449de82.webp)

**장르:** [FANTASY_CHIBI_SD, COZY, PIXEL]  
**애셋 역할 가설:** [CHARACTER, PROP]  
**외부 스타일 ID:** `6d67e449de82`  
**실험 상태:** 외부 샘플 있음 / 우리 Krea2 재현 NOT_RUN / Anima 변환 NOT_RUN / 사람 리뷰 NOT_RUN / 게임 적용 NOT_RUN

**출처 스타일 표현:**

```text
pixel art, kawaii aesthetic, pastel color palette, 8-bit retro style, chibi character design, clean isolated sprite, nostalgic game asset
```

**후보 조합:** Krea2 Turbo · 현재 `krea2_base` · 현재 `qwen_image_vae.safetensors` · LoRA 없음. **이 조합은 아직 원본 샘플의 실제 재현을 검증하지 않았음.**
**피사체 누출 주의:** 외부 스타일 문장 자체에 인물/물체/장르 묘사가 포함되어 있을 수 있으므로 SOT 고정 요소에 섞지 않는다.
**특기:** 'This Krea preview does not establish native 32x32 pixel quality or alpha.'

---

## STYLE-006 — Engraved Ink Storybook

![외부 생성 미리보기 STYLE-006](https://raw.githubusercontent.com/ThetaCursed/Krea2-Style-Explorer/eb690aa57bc6974af6b4b3b8c5a780195bcadf78/images/1/a67caabb5179.webp)

**장르:** [MEDIEVAL_FANTASY, HISTORICAL, COZY]  
**애셋 역할 가설:** [PROP, BACKGROUND, CHARACTER]  
**외부 스타일 ID:** `a67caabb5179`  
**실험 상태:** 외부 샘플 있음 / 우리 Krea2 재현 NOT_RUN / Anima 변환 NOT_RUN / 사람 리뷰 NOT_RUN / 게임 적용 NOT_RUN

**출처 스타일 표현:**

```text
fine-line engraving, stippled pointillism, pastel botanical illustration, cross-hatching texture, whimsical storybook aesthetic, muted desaturated palette, intricate ink work
```

**후보 조합:** Krea2 Turbo · 현재 `krea2_base` · 현재 `qwen_image_vae.safetensors` · LoRA 없음. **이 조합은 아직 원본 샘플의 실제 재현을 검증하지 않았음.**
**피사체 누출 주의:** 외부 스타일 문장 자체에 인물/물체/장르 묘사가 포함되어 있을 수 있으므로 SOT 고정 요소에 섞지 않는다.

---

## STYLE-007 — Crimson Dark Fantasy Paint

![외부 생성 미리보기 STYLE-007](https://raw.githubusercontent.com/ThetaCursed/Krea2-Style-Explorer/eb690aa57bc6974af6b4b3b8c5a780195bcadf78/images/1/af70aeb23773.webp)

**장르:** [DARK_FANTASY, MEDIEVAL_FANTASY]  
**애셋 역할 가설:** [BACKGROUND, CHARACTER, PROP]  
**외부 스타일 ID:** `af70aeb23773`  
**실험 상태:** 외부 샘플 있음 / 우리 Krea2 재현 NOT_RUN / Anima 변환 NOT_RUN / 사람 리뷰 NOT_RUN / 게임 적용 NOT_RUN

**출처 스타일 표현:**

```text
dark gothic fantasy, chiaroscuro lighting, fiery crimson accents, expressive impasto texture, ominous atmosphere, dynamic painterly brushstrokes, high contrast composition
```

**후보 조합:** Krea2 Turbo · 현재 `krea2_base` · 현재 `qwen_image_vae.safetensors` · LoRA 없음. **이 조합은 아직 원본 샘플의 실제 재현을 검증하지 않았음.**

---

## STYLE-008 — Modern Flat Manga

![외부 생성 미리보기 STYLE-008](https://raw.githubusercontent.com/ThetaCursed/Krea2-Style-Explorer/eb690aa57bc6974af6b4b3b8c5a780195bcadf78/images/1/03efebcc9262.webp)

**장르:** [MODERN, SLICE_OF_LIFE, COMEDY]  
**애셋 역할 가설:** [CHARACTER, PROP, BACKGROUND]  
**외부 스타일 ID:** `03efebcc9262`  
**실험 상태:** 외부 샘플 있음 / 우리 Krea2 재현 NOT_RUN / Anima 변환 NOT_RUN / 사람 리뷰 NOT_RUN / 게임 적용 NOT_RUN

**출처 스타일 표현:**

```text
minimalist manga illustration, bold ink line art, solid vibrant background, flat color blocking, high contrast graphic art, slice of life anime, pop art aesthetic
```

**후보 조합:** Krea2 Turbo · 현재 `krea2_base` · 현재 `qwen_image_vae.safetensors` · LoRA 없음. **이 조합은 아직 원본 샘플의 실제 재현을 검증하지 않았음.**

---

## STYLE-009 — Graphic Retro Anime Risograph

![외부 생성 미리보기 STYLE-009](https://raw.githubusercontent.com/ThetaCursed/Krea2-Style-Explorer/eb690aa57bc6974af6b4b3b8c5a780195bcadf78/images/1/0bb1c8cab169.webp)

**장르:** [MODERN, FANTASY_CHIBI_SD, COMEDY, SF_CYBERPUNK]  
**애셋 역할 가설:** [CHARACTER, PROP]  
**외부 스타일 ID:** `0bb1c8cab169`  
**실험 상태:** 외부 샘플 있음 / 우리 Krea2 재현 NOT_RUN / Anima 변환 NOT_RUN / 사람 리뷰 NOT_RUN / 게임 적용 NOT_RUN

**출처 스타일 표현:**

```text
bold graphic illustration, risograph texture, saturated color blocking, stylized cartoon character, 90s anime influence, clean thick linework, playful whimsical mood
```

**후보 조합:** Krea2 Turbo · 현재 `krea2_base` · 현재 `qwen_image_vae.safetensors` · LoRA 없음. **이 조합은 아직 원본 샘플의 실제 재현을 검증하지 않았음.**
**피사체 누출 주의:** 외부 스타일 문장 자체에 인물/물체/장르 묘사가 포함되어 있을 수 있으므로 SOT 고정 요소에 섞지 않는다.

---

## STYLE-010 — Cozy Voxel Diorama

![외부 생성 미리보기 STYLE-010](https://raw.githubusercontent.com/ThetaCursed/Krea2-Style-Explorer/eb690aa57bc6974af6b4b3b8c5a780195bcadf78/images/1/6dbec3956138.webp)

**장르:** [FANTASY_CHIBI_SD, COZY, TACTICAL]  
**애셋 역할 가설:** [BACKGROUND, PROP]  
**외부 스타일 ID:** `6dbec3956138`  
**실험 상태:** 외부 샘플 있음 / 우리 Krea2 재현 NOT_RUN / Anima 변환 NOT_RUN / 사람 리뷰 NOT_RUN / 게임 적용 NOT_RUN

**출처 스타일 표현:**

```text
isometric voxel diorama, low-poly blocky style, soft directional lighting, cozy miniature aesthetic, warm earthy color palette, clean solid background, MagicaVoxel render
```

**후보 조합:** Krea2 Turbo · 현재 `krea2_base` · 현재 `qwen_image_vae.safetensors` · LoRA 없음. **이 조합은 아직 원본 샘플의 실제 재현을 검증하지 않았음.**
**피사체 누출 주의:** 외부 스타일 문장 자체에 인물/물체/장르 묘사가 포함되어 있을 수 있으므로 SOT 고정 요소에 섞지 않는다.
**특기:** '3D-looking style preview is not a Godot 3D/rig or production 3D mesh.'

---

## STYLE-011 — Clay Toy Chibi

![외부 생성 미리보기 STYLE-011](https://raw.githubusercontent.com/ThetaCursed/Krea2-Style-Explorer/eb690aa57bc6974af6b4b3b8c5a780195bcadf78/images/1/d5f832669a95.webp)

**장르:** [FANTASY_CHIBI_SD, COZY]  
**애셋 역할 가설:** [CHARACTER, PROP]  
**외부 스타일 ID:** `d5f832669a95`  
**실험 상태:** 외부 샘플 있음 / 우리 Krea2 재현 NOT_RUN / Anima 변환 NOT_RUN / 사람 리뷰 NOT_RUN / 게임 적용 NOT_RUN

**출처 스타일 표현:**

```text
3D claymation style, tactile toy aesthetic, soft pastel palette, matte and plush textures, chibi proportion, vibrant whimsical render, shallow depth of field
```

**후보 조합:** Krea2 Turbo · 현재 `krea2_base` · 현재 `qwen_image_vae.safetensors` · LoRA 없음. **이 조합은 아직 원본 샘플의 실제 재현을 검증하지 않았음.**
**피사체 누출 주의:** 외부 스타일 문장 자체에 인물/물체/장르 묘사가 포함되어 있을 수 있으므로 SOT 고정 요소에 섞지 않는다.
**특기:** '3D-looking style preview is not a Godot 3D/rig or production 3D mesh.'

---

## STYLE-012 — Punk Zine Monochrome

![외부 생성 미리보기 STYLE-012](https://raw.githubusercontent.com/ThetaCursed/Krea2-Style-Explorer/eb690aa57bc6974af6b4b3b8c5a780195bcadf78/images/1/960625243657.webp)

**장르:** [SF_CYBERPUNK, MODERN, PUNK]  
**애셋 역할 가설:** [CHARACTER, PROP, UI]  
**외부 스타일 ID:** `960625243657`  
**실험 상태:** 외부 샘플 있음 / 우리 Krea2 재현 NOT_RUN / Anima 변환 NOT_RUN / 사람 리뷰 NOT_RUN / 게임 적용 NOT_RUN

**출처 스타일 표현:**

```text
high-contrast monochrome, photocopy texture, punk zine aesthetic, stark black and white, gritty halftone, distressed ink, avant-garde editorial
```

**후보 조합:** Krea2 Turbo · 현재 `krea2_base` · 현재 `qwen_image_vae.safetensors` · LoRA 없음. **이 조합은 아직 원본 샘플의 실제 재현을 검증하지 않았음.**

---

## 모델별 검증 및 실제 레시피 승격 Gate

| 단계 | 성공 조건 | 현재 |
|---|---|---|
| 외부 시각 예시 | 원본 스타일 ID+이미지+문구 연결 | **12개 출처 대조 완료** |
| 우리 Krea2 재현 | 정확한 모델/노드/seed/prompt/원본 이미지 해시 기록 | NOT_RUN |
| Anima 변환 | 의미 보존 어댑터로 같은 인물·배경을 생성 | NOT_RUN |
| 스타일 재현성 | 캐릭터·환경·소품 전환에도 선/색/질감 일관 | NOT_RUN |
| 기술 게이트 | PNG 무결성, 지원되는 해상도, 필요한 alpha/후처리 | NOT_RUN |
| 인게임 평가 | 실제 32px/출력 화소·표시 배경·가독성 등 역할별 검수 | NOT_RUN |
| Golden 승인 | 사용자 직접 스타일 결과 선택 + 프로젝트 SOT | 0 |

**실험 계획(실제 생성하지 않음):** `python scripts/style_menu.py plan --output workspace/style_menu/pilot_plan.json`. 선정 4종 × 공통 인물·배경 2종 × Krea2/Anima 2종 = 제안 16개 후보. 현재 새 생성 예산 0. 32px 화풍은 이 실험과 독립적으로 검증.

**운영 경계:** 스타일을 번호로 선택한 다음 모델별 어댑터와 프롬프트를 편집할 수 있지만, 승인된 원본 외형·팔레트·장비는 프로젝트 SOT가 정의한다. 외부 이미지는 링크 방식으로만 표기하며 사용 권리는 별도 검토한다.
