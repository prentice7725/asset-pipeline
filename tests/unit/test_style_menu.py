"""Offline curated gallery tests. Never generate images or promote menu choices."""
import copy
import json
from pathlib import Path

import pytest

from scripts import style_menu

ROOT = Path(__file__).resolve().parents[2]


def test_numbered_menu_consistent_with_registered_krea2_workflow():
    menu = style_menu.load_menu()
    status = style_menu.validate(menu)
    assert status["state"] == "EXTERNAL_PREVIEW_ONLY"
    assert status["cards"] == 12
    assert status["local_model_generations"] == 0
    assert status["approved_cards"] == 0
    assert status["upstream_verified"] is False
    assert "FANTASY_CHIBI_SD" in status["categories"]
    assert "SF_CYBERPUNK" in status["categories"]


def test_style_005_is_candidate_not_a_proven_native_pixel_sprite():
    item = next(x for x in style_menu.load_menu()["cards"] if x["menu_id"] == "STYLE-005")
    assert "chibi" in item["source_prompt"]
    assert "32x32" in item["warning"]
    assert item["experiment_status"] == "HOLD_PIXEL_NO_GENERATION"
    assert item["base_workflow"] == "krea2_base"
    assert item["approved"] is False


def test_gallery_has_previews_and_exact_source_prompts():
    obj = style_menu.load_menu()
    doc = style_menu.markdown_menu(obj)
    assert doc.count("![외부 제작자 스타일 예시") == 12
    for item in obj["cards"]:
        assert item["source_prompt"] in doc
        assert item["preview"] in doc
    assert "NOT_RUN" in doc


def test_plan_is_no_execution_and_no_quality_approval():
    plan = style_menu.pilot_plan(style_menu.load_menu())
    assert plan["proposed_jobs"] == 16
    assert plan["generation_budget_approved"] == 0
    assert plan["generation_requests_submitted"] == 0
    assert set(x["workflow"] for x in plan["jobs"]) == {"krea2_base", "anima_base"}
    assert set(x["subject_fixture"] for x in plan["jobs"]) == {"CHARACTER", "ENVIRONMENT"}
    assert all(x["status"] == "PLANNED_NOT_AUTHORIZED" and x["artifact"] is None for x in plan["jobs"])


def test_gallery_duplicate_id_or_fake_approval_blocked():
    obj = style_menu.load_menu()
    obj["cards"][1]["menu_id"] = "STYLE-001"
    with pytest.raises(ValueError, match="duplicate"):
        style_menu.validate(obj)
    obj = style_menu.load_menu()
    obj["cards"][0]["approved"] = True
    with pytest.raises(ValueError, match="cannot declare approved"):
        style_menu.validate(obj)


def test_gallery_preview_id_cannot_mismatch_original():
    obj = style_menu.load_menu()
    obj["cards"][0]["preview"] = obj["cards"][1]["preview"]
    with pytest.raises(ValueError, match="Preview not pinned"):
        style_menu.validate(obj)


def test_upstream_drift_is_rejected(tmp_path):
    obj = style_menu.load_menu()
    upstream = tmp_path / "data.js"
    data = [
        {"id": c["source_id"], "prompt": c["source_prompt"], "folder": c["source_folder"]}
        for c in obj["cards"]
    ]
    upstream.write_text("const galleryData = " + json.dumps(data) + ";", encoding="utf-8")
    assert style_menu.validate(obj, upstream_data=upstream)["upstream_verified"]
    data[0]["prompt"] = "A changed prompt!"
    upstream.write_text("const galleryData = " + json.dumps(data) + ";", encoding="utf-8")
    with pytest.raises(ValueError, match="Source prompt/gallery mismatch"):
        style_menu.validate(obj, upstream_data=upstream)


def test_cli_check_render_and_plan_do_not_generate(tmp_path):
    check = tmp_path / "check.json"
    md = tmp_path / "menu.md"
    plan = tmp_path / "plan.json"
    assert style_menu.main(["check", "--output", str(check)]) == 0
    assert style_menu.main(["render", "--output", str(md)]) == 0
    assert style_menu.main(["plan", "--output", str(plan)]) == 0
    assert json.loads(check.read_text())["local_model_generations"] == 0
    assert json.loads(plan.read_text())["generation_budget_approved"] == 0
    assert "STYLE-001" in md.read_text()
    assert "STYLE-012" in md.read_text()
