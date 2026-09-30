import json
from pathlib import Path

import pytest

from assetpipe._ported.errors import ConfigurationError
from assetpipe._ported.comfy_bridge.runner import patch_workflow
from assetpipe._ported.comfy_bridge.workflow_loader import Workflow, load_workflow


def test_concept_workflow_loads_and_patches_prompt_seed_and_negative_prompt() -> None:
    root = Path(__file__).resolve().parents[1]
    workflow = load_workflow("concept_character", root / "config" / "workflows")
    patched = patch_workflow(
        workflow,
        prompt="test character",
        negative_prompt="blurry",
        seed=123,
        filename_prefix="pixelpipe/test",
    )
    assert patched["5"]["inputs"]["prompt"] == "test character"
    assert patched["5"]["inputs"]["negative_prompt"] == "blurry"
    assert patched["6"]["inputs"]["seed"] == 123
    assert patched["8"]["inputs"]["filename_prefix"] == "pixelpipe/test"
    assert workflow.api_prompt["6"]["inputs"]["seed"] == 0


def test_mushroom_courier_production_workflow_is_vae_only_and_keeps_pixel_prompt() -> None:
    root = Path(__file__).resolve().parents[1]
    workflow = load_workflow("anima_mushroom_courier_production", root / "config" / "workflows")
    node_types = {node["class_type"] for node in workflow.api_prompt.values()}
    assert "UNETLoader" in node_types
    assert "VAELoader" in node_types
    assert "LoraLoaderModelOnly" not in node_types
    assert workflow.api_prompt["3"]["inputs"]["vae_name"] == "pixelateX4VAEForAnima_animaV10.safetensors"
    assert workflow.api_prompt["5"]["inputs"]["text"].startswith("pixel art, chibi, white background, simple background")


def test_deno_ref2va_workflow_uses_acc_lora_and_uploaded_reference() -> None:
    root = Path(__file__).resolve().parents[1]
    workflow = load_workflow("deno_minimax_h3_r2v_8step", root / "config" / "workflows")
    patched = patch_workflow(
        workflow,
        prompt="<Picture 1> walks in place",
        seed=123,
        input_image="uploaded_master.png",
        filename_prefix="pixelpipe/walk",
    )
    assert patched["127"]["inputs"]["unet_name"].startswith("minimax_h3_ref2va_")
    assert patched["183"]["inputs"]["acc_lora"] == "MiniMax-H3-Ref2VA-Acc-8Step.safetensors"
    assert patched["185"]["inputs"]["steps"] == 8
    assert patched["185"]["inputs"]["model"] == ["190", 0]
    assert patched["190"]["inputs"]["model"] == ["183", 0]
    assert patched["190"]["inputs"]["sage_attention"] == "auto"
    assert patched["142"]["inputs"]["image_paths"] == "uploaded_master.png"
    assert patched["141"]["inputs"]["prompt"] == "<Picture 1> walks in place"
    assert patched["129"]["inputs"]["noise_seed"] == 123
    assert patched["144"]["inputs"]["filename_prefix"] == "pixelpipe/walk"


def test_missing_prompt_binding_is_rejected() -> None:
    workflow = Workflow(
        name="invalid",
        path=Path("invalid.json"),
        api_prompt={"1": {"inputs": {"text": ""}}},
        bindings={},
        output_nodes=(),
        sha256="",
    )
    with pytest.raises(ConfigurationError, match="required 'prompt'"):
        patch_workflow(workflow, prompt="test", seed=7)


def test_image_input_is_patched_into_bound_workflow() -> None:
    workflow = Workflow(
        name="image_workflow",
        path=Path("image_workflow.json"),
        api_prompt={"1": {"inputs": {"text": ""}}, "2": {"inputs": {"image": ""}}},
        bindings={
            "prompt": {"node": "1", "input": "text"},
            "seed": {"node": "1", "input": "seed"},
            "input_image": {"node": "2", "input": "image"},
        },
        output_nodes=(),
        sha256="",
    )
    workflow.api_prompt["1"]["inputs"]["seed"] = 0
    patched = patch_workflow(workflow, prompt="reference character", seed=42, input_image="upload.png")
    assert patched["2"]["inputs"]["image"] == "upload.png"


def test_bad_workflow_json_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "bad.json").write_text(json.dumps({"api_prompt": {}}), encoding="utf-8")
    with pytest.raises(ConfigurationError, match="non-empty"):
        load_workflow("bad", tmp_path)
