"""Contract tests for offline model knowledge: no model generation or approvals."""
import copy
import json
import shutil
from pathlib import Path

import pytest
import yaml

from assetpipe.cli import main
from assetpipe.knowledge import KnowledgeError, build_snapshot, inspect, scan_expected_weights

ROOT = Path(__file__).resolve().parents[2]
REQUIRED_FILES = (
    "config/workflow_registry.yaml",
    "config/workflows/krea2_pixel64_smoke_experimental.json",
    "config/workflows/krea2_pixel64_redraw_experimental.json",
    "config/workflows/concept_character.json",
    "config/workflows/anima_mushroom_courier_production.json",
    "config/workflows/anima_tomohi_api.json",
    "config/workflows/audio_stable_audio_3_medium.json",
    "config/workflows/baseline_anima_api.json",
    "config/workflows/deno_minimax_h3_r2v_8step.json",
    "config/workflows/krea2_turbo_api.json",
    "config/model_profiles.yaml",
    "config/styles/catalog.yaml",
    "config/styles/model_recipes.yaml",
    "config/styles/recipes/anima.yaml",
    "config/styles/recipes/krea2.yaml",
    "config/styles/recipes/pixel.yaml",
    "config/knowledge/model_catalog.yaml",
    "config/knowledge/experiment_evidence.yaml",
    "docs/m2/STATUS.json",
    "docs/style/M25_BLOCKER.md",
    "docs/style/PIXEL_ROOT_CAUSE_AUDIT_20261001.md",
    "docs/research/KREA2_PIXEL64_SMOKE_20261003.md",
    "docs/style/VISUAL_HIERARCHY.md",
)


@pytest.fixture
def replica(tmp_path):
    for name in REQUIRED_FILES:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, target)
    return tmp_path


def mutate(root, name, callback):
    path = root / name
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    callback(data)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def test_complete_mapping_and_counts():
    result = build_snapshot(ROOT)
    assert result["research_state"] == "INVENTORY_ONLY"
    assert result["counts"]["workflows"] == 9
    assert result["counts"]["model_variants"] == 10
    assert result["counts"]["model_profiles"] == 6
    assert result["counts"]["styles"] == 7
    assert result["counts"]["runtime_recipes"] == 15
    assert result["counts"]["recipe_states"] == {"TESTED": 2, "UNTESTED": 13}
    assert result["counts"]["historical_report_records"] == 6
    assert "config/workflows/krea2_pixel64_smoke_experimental.json" in result["unregistered_workflow_graphs"]
    assert result["styles"]["ink-storybook"]["visual_grammar"]["linework"] == ["fine ink contours"]
    assert result["workflows"]["anima_base"]["prompt_adapter"] == "anima"
    assert result["workflows"]["krea2_base"]["prompt_adapter"] == "krea2"
    assert result["workflows"]["anima_pixelate_x4_vae"]["profile_positive_prefix"] == ["pixel art", "chibi"]
    assert result["workflows"]["krea2_base"]["declared_presets"]["concept_art"]["steps"] == 8
    assert result["generation_requests_made_by_this_command"] == 0
    assert result["side_effects"] == "NONE"
    assert result["ranked_models"] == result["approved_recommendations"] == []


def test_every_model_and_style_explicitly_unranked():
    report = build_snapshot(ROOT)
    assert all(m["art_quality"] == "UNKNOWN" and m["license_review"] == "REQUIRED" for m in report["models"].values())
    assert all(w["art_quality"] == "UNKNOWN" and not w["local_runtime_verified_this_session"] for w in report["workflows"].values())
    assert all(s["art_quality"] == "UNKNOWN" for s in report["styles"].values())
    assert all(x["artistic_review"] == "NOT_REVIEWED" and not x["raw_artifacts_verified"] and not x["project_approved"] for x in report["historical_reports"].values())
    assert report["historical_reports"]["m25-anima-pixel-fail"]["technical_qa"] == "FAIL_REPORTED"
    assert report["historical_reports"]["krea2-pixel64-smoke"]["technical_qa"] == "PASS_REPORTED"
    assert report["models"]["anima-turbo"]["workflow_ids"] == []
    assert report["models"]["krea2-raw"]["catalog_state"] == "RESEARCH_ONLY"


def test_model_and_style_lookup_never_ranks():
    snapshot = build_snapshot(ROOT)
    result = inspect(snapshot, "krea2-turbo", "graphic-risograph")
    assert result["art_quality"] == "UNKNOWN"
    assert result["approved_recommendations"] == []
    assert "m2-graphic-risograph-pair" in result["relevant_reports"]
    assert "m25-anima-pixel-fail" not in result["relevant_reports"]
    with pytest.raises(KnowledgeError, match="Unknown model"):
        inspect(snapshot, "invented-model")
    with pytest.raises(KnowledgeError, match="Unknown style"):
        inspect(snapshot, style_id="nonexistent")


def test_no_implicit_approval_on_forged_evidence(replica):
    def forge(data):
        data["evidence"]["m25-anima-pixel-fail"]["project_approval"] = True
    mutate(replica, "config/knowledge/experiment_evidence.yaml", forge)
    with pytest.raises(KnowledgeError, match="cannot approve"):
        build_snapshot(replica)


def test_no_missing_unregistered_workflow(replica):
    def alter(data):
        data["models"]["anima-base"]["workflows"] = ["anima_base"]
    mutate(replica, "config/knowledge/model_catalog.yaml", alter)
    with pytest.raises(KnowledgeError, match="Unmapped live registry"):
        build_snapshot(replica)


def test_unverified_technical_report_cannot_fake_art_review(replica):
    def alter(data):
        data["evidence"]["krea2-pixel64-smoke"]["artistic_review"] = "PASS_REPORTED"
    mutate(replica, "config/knowledge/experiment_evidence.yaml", alter)
    with pytest.raises(KnowledgeError, match="image-level art review"):
        build_snapshot(replica)


def test_repository_report_must_exist_and_stay_inside_repo(replica):
    def alter(data):
        data["evidence"]["krea2-pixel64-smoke"]["report"] = "../private/report.json"
    mutate(replica, "config/knowledge/experiment_evidence.yaml", alter)
    with pytest.raises(KnowledgeError, match="tracked docs"):
        build_snapshot(replica)


def test_unregistered_unknown_style_in_recipe(replica):
    def alter(data):
        data["recipes"]["fake_not_reviewed"] = {}
    mutate(replica, "config/styles/model_recipes.yaml", alter)
    with pytest.raises(KnowledgeError, match="Unrecognized style IDs"):
        build_snapshot(replica)


def test_research_model_cannot_claim_active_routing(replica):
    def alter(data):
        data["models"]["anima-turbo"]["workflows"] = ["anima_base"]
    mutate(replica, "config/knowledge/model_catalog.yaml", alter)
    with pytest.raises(KnowledgeError, match="Research-only model"):
        build_snapshot(replica)


def test_cli_reads_without_generation_and_supports_queries(tmp_path, capsys):
    output = tmp_path / "knowledge.json"
    assert main(["--root", str(ROOT), "knowledge", "--model-id", "anima-base", "--output", str(output)]) == 0
    data = json.loads(output.read_text(encoding="utf-8"))
    assert "anima-base" in data["model"]
    assert data["declared_workflows"]["anima_base"]["declared_presets"]["character_portrait"]["steps"] == 24
    assert data["generation_requests_made_by_this_command"] == 0
    assert not data["approved_recommendations"]
    assert main(["--root", str(ROOT), "knowledge", "--style-id", "limited_palette_pixel"]) == 0
    assert "limited_palette_pixel" in capsys.readouterr().out
    assert main(["--root", str(ROOT), "knowledge", "--style-id", "missing_style"]) == 1
    assert "Unknown style" in capsys.readouterr().err


def test_declared_weight_scan_is_readonly_and_reports_missing(tmp_path):
    models_root = tmp_path / "models"
    sample = models_root / "diffusion_models" / "anima-base-v1.0.safetensors"
    sample.parent.mkdir(parents=True)
    sample.write_bytes(b"small fixture, not a model")
    report = scan_expected_weights(ROOT, models_root, hash_files=True)
    assert report["present"] >= 1 and report["missing"] >= 1
    record = next(x for x in report["files"] if x["filename"] == "anima-base-v1.0.safetensors")
    assert record["hash_status"] == "LOCAL_BYTES_SHA256"
    assert len(record["sha256"]) == 64
    assert record["model_identity_verified"] is False
    assert report["generation_requests"] == 0
    assert report["art_quality"] == "UNKNOWN"
    assert sample.read_bytes() == b"small fixture, not a model"


def test_missing_models_root_fails_closed(tmp_path):
    with pytest.raises(KnowledgeError, match="does not exist"):
        scan_expected_weights(ROOT, tmp_path / "not_existing")


def test_cli_rejects_hash_without_explicit_models_dir(capsys):
    assert main(["--root", str(ROOT), "knowledge", "--hash-models"]) == 1
    assert "--models-root" in capsys.readouterr().err


def test_unregistered_weights_are_discovered_but_not_routed(tmp_path):
    root = tmp_path / "models"
    unknown = root / "diffusion_models" / "new-but-unregistered.safetensors"
    unknown.parent.mkdir(parents=True)
    unknown.write_bytes(b"not a real model")
    report = scan_expected_weights(ROOT, root, discover_unregistered=True)
    assert report["unregistered_count"] == 1
    item = report["unregistered_candidates"][0]
    assert item["relative_filename"] == unknown.name
    assert item["runtime_available"] is False
    assert item["hash_status"] == "NOT_REQUESTED"
    assert report["generation_requests"] == 0
