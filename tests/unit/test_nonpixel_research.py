"""Nonpixel model-specific menu prompt research integrity.

This suite must never call ComfyUI or any image generation provider.
"""
import copy
import json
from pathlib import Path

import pytest
import yaml

from scripts import nonpixel_research, style_menu

ROOT = Path(__file__).resolve().parents[2]


def test_all_nonpixel_menus_have_two_model_specific_prompt_studies():
    state = nonpixel_research.inspect()
    assert state["status"] == "OFFLINE_PROMPT_STUDY"
    assert state["model_workflows"] == ["anima_base", "krea2_base"]
    assert state["research_style_count"] == 11
    assert state["pixel_holds"] == ["STYLE-005"]
    assert state["cli_providers"] == "SMOKE_ONLY"
    assert state["generated"] == state["approved"] == 0


def test_export_project_canon_is_not_changed_and_lora_none():
    subject = "One adult guard with brown hair wearing a blue coat and carrying a brass compass."
    anima = nonpixel_research.export_packet(ROOT, "STYLE-004", "anima_base", subject)
    krea = nonpixel_research.export_packet(ROOT, "STYLE-004", "krea2_base", subject)
    assert anima["example_unapproved_compiled_text"] is None
    assert anima["style_contract_ref"] == "config/styles/catalog.yaml#/styles/STYLE-004/style_contract"
    assert "STRUCTURED_STYLE_CONTRACT" in anima["prompt_dialect"]
    assert subject in krea["example_unapproved_compiled_text"]
    for packet in (anima, krea):
        assert packet["output_class"] == "NONPIXEL_IMAGE"
        assert packet["loras"] == []
        assert packet["vae"] == "qwen_image_vae.safetensors"
        assert packet["project_approval"] is False
        assert packet["generation_requests"] == 0
        assert packet["original_image_reproduction"] == "NOT_RUN"
        assert "project_subject_identity" in packet["canon_locked_axes"]
    assert "gouache" in krea["example_unapproved_compiled_text"]


def test_nonpixel_research_rejects_pixel_and_cli_providers():
    subject = "Exactly one adult traveler in an unadorned blue coat, standing."
    with pytest.raises(ValueError, match="PIXEL HOLD"):
        nonpixel_research.export_packet(ROOT, "STYLE-005", "krea2_base", subject)
    with pytest.raises(ValueError, match="Unsupported style research workflow"):
        nonpixel_research.export_packet(ROOT, "STYLE-004", "codex_imagegen", subject)
    with pytest.raises(ValueError, match="Subject facts"):
        nonpixel_research.export_packet(ROOT, "STYLE-004", "krea2_base", "fantasy")


def test_menu_pilot_is_nonpixel_only_and_excludes_005():
    plan = style_menu.pilot_plan(style_menu.load_menu())
    assert plan["proposed_jobs"] == 16
    assert set(x["style_id"] for x in plan["jobs"]) == {
        "STYLE-001", "STYLE-004", "STYLE-006", "STYLE-008"
    }
    assert plan["pixel_style_hold"] == ["STYLE-005"]
    assert plan["pixel_quality_test"] == "ON_HOLD_NO_GENERATION"
    assert plan["experiment_scope"] == "NONPIXEL_IMAGE_ONLY"
    assert plan["generation_budget_approved"] == 0
    pair_krea = next(x for x in plan["jobs"] if x["style_id"] == "STYLE-004" and x["workflow"] == "krea2_base")
    pair_anima = next(x for x in plan["jobs"] if x["style_id"] == "STYLE-004" and x["workflow"] == "anima_base")
    assert pair_krea["model_specific_study"]["positive_dialect"] == "NATURAL_LANGUAGE"
    assert pair_anima["model_specific_study"]["positive_dialect"] == "STRUCTURED_STYLE_CONTRACT"
    assert pair_krea["lora_weights"] == pair_anima["lora_weights"] == []
    assert pair_krea["model_dialect_compiler_required"]
    assert pair_krea["study_state"] == "OFFLINE_RESEARCH_NOT_RUN"


def test_upstream_preview_cannot_be_approved_via_recipe_text(tmp_path):
    target = tmp_path
    for relative in [
        "config/style_menu/nonpixel_prompt_research_v0.yaml",
        "config/style_menu/candidates_v0.yaml",
        "config/workflow_registry.yaml",
        "config/model_profiles.yaml",
        "config/styles/catalog.yaml"
    ]:
        dest = target / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((ROOT / relative).read_bytes())
    config = yaml.safe_load((target / "config/style_menu/nonpixel_prompt_research_v0.yaml").read_text())
    config["recipes"]["STYLE-001"]["human_approval"] = True
    (target / "config/style_menu/nonpixel_prompt_research_v0.yaml").write_text(
        yaml.safe_dump(config, allow_unicode=True), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="unreviewed promotion"):
        nonpixel_research.inspect(target)


def test_cli_export_offline(tmp_path):
    output = tmp_path / "packet.json"
    assert nonpixel_research.main([
        "export", "--style", "STYLE-008", "--workflow", "anima_base",
        "--subject", "One adult person in a plain blue jacket holding a brass compass.",
        "--output", str(output)
    ]) == 0
    packet = json.loads(output.read_text(encoding="utf-8"))
    assert packet["generation_requests"] == 0
    assert packet["model_weight"] == "anima-base-v1.0.safetensors"
    assert "flat" in packet["example_unapproved_compiled_text"].lower()
