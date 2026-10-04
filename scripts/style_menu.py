"""Build an *illustrated candidate* style menu from pinned Krea Explorer references.

No model inference, no generation calls, no approved recipe promotion.
Usage:
    python scripts/style_menu.py check
    python scripts/style_menu.py render --output docs/style_menu/CANDIDATE_MENU_v0.md
    python scripts/style_menu.py plan --output workspace/style_menu/pilot_plan.json
    python scripts/style_menu.py check --upstream-data ../Krea2-Style-Explorer/app/data.js \
        --upstream-images ../Krea2-Style-Explorer/images
"""
import argparse
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "config/style_menu/candidates_v0.yaml"
IDS = ("STYLE-001", "STYLE-004", "STYLE-006", "STYLE-008")  # 4 NONPIXEL genre pilots; PIXEL STYLE-005 HELD
SUBJECTS = {
    "CHARACTER": {
        "text": "Exactly one adult traveler standing full body, short dark brown hair, plain blue coat, a brass compass held in the left hand, feet visible, front three-quarter view, centered.",
        "must_have": ["one complete adult", "blue coat", "brass compass in left hand", "feet visible", "three-quarter view"],
    },
    "ENVIRONMENT": {
        "text": "An empty single-arched stone bridge across a calm canal, one red lantern hanging beneath the arch, overcast daylight, wide view with foreground bridge, middle canal and background trees.",
        "must_have": ["exactly one arch", "one red lantern", "calm canal", "foreground/middle/background separation", "no people"],
    },
}


def load_menu(path=CATALOG):
    obj = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(obj, dict) or obj.get("schema_version") != 1:
        raise ValueError("Invalid menu schema")
    if obj.get("validation_state") != "EXTERNAL_PREVIEW_ONLY" or obj.get("canonical_project_approval") is not False:
        raise ValueError("Menu cannot claim local validation/approval")
    cards = obj.get("cards")
    if not isinstance(cards, list) or not cards:
        raise ValueError("Style cards must be a nonempty list")
    return obj


def parse_upstream(path):
    source = Path(path).read_text(encoding="utf-8")
    prefix = "const galleryData = "
    if not source.startswith(prefix) or not source.rstrip().endswith("];"):
        raise ValueError("Unexpected upstream data.js format")
    rows = json.loads(source[len(prefix):].rstrip().removesuffix(";"))
    if not isinstance(rows, list):
        raise ValueError("Upstream gallery data must be a list")
    return {row["id"]: row for row in rows}


def validate(obj, root=ROOT, upstream_data=None, upstream_images=None):
    import re
    from collections import Counter
    ref = obj["source"]
    if not re.fullmatch(r"[a-f0-9]{40}", ref.get("revision", "")):
        raise ValueError("Upstream source must pin a real 40-char commit SHA")
    if obj["model_experiment_policy"]["local_reproduction"] != "NOT_RUN":
        raise ValueError("Do not claim undocumented local test completion")
    src = parse_upstream(upstream_data) if upstream_data else None
    models = yaml.safe_load((root / "config/workflow_registry.yaml").read_text(encoding="utf-8"))["workflows"]
    style_ids = set()
    counts = Counter()
    for index, card in enumerate(obj["cards"], 1):
        menu_id = card.get("menu_id", "")
        if not re.fullmatch(r"STYLE-\d{3}", menu_id) or menu_id in style_ids:
            raise ValueError(f"Missing/duplicate stable menu ID: {menu_id}")
        if int(menu_id[-3:]) != index:
            raise ValueError("Menu cards must use contiguous stable numbered IDs")
        style_ids.add(menu_id)
        if (menu_id == "STYLE-005") != (card.get("experiment_status") == "HOLD_PIXEL_NO_GENERATION"):
            raise ValueError("PIXEL HOLD policy must apply only to STYLE-005")
        source_id = card.get("source_id", "")
        folder = card.get("source_folder")
        if not re.fullmatch(r"[a-f0-9]{12}", source_id) or folder not in {"1", "2"}:
            raise ValueError(f"Unrecognized source ID: {menu_id}")
        exact_url = ("https://raw.githubusercontent.com/ThetaCursed/Krea2-Style-Explorer/"
                     + ref["revision"] + "/images/" + folder + "/" + source_id + ".webp")
        if card.get("preview") != exact_url:
            raise ValueError(f"Preview not pinned to matching style ID: {menu_id}")
        prompt = card.get("source_prompt")
        if not isinstance(prompt, str) or len(prompt) < 20:
            raise ValueError(f"Empty source prompt: {menu_id}")
        if src is not None:
            original = src.get(source_id)
            if not original or original["prompt"] != prompt or original["folder"] != folder:
                raise ValueError(f"Source prompt/gallery mismatch: {menu_id}")
        if upstream_images:
            if not (Path(upstream_images) / folder / (source_id + ".webp")).is_file():
                raise ValueError(f"Missing original image: {menu_id}")
        for field in ("tested_on_local_krea2", "tested_on_local_anima", "verified_in_game", "approved"):
            if card.get(field) is not False:
                raise ValueError(f"Unreviewed menu entry cannot declare {field}: {menu_id}")
        if card.get("base_workflow") != "krea2_base" or card.get("alternate_workflow") != "anima_base":
            raise ValueError(f"Preview model must stay Krea2 and Anima transfer untested: {menu_id}")
        wf = models[card["base_workflow"]]
        if wf["output_class"] != "NONPIXEL_IMAGE" or wf["status"] != "ACTIVE":
            raise ValueError(f"Cannot route preview to unsupported output class: {menu_id}")
        if card["lora_required"] is not False or card["vae"] not in wf["models"]["vae"]:
            raise ValueError(f"Invalid Krea2 base VAE or LoRA claim: {menu_id}")
        for name in ("genre_tags", "asset_roles"):
            if not card.get(name) or not isinstance(card[name], list):
                raise ValueError(f"Missing {name}: {menu_id}")
        counts.update(card["genre_tags"])
    return {"state": "EXTERNAL_PREVIEW_ONLY", "cards": len(style_ids),
            "categories": dict(counts), "local_model_generations": 0,
            "approved_cards": 0, "upstream_verified": bool(src),
            "original_image_paths_verified": bool(upstream_images)}


def markdown_menu(obj):
    lines = [
        "# 화풍 메뉴판 — 탐색 후보 v0.1 (외부 Krea2 샘플, 미검증)",
        "",
        "> **상태: EXTERNAL_PREVIEW_ONLY.** 이 카드들은 ThetaCursed가 만든 Krea2 Turbo 예시이지",
        "> 현재 Asset-Pipeline의 로컬 생성 실험·사람 승인·32px 검증 결과가 아니다.",
        "> 원본 미리보기는 링크로 표시하며 이미지를 저장소에 재배포하지 않는다.",
        "> 모든 후보는 **0개 실사용 승인** 상태이고, 번호 선택만으로 자동 생성하지 않는다.",
        "",
        f"원본: [Krea2 Style Explorer]({obj['source']['url']}) · "
        f"[원본 코드]({obj['source']['repo']}) · 고정 커밋 `{obj['source']['revision'][:12]}`.",
        "",
        "## 장르별 후보 번호 (품질 추천·순위가 아님)",
        "",
    ]
    genres = {}
    for card in obj["cards"]:
        for genre in card["genre_tags"]:
            genres.setdefault(genre, []).append(card["menu_id"])
    for genre, ids in sorted(genres.items()):
        lines.append(f"- **{genre.replace('_', ' ')}**: " + ", ".join(f"`{s}`" for s in ids))
    lines.extend(["", "---", ""])
    for card in obj["cards"]:
        lines.extend([
            f"## {card['menu_id']} — {card['title']}",
            "",
            f"![외부 제작자 스타일 예시 — {card['menu_id']}]({card['preview']})",
            "",
            "**상태:** EXTERNAL_PREVIEW_ONLY · 로컬 Krea2 재현 NOT_RUN · Anima 이식 NOT_RUN · human review NOT_RUN · 프로젝트 승인 없음.",
            "",
            "**장르:** " + ", ".join(card["genre_tags"]) + " · **애셋:** " + ", ".join(card["asset_roles"]),
            "",
            f"**원본 스타일 ID:** `{card['source_id']}` · **사용 의도 가설:** `krea2_base`",
            " / `qwen_image_vae.safetensors` / LoRA 없음.",
            "",
            "**원본 스타일 묘사(제작자 제공, 아직 대상 분리·모델별 이식 검증 안 됨):**",
            "",
            "```text",
            card["source_prompt"],
            "```",
            "",
            "**통과해야 사용할 수 있는 조건:** 같은 스타일로 전신 인물·배경 등",
            "서로 다른 테스트를 실제 생성하고, 구조 보존·선명도·인게임 크기·권리를 평가.",
            "",
        ])
        if card.get("warning"):
            lines.extend(["**주의:** " + card["warning"], ""])
        if card.get("subject_baked_in"):
            lines.extend(["**피사체 오염 위험:** 외부 스타일 문자열 자체에 특정 피사체/물체가 포함되어 있어 그대로 합성하면 캐논을 침범할 수 있음.", ""])
        lines.extend(["---", ""])
    lines.extend([
        "## 픽셀 홀드: STYLE-005",
        "",
        "STYLE-005의 출처 미리보기는 검색용으로만 남긴다. **32px/64px 픽셀 실험은 HOLD이며**",
        "비픽셀 최초 pilot의 생성 대상에서 제외한다.",
        "",
        "## 실험에서 승인 카드로 전환하는 기준",
        "",
        "외부 미리보기(탐색) → Krea2 로컬 재현 → Anima 모델별 별도 비교 →",
        "전신 인물/소품/배경의 프롬프트 의미 보존 → 시각 리뷰 →",
        "목표 게임 크기 리뷰 → 라이선스 검토 및 사용자 승인.",
        "",
        "32px와 64px Pixel Gate는 별도의 목표 해상도 실험이다.",
        "이미지 개수·기술 PASS만으로 승인하지 않으며 Krea Style Explorer 외부 이미지에",
        "대한 권리는 별도 검토한다.",
        "",
        "실험계획: `python scripts/style_menu.py plan --output workspace/style_menu/pilot_plan.json`",
        " (계획 JSON만 생성; 모델 구동·GPU 사용 0건).",
    ])
    return "\n".join(lines) + "\n"


def pilot_plan(obj):
    cards = {c["menu_id"]: c for c in obj["cards"]}
    if any("PIXEL" in cards[x]["genre_tags"] for x in IDS):
        raise ValueError("Pixel menu cannot enter NONPIXEL pilot")
    jobs = []
    for style_id in IDS:
        card = cards[style_id]
        for subject_id, subject in SUBJECTS.items():
            for workflow in ("krea2_base", "anima_base"):
                jobs.append({
                    "style_id": style_id, "source_style_id": card["source_id"],
                    "subject_fixture": subject_id, "canonical_requirements": subject["must_have"],
                    "subject": subject["text"],
                    "source_style_prompt": card["source_prompt"],
                    "workflow": workflow,
                    "seed": 7725, "prompt_adapter": "krea2" if workflow == "krea2_base" else "anima",
                    "status": "PLANNED_NOT_AUTHORIZED", "artifact": None,
                    "semantic_review": "NOT_REVIEWED", "art_review": "NOT_REVIEWED",
                    "experiment_note": ("Do not copy Krea2 raw string directly as Anima tags: "
                                        "independent meaning-preserving adapter review first"),
                })
    return {
        "experiment_id": "STYLE_MENU_PILOT_A_20261004",
        "status": "PLANNED_NOT_AUTHORIZED",
        "generation_budget_approved": 0,
        "generation_requests_submitted": 0,
        "proposed_jobs": len(jobs),
        "pixel_quality_test": "ON_HOLD_NO_GENERATION",
        "pixel_style_hold": ["STYLE-005"],
        "experiment_scope": "NONPIXEL_IMAGE_ONLY",
        "same_seed_is_not_equivalent_noise": True,
        "can_promote_without_human_review": False,
        "jobs": jobs,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["check", "render", "plan"])
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--upstream-data", type=Path)
    parser.add_argument("--upstream-images", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    obj = load_menu(args.root / "config/style_menu/candidates_v0.yaml")
    result = validate(obj, args.root, args.upstream_data, args.upstream_images)
    if args.command == "render":
        output = markdown_menu(obj)
    elif args.command == "plan":
        output = json.dumps(pilot_plan(obj), indent=2, ensure_ascii=False) + "\n"
    else:
        output = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8", newline="\n")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
