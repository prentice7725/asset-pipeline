from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from ..errors import ConfigurationError

_WORKFLOW_ID = re.compile(r"^[A-Za-z0-9_-]+$")


@dataclass(frozen=True)
class Workflow:
    name: str
    path: Path
    api_prompt: dict[str, dict[str, Any]]
    bindings: dict[str, dict[str, Any]]
    output_nodes: tuple[str, ...]
    sha256: str
    version: str | None = None
    models: dict[str, Any] | None = None
    defaults: dict[str, Any] | None = None


def load_workflow(name: str, workflows_dir: Path) -> Workflow:
    if not _WORKFLOW_ID.fullmatch(name):
        raise ConfigurationError("Workflow names may contain only letters, numbers, '_' and '-'.")
    path = workflows_dir / f"{name}.json"
    if not path.is_file():
        adapter_path = workflows_dir / f"{name}_adapter.yaml"
        if adapter_path.is_file():
            try:
                adapter = yaml.safe_load(adapter_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
                raise ConfigurationError(f"Cannot read workflow adapter '{adapter_path}': {exc}") from exc
            workflow_file = adapter.get("workflow_file") if isinstance(adapter, dict) else None
            if not isinstance(workflow_file, str) or Path(workflow_file).name != workflow_file or not workflow_file.endswith(".json"):
                raise ConfigurationError(f"Workflow adapter '{adapter_path}' needs a local JSON 'workflow_file'.")
            path = workflows_dir / workflow_file
    try:
        raw = path.read_bytes()
        value = json.loads(raw)
    except OSError as exc:
        raise ConfigurationError(f"Cannot read workflow '{path}': {exc}") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ConfigurationError(f"Workflow '{path}' is not valid UTF-8 JSON: {exc}") from exc

    if not isinstance(value, dict):
        raise ConfigurationError("Workflow file must contain a JSON object.")
    api_prompt = value.get("api_prompt")
    bindings = value.get("bindings", {})
    output_nodes = value.get("output_nodes", [])
    if not isinstance(api_prompt, dict) or not api_prompt:
        raise ConfigurationError("Workflow must contain a non-empty 'api_prompt' node graph.")
    if not isinstance(bindings, dict) or not isinstance(output_nodes, list):
        raise ConfigurationError("Workflow 'bindings' must be an object and 'output_nodes' an array.")

    normalized_bindings: dict[str, dict[str, Any]] = {}
    for binding, target in bindings.items():
        if not isinstance(binding, str) or not isinstance(target, dict):
            raise ConfigurationError("Each workflow binding must map a name to a node/input object.")
        node_id, input_name = target.get("node"), target.get("input")
        if not isinstance(node_id, str) or not isinstance(input_name, str):
            raise ConfigurationError(f"Workflow binding '{binding}' needs string 'node' and 'input' values.")
        if node_id not in api_prompt:
            raise ConfigurationError(f"Workflow binding '{binding}' refers to missing node '{node_id}'.")
        inputs = api_prompt[node_id].get("inputs") if isinstance(api_prompt[node_id], dict) else None
        if not isinstance(inputs, dict) or input_name not in inputs:
            raise ConfigurationError(f"Workflow binding '{binding}' refers to missing input '{node_id}.{input_name}'.")
        required = target.get("required", False)
        if not isinstance(required, bool):
            raise ConfigurationError(f"Workflow binding '{binding}' field 'required' must be a boolean.")
        normalized_bindings[binding] = {"node": node_id, "input": input_name, "required": required}

    if not isinstance(output_nodes, list) or any(not isinstance(node_id, str) for node_id in output_nodes):
        raise ConfigurationError("Workflow 'output_nodes' must contain node id strings.")
    missing_outputs = [node_id for node_id in output_nodes if node_id not in api_prompt]
    if missing_outputs:
        raise ConfigurationError(f"Workflow refers to missing output node(s): {', '.join(missing_outputs)}.")
    if "prompt" not in normalized_bindings:
        raise ConfigurationError("Workflow must define a 'prompt' binding.")
    version = value.get("workflow_version")
    models = value.get("models", {})
    defaults = value.get("defaults", {})
    if version is not None and not isinstance(version, str):
        raise ConfigurationError("Workflow 'workflow_version' must be a string.")
    if not isinstance(models, dict) or not isinstance(defaults, dict):
        raise ConfigurationError("Workflow 'models' and 'defaults' must be objects.")
    return Workflow(
        name=name,
        path=path,
        api_prompt=copy.deepcopy(api_prompt),
        bindings=normalized_bindings,
        output_nodes=tuple(output_nodes),
        sha256=hashlib.sha256(raw).hexdigest(),
        version=version,
        models=copy.deepcopy(models),
        defaults=copy.deepcopy(defaults),
    )
