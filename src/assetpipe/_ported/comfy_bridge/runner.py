from __future__ import annotations

import copy
import hashlib
import json
import logging
import math
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

from ..config import PipelineConfig
from ..errors import ConfigurationError, ExternalServiceError
from .client import ComfyClient
from .workflow_loader import Workflow, load_workflow

logger = logging.getLogger(__name__)


def patch_workflow(
    workflow: Workflow,
    *,
    prompt: str,
    seed: int,
    negative_prompt: str = "",
    input_image: str | None = None,
    filename_prefix: str | None = None,
    lora_strength: float | None = None,
    workflow_inputs: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    graph = copy.deepcopy(workflow.api_prompt)
    values: dict[str, Any] = {
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "seed": seed,
        "input_image": input_image,
        "filename_prefix": filename_prefix,
        "lora_strength": lora_strength,
    }
    override_names = set(workflow_inputs or {})
    values.update(workflow_inputs or {})
    for name, value in values.items():
        binding = workflow.bindings.get(name)
        if value is None:
            if binding is not None and binding.get("required"):
                raise ConfigurationError(f"Workflow '{workflow.name}' requires a value for '{name}'.")
            continue
        if name in {"lora_strength", "cfg"} and not math.isfinite(float(value)):
            raise ConfigurationError(f"Workflow input '{name}' must be a finite number.")
        if name in {"width", "height", "steps"} and int(value) <= 0:
            raise ConfigurationError(f"Workflow input '{name}' must be greater than zero.")
        if binding is None:
            if name in {"prompt", "seed"}:
                raise ConfigurationError(f"Workflow '{workflow.name}' is missing its required '{name}' binding.")
            if name == "lora_strength":
                raise ConfigurationError(f"Workflow '{workflow.name}' does not declare a 'lora_strength' binding.")
            if name == "input_image":
                raise ConfigurationError(
                    f"Workflow '{workflow.name}' does not accept an input image; choose one that declares input_image."
                )
            if name in override_names:
                raise ConfigurationError(f"Workflow '{workflow.name}' does not declare a '{name}' binding.")
            continue
        graph[binding["node"]]["inputs"][binding["input"]] = value
    for name, binding in workflow.bindings.items():
        if binding.get("required") and name not in values:
            raise ConfigurationError(f"Workflow '{workflow.name}' requires a value for '{name}'.")
    return graph


def _write_json(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def _setting(config: PipelineConfig, key: str, default: Any) -> Any:
    return config.section("comfyui").get(key, default)


def run_workflow(
    config: PipelineConfig,
    *,
    workflow_name: str,
    prompt: str,
    seed: int | None = None,
    negative_prompt: str = "",
    input_image: Path | None = None,
    output_dir: Path | None = None,
    filename_prefix: str | None = None,
    lora_strength: float | None = None,
    workflow_inputs: Mapping[str, Any] | None = None,
) -> list[Path]:
    if not prompt.strip():
        raise ConfigurationError("Prompt must not be empty.")
    chosen_seed = secrets.randbits(32) if seed is None else seed
    if chosen_seed < 0 or chosen_seed > 18_446_744_073_709_551_615:
        raise ConfigurationError("Seed must be an unsigned 64-bit integer.")

    workflow = load_workflow(workflow_name, config.root / "config" / "workflows")
    client = ComfyClient(
        str(_setting(config, "base_url", "http://127.0.0.1:8188")),
        request_timeout=float(_setting(config, "request_timeout_seconds", 30)),
        execution_timeout=float(_setting(config, "execution_timeout_seconds", 1800)),
        poll_interval=float(_setting(config, "poll_interval_seconds", 1)),
    )
    stats = client.check_connection()
    comfy_version = stats.get("system", {}).get("comfyui_version")
    logger.info("Connected to ComfyUI%s.", f" {comfy_version}" if comfy_version else "")

    uploaded_image = client.upload_image(input_image) if input_image else None
    api_prompt = patch_workflow(
        workflow,
        prompt=prompt,
        seed=chosen_seed,
        negative_prompt=negative_prompt,
        input_image=uploaded_image,
        filename_prefix=filename_prefix or f"pixelpipe/{workflow_name}",
        lora_strength=lora_strength,
        workflow_inputs=workflow_inputs,
    )
    client_id = str(uuid4())
    prompt_id = client.queue_prompt(api_prompt, client_id)

    output_dir = output_dir or (config.path_for("workspace", "intermediate") / f"comfy_{prompt_id}")
    output_dir = Path(output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=False)
    metadata: dict[str, Any] = {
        "status": "RUNNING",
        "workflow": workflow.name,
        "workflow_path": str(workflow.path),
        "workflow_sha256": workflow.sha256,
        "workflow_version": workflow.version,
        "models": workflow.models or {},
        "generation_parameters": {
            **(workflow.defaults or {}),
            **{name: value for name, value in (workflow_inputs or {}).items() if value is not None},
            "seed": chosen_seed,
            "lora_strength": lora_strength,
        },
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "seed": chosen_seed,
        "lora_strength": lora_strength,
        "prompt_id": prompt_id,
        "client_id": client_id,
        "comfyui_base_url": client.base_url,
        "comfyui_version": comfy_version,
        "input_image": str(input_image.resolve()) if input_image else None,
        "input_image_sha256": hashlib.sha256(input_image.read_bytes()).hexdigest() if input_image else None,
        "uploaded_input_image": uploaded_image,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "artifacts": [],
    }
    _write_json(output_dir / "generation.json", metadata)
    (output_dir / "workflow.json").write_text(
        json.dumps(api_prompt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    try:
        image_outputs = client.wait_for_outputs(prompt_id, workflow.output_nodes)
        saved_paths: list[Path] = []
        for index, image_output in enumerate(image_outputs, start=1):
            server_name = Path(image_output["filename"]).name
            suffix = Path(server_name).suffix or ".png"
            destination = output_dir / f"{index:03d}_{Path(server_name).stem}{suffix}"
            if suffix.lower() == ".png":
                client.download_image(image_output, destination)
            else:
                client.download_asset(image_output, destination)
            saved_paths.append(destination)
        metadata["status"] = "COMPLETED"
        metadata["artifacts"] = [str(path) for path in saved_paths]
        metadata["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
        _write_json(output_dir / "generation.json", metadata)
        return saved_paths
    except ExternalServiceError as exc:
        metadata["status"] = "FAILED"
        metadata["error"] = str(exc)
        metadata["failed_at_utc"] = datetime.now(timezone.utc).isoformat()
        _write_json(output_dir / "generation.json", metadata)
        raise
