"""Research-only compiler for numbered NONPIXEL menu candidates.

It returns a structured *prompt study* packet for a Codex/Claude agent to adapt
against actual project SOT. It does NOT auto-generate and is not a second router.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from assetpipe.styles.contracts import load_style_contract

ROOT = Path(__file__).resolve().parents[1]
MENU = "config/style_menu/candidates_v0.yaml"
RESEARCH = "config/style_menu/nonpixel_prompt_research_v0.yaml"
WORKFLOWS = "config/workflow_registry.yaml"
PROFILES = "config/model_profiles.yaml"
HOLD_STYLE = "STYLE-005"


def _read(root, path):
    value = yaml.safe_load((root / path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Malformed YAML: {path}")
    return value


def inspect(root=ROOT):
    root = Path(root).resolve()
    menu = _read(root, MENU)
    config = _read(root, RESEARCH)
    workflows = _read(root, WORKFLOWS)["workflows"]
    profiles = _read(root, PROFILES)["profiles"]
    cards = {card["menu_id"]: card for card in menu["cards"]}
    research = config.get("recipes", {})
    if config.get("status") != "OFFLINE_PROMPT_STUDY" or menu.get("validation_state") != "EXTERNAL_PREVIEW_ONLY":
        raise ValueError("Research study cannot assert visual validation")
    if config.get("global_rules", {}).get("no_pixel_generation") is not True:
        raise ValueError("Pixel generation must remain held")
    if config["global_rules"]["pixel_menus_hold"] != [HOLD_STYLE]:
        raise ValueError("Pixel hold list drift")
    if (HOLD_STYLE not in cards or "PIXEL" not in cards[HOLD_STYLE]["genre_tags"] or
            cards[HOLD_STYLE].get("experiment_status") != "HOLD_PIXEL_NO_GENERATION"):
        raise ValueError("Pixel entry/hold mismatch")
    expected = set(cards) - {HOLD_STYLE}
    if set(research) != expected:
        raise ValueError(f"Research/menu card mismatch: missing {sorted(expected-set(research))}; extra {sorted(set(research)-expected)}")
    for workflow, scope in config["model_scopes"].items():
        if workflow not in {"krea2_base", "anima_base"}:
            raise ValueError("Only Anima Base and Krea2 Turbo allowed for style research")
        entry = workflows[workflow]
        if (entry["output_class"] != "NONPIXEL_IMAGE" or entry["status"] != "ACTIVE" or
                scope["profile"] != entry["model_profile"] or scope["file"] != entry["workflow_file"]):
            raise ValueError(f"Invalid workflow profile/graph binding: {workflow}")
        actual = entry["models"]
        if (scope["base_model"] not in actual.get("diffusion_models", []) or
                scope["text_encoder"] not in actual.get("text_encoders", []) or
                scope["vae"] not in actual.get("vae", []) or scope["loras"]):
            raise ValueError(f"Model/encoder/VAE/LoRA claims do not match registry: {workflow}")
        if scope["recipe_policy"] == "KREA_NATURAL_LANGUAGE":
            if profiles[scope["profile"]]["prompt_adapter"] != "krea2":
                raise ValueError("Invalid Krea2 adapter")
        elif scope["recipe_policy"] == "ANIMA_TAGS_PLUS_CAPTION":
            if profiles[scope["profile"]]["prompt_adapter"] != "anima":
                raise ValueError("Invalid Anima adapter")
        else:
            raise ValueError("Unknown study prompt dialect")
    for style_id, entry in research.items():
        if (entry["status"] != "RESEARCH_NOT_RUN" or
                entry["output_class"] != "NONPIXEL_IMAGE" or
                entry["image_validation"] != "NOT_RUN" or
                entry["repeated_seeds"] != "NOT_RUN" or
                entry["game_size_validation"] != "NOT_RUN" or
                entry["human_approval"] is not False):
            raise ValueError(f"Research candidate attempts an unreviewed promotion: {style_id}")
        if not entry["krea2_base"].get("style_clause") or entry["krea2_base"]["negative_native"] != "UNSUPPORTED":
            raise ValueError(f"Krea2 style clause / capability invalid: {style_id}")
        anima = entry["anima_base"]
        if style_id in {"STYLE-001", "STYLE-004"}:
            contract = load_style_contract(root, style_id)
            expected_ref = f"config/styles/catalog.yaml#/styles/{style_id}/style_contract"
            if (anima.get("contract_ref") != expected_ref or
                    anima.get("positive_dialect") != "STRUCTURED_STYLE_CONTRACT" or
                    "positive_tags" in anima or "natural_language_caption" in anima):
                raise ValueError(f"Invalid structured Anima Style Contract reference: {style_id}")
            if contract["id"] != style_id:
                raise ValueError(f"Anima Style Contract identity mismatch: {style_id}")
        elif (not anima.get("positive_tags") or
              not anima.get("natural_language_caption") or
              anima.get("optional_negative") != []):
            raise ValueError(f"Invalid Anima research dialect or unapproved negative: {style_id}")
        if "project_subject_identity" not in entry["locked_axes"]:
            raise ValueError(f"Canon may not be edited by style recipe: {style_id}")
        if "PIXEL" in cards[style_id]["genre_tags"]:
            raise ValueError(f"Pixel card may not enter nonpixel research: {style_id}")
    return {"status": "OFFLINE_PROMPT_STUDY", "model_workflows": sorted(config["model_scopes"]),
            "research_style_count": len(research), "pixel_holds": [HOLD_STYLE],
            "cli_providers": "SMOKE_ONLY",
            "generated": 0, "approved": 0}


def export_packet(root, style_id, workflow_id, subject_text):
    root = Path(root).resolve()
    inspect(root)
    style = _read(root, RESEARCH)["recipes"].get(style_id)
    cards = {c["menu_id"]: c for c in _read(root, MENU)["cards"]}
    if style_id == HOLD_STYLE:
        raise ValueError("STYLE-005 PIXEL HOLD; cannot export nonpixel research recipe")
    if style is None:
        raise ValueError(f"Unknown menu style: {style_id}")
    if workflow_id not in {"krea2_base", "anima_base"}:
        raise ValueError(f"Unsupported style research workflow: {workflow_id}")
    if not isinstance(subject_text, str) or len(subject_text.strip()) < 15:
        raise ValueError("Subject facts must come from validated project SOT or a labelled synthetic fixture")
    details = style[workflow_id]
    contract_ref = None
    if workflow_id == "krea2_base":
        prototype = subject_text.strip() + " Style direction: " + details["style_clause"]
        dialect = "NATURAL_LANGUAGE; mandatory independent semantic review before actual runtime PromptSpec"
    elif details.get("contract_ref"):
        # Research export preserves provenance and the structured reference only.
        # Final model text is compiled from PromptSpec at runtime, never authored here.
        prototype = None
        contract_ref = details["contract_ref"]
        dialect = "STRUCTURED_STYLE_CONTRACT; compiled by the PromptSpec model-dialect compiler"
    else:
        prototype = ", ".join(details["positive_tags"]) + ". " + subject_text.strip() + " " + details["natural_language_caption"]
        dialect = "ANIMA_TAGS_PLUS_CAPTION; preserve original model native prompt compiler"
    model = _read(root, RESEARCH)["model_scopes"][workflow_id]
    card = cards[style_id]
    return {
        "status": "OFFLINE_RESEARCH_CANDIDATE_NOT_FOR_DIRECT_DISPATCH",
        "source_style": {"menu_id": style_id, "explorer_id": card["source_id"],
                         "preview": card["preview"], "original_style_prompt": card["source_prompt"]},
        "output_class": "NONPIXEL_IMAGE", "workflow_id": workflow_id,
        "model_weight": model["base_model"], "text_encoder": model["text_encoder"],
        "vae": model["vae"], "loras": [],
        "prompt_dialect": dialect, "style_contract_ref": contract_ref,
        "example_unapproved_compiled_text": prototype,
        "suggested_editable_axes": style["editable_axes"], "canon_locked_axes": style["locked_axes"],
        "prompt_risk": style["failure_risk"],
        "original_image_reproduction": "NOT_RUN",
        "human_review": "NOT_RUN", "project_approval": False,
        "generation_requests": 0, "local_model_quality": "UNKNOWN",
        "agent_next_step": "Read project ACTIVE/SOT; compose existing Asset Brief/PromptSpec and evaluate before a separately authorized generation.",
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", choices=["check", "export"])
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--style", help="STYLE-001 ... STYLE-012, except held STYLE-005")
    ap.add_argument("--workflow", choices=["krea2_base", "anima_base"])
    ap.add_argument("--subject", help="Synthetic test fixture or facts already verified against project SOT")
    ap.add_argument("--output", type=Path)
    args = ap.parse_args(argv)
    if args.command == "export":
        if not args.style or not args.workflow or not args.subject:
            ap.error("export requires --style, --workflow and --subject")
        data = export_packet(args.root, args.style, args.workflow, args.subject)
    else:
        data = inspect(args.root)
    payload = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8", newline="\n")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
