from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .errors import ConfigurationError


@dataclass(frozen=True)
class PipelineConfig:
    path: Path
    values: dict[str, Any]

    @property
    def root(self) -> Path:
        return self.path.parent.parent

    def section(self, name: str) -> dict[str, Any]:
        value = self.values.get(name, {})
        if not isinstance(value, dict):
            raise ConfigurationError(f"Configuration section '{name}' must be a mapping.")
        return value

    def path_for(self, section: str, key: str) -> Path:
        value = self.section(section).get(key)
        if not isinstance(value, str) or not value.strip():
            raise ConfigurationError(f"Missing path setting '{section}.{key}'.")
        path = Path(value)
        return path if path.is_absolute() else self.root / path


def load_config(path: str | Path | None = None) -> PipelineConfig:
    config_path = Path(path or "config/pipeline.yaml").expanduser().resolve()
    try:
        with config_path.open("r", encoding="utf-8") as stream:
            values = yaml.safe_load(stream)
    except OSError as exc:
        raise ConfigurationError(f"Cannot read config '{config_path}': {exc}") from exc
    except yaml.YAMLError as exc:
        raise ConfigurationError(f"Invalid YAML in '{config_path}': {exc}") from exc
    if not isinstance(values, dict):
        raise ConfigurationError(f"Config '{config_path}' must contain a YAML mapping.")
    for name in ("comfyui", "workspace", "pixel"):
        section = values.get(name, {})
        if not isinstance(section, dict):
            raise ConfigurationError(f"Configuration section '{name}' must be a mapping.")
    return PipelineConfig(path=config_path, values=values)
