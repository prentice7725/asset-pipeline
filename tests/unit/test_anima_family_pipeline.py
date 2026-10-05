import json
from pathlib import Path

import pytest

from assetpipe.registry import load_registry
from assetpipe.prompts import compile_prompt, workflow_values
from scripts import anima_family_pipeline as afp

ROOT = Path(__file__).resolve().parents[2]


def test_anima_family_registry_uses_separate_experimental_profiles():
    state = afp.inspect(ROOT)
    assert state["status"] == "PIPELINE_CONFIG_VALID"
    assert set(state["workflows"]) == {"anima_base_rebuilt", "anima_turbo"}
    base = state["workflows"]["anima_base_rebuilt"]
    turbo = state["workflows"]["anima_turbo"]
    assert base["profile"] == "anima-base-rebuilt"
    assert turbo["profile"] == "anima-turbo"
    assert base["preset"]["steps"] == 30
    assert base["preset"]["cfg"] == 4.0
    assert base["preset"]["sampler"] == "er_sde"
    assert turbo["preset"]["steps"] == 10
    assert turbo["preset"]["cfg"] == 1.0
    assert turbo["preset"]["sampler"] == "euler"


def test_anima_hybrid_compiler_applies_official_prefix_and_negative():
    registry = load_registry(ROOT)
    research = afp._yaml(ROOT / "config/style_menu/nonpixel_prompt_research_v0.yaml")["recipes"]
    brief = afp._fixture("STYLE-001", research["STYLE-001"], "anima_base_rebuilt")
    compiled = compile_prompt(brief, registry["anima_base_rebuilt"], ROOT)
    assert compiled["adapter"] == "anima_hybrid"
    assert compiled["positive"].startswith("masterpiece, best quality, score_7, safe.")
    assert "Depict Exactly one adult traveler" in compiled["positive"]
    assert "Appearance:" not in compiled["positive"]  # all appearance facts are already in subject/equipment contract
    assert "Style direction:" in compiled["positive"]
    assert "whole character in frame from head to toe" in compiled["positive"]
    assert compiled["negative"].startswith(", ".join(afp.OFFICIAL_NEGATIVE))
    assert compiled["contract_negative_guards"] == [
        "duplicate required equipment", "extra copies of required equipment"
    ]
    assert compiled["negative"].endswith("duplicate required equipment, extra copies of required equipment")
    assert compiled["negative_mode"] == "NATIVE"
    assert compiled["compiler_revision"] == "anima_hybrid_v2"
    assert compiled["positive"].lower().count("compass") == 1
    assert "simple subdued neutral environment" not in compiled["positive"].lower()
    assert "consistent with the selected style direction" in compiled["positive"].lower()
    values = workflow_values(compiled, registry["anima_base_rebuilt"], brief)
    assert (values["width"], values["height"], values["steps"], values["cfg"]) == (512, 768, 30, 4.0)


def test_turbo_uses_same_canonical_fixture_but_native_turbo_preset():
    registry = load_registry(ROOT)
    research = afp._yaml(ROOT / "config/style_menu/nonpixel_prompt_research_v0.yaml")["recipes"]
    base_brief = afp._fixture("STYLE-004", research["STYLE-004"], "anima_base_rebuilt")
    turbo_brief = afp._fixture("STYLE-004", research["STYLE-004"], "anima_turbo")
    assert base_brief["prompt_spec"] == turbo_brief["prompt_spec"]
    assert base_brief["prompt_spec"]["subject_integrity"]["camera_view"] == "front"
    assert "anatomical left hand" in base_brief["prompt_spec"]["subject_integrity"]["equipment"][0]["source_trait"]
    compiled = compile_prompt(turbo_brief, registry["anima_turbo"], ROOT)
    values = workflow_values(compiled, registry["anima_turbo"], turbo_brief)
    assert compiled["profile_id"] == "anima-turbo"
    assert "small body" not in compiled["positive"].lower()
    assert "chibi" not in compiled["positive"].lower()
    assert "gouache" in compiled["positive"].lower()
    assert (values["width"], values["height"], values["steps"], values["cfg"], values["sampler"]) == (
        512, 768, 10, 1.0, "euler"
    )


def test_plan_is_four_cells_no_generation_no_lora_no_vae_change(tmp_path):
    path = tmp_path / "plan.json"
    result = afp.plan(ROOT, path)
    assert result["status"] == "PREPARED_NOT_EXECUTED"
    assert result["cohort"] == afp.COHORT
    assert result["supersedes_r1_evidence_commit"] == afp.R1_EVIDENCE_COMMIT
    assert result["reserved_calls_required"] == 4
    assert result["generation_requests"] == 0
    assert result["pixel_generation"] == 0
    assert result["lora_changes"] == 0
    assert result["vae_changes"] == 0
    assert len(result["jobs"]) == 4
    assert {j["style_id"] for j in result["jobs"]} == {"STYLE-001", "STYLE-004"}
    assert {j["workflow_id"] for j in result["jobs"]} == {"anima_base_rebuilt", "anima_turbo"}
    assert all(j["seed"] == 7725 and j["retry_budget"] == 0 for j in result["jobs"])
    disk = json.loads(path.read_text(encoding="utf-8"))
    assert disk["jobs"][0]["generation_status"] == "NOT_RUN"


def test_pixel_style_cannot_enter_family_plan(tmp_path):
    with pytest.raises(ValueError, match="Pixel style is HOLD"):
        afp.plan(ROOT, tmp_path / "bad.json", styles=("STYLE-005",))


def test_local_model_preflight_blocks_missing_turbo(tmp_path):
    models = tmp_path / "models"
    for relative in (
        "diffusion_models/anima-base-v1.0.safetensors",
        "text_encoders/qwen_3_06b_base.safetensors",
        "vae/qwen_image_vae.safetensors",
    ):
        path = models / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"x")
    state = afp.inspect(ROOT, models_root=models)
    assert state["status"] == "BLOCKED_MISSING_MODEL_FILES"
    assert state["missing"] == ["anima-turbo-v1.1.safetensors"]


def test_execute_needs_explicit_confirmation(tmp_path):
    with pytest.raises(ValueError, match="--confirm-generation"):
        afp.execute(ROOT, tmp_path / "none.json", tmp_path, tmp_path / "out", "user-authorized", False)
