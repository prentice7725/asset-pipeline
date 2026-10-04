"""Read-only, fail-closed model/style research inventory.

This module does NOT probe a provider, generate an asset, assign quality scores,
promote a style, or change production routing. Historical report references are
not independently verified output files.
"""
from __future__ import annotations

from collections import Counter
import hashlib
from pathlib import Path

import yaml


class KnowledgeError(ValueError):
    """Malformed research evidence or a broken registry cross-reference."""


MODEL_STATES = {"REGISTERED", "EXPERIMENTAL", "RESEARCH_ONLY"}
EVIDENCE_LEVELS = {"REPOSITORY_REPORT"}
QA_STATES = {"PASS_REPORTED", "FAIL_REPORTED", "PARTIAL_REPORTED", "NOT_VERIFIED"}
REVIEW_STATES = {"PASS_REPORTED", "FAIL_REPORTED", "NOT_REVIEWED"}
STYLE_STATES = {"APPROVED", "TESTED", "UNTESTED", "REJECTED"}


def _read(root: Path, relative: str) -> dict:
    path = (root / relative).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise KnowledgeError(f"Missing or unsafe knowledge input: {relative}")
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise KnowledgeError(f"Invalid YAML: {relative}: {exc}") from exc
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise KnowledgeError(f"Invalid schema version or root mapping: {relative}")
    return value


def _local_report(root: Path, name: str) -> None:
    if not isinstance(name, str) or not name.startswith("docs/"):
        raise KnowledgeError("Evidence report must be a tracked docs/ path")
    path = (root / name).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise KnowledgeError(f"Missing evidence report: {name}")


def _validate_models(models, workflows):
    if not isinstance(models, dict) or not models:
        raise KnowledgeError("model_catalog.models must be a nonempty mapping")
    owners = {}
    for model_id, model in sorted(models.items()):
        if not isinstance(model, dict):
            raise KnowledgeError(f"Malformed model entry: {model_id}")
        if model.get("status") not in MODEL_STATES or model.get("art_quality") != "UNKNOWN":
            raise KnowledgeError(f"Model must be explicitly unranked until verified: {model_id}")
        if model.get("license_review") != "REQUIRED":
            raise KnowledgeError(f"Commercial suitability may not be presumed: {model_id}")
        if model.get("local_installation") not in {"UNKNOWN", "NOT_PROBED_THIS_SESSION"}:
            raise KnowledgeError(f"Remote catalog cannot assert local installation: {model_id}")
        if model.get("source_kind") not in {"MODEL_AUTHOR", "COMMUNITY_AUTHOR", "LOCAL_CONFIG"}:
            raise KnowledgeError(f"Unclassified claim provenance: {model_id}")
        if not isinstance(model.get("source"), str) or not model["source"].startswith("https://"):
            raise KnowledgeError(f"Model source must be HTTPS: {model_id}")
        if not isinstance(model.get("author_claims"), list) or any(
            not isinstance(c, str) or not c.strip() for c in model["author_claims"]
        ):
            raise KnowledgeError(f"Author claims must be a text list: {model_id}")
        if not isinstance(model.get("workflows"), list):
            raise KnowledgeError(f"Invalid workflow list: {model_id}")
        if model["status"] == "RESEARCH_ONLY" and model["workflows"]:
            raise KnowledgeError(f"Research-only model cannot claim production routing: {model_id}")
        if model["status"] != "RESEARCH_ONLY" and not model["workflows"]:
            raise KnowledgeError(f"Registered model has no workflow: {model_id}")
        for workflow_id in model["workflows"]:
            if workflow_id not in workflows or workflow_id in owners:
                raise KnowledgeError(f"Unknown/duplicate workflow mapping: {workflow_id}")
            owners[workflow_id] = model_id
    unknown = sorted(set(workflows) - set(owners))
    if unknown:
        raise KnowledgeError(f"Unmapped live registry workflows: {unknown}")
    return owners


def _validate_evidence(root, records, workflows, models, styles):
    if not isinstance(records, dict):
        raise KnowledgeError("experiment_evidence.evidence must be a mapping")
    for evidence_id, item in sorted(records.items()):
        if not isinstance(item, dict):
            raise KnowledgeError(f"Malformed evidence: {evidence_id}")
        if item.get("source_level") not in EVIDENCE_LEVELS:
            raise KnowledgeError(f"Unverified evidence origin: {evidence_id}")
        if item.get("originals_reviewed_here") is not False:
            raise KnowledgeError(f"Repository summary cannot certify original images: {evidence_id}")
        if item.get("project_approval") is not False or item.get("generalization") != "NONE":
            raise KnowledgeError(f"Historical report cannot approve or generalize: {evidence_id}")
        if item.get("technical_qa") not in QA_STATES or item.get("semantic_review") not in REVIEW_STATES or item.get("artistic_review") not in REVIEW_STATES:
            raise KnowledgeError(f"Evidence stages must be explicitly known: {evidence_id}")
        if item.get("artistic_review") != "NOT_REVIEWED":
            raise KnowledgeError(f"No audited image-level art review in this inventory: {evidence_id}")
        if not isinstance(item.get("workflows"), list) or any(w not in workflows for w in item["workflows"]):
            raise KnowledgeError(f"Unknown evidence workflow: {evidence_id}")
        if item.get("model_id") is not None and item["model_id"] not in models:
            raise KnowledgeError(f"Unknown evidence model: {evidence_id}")
        if item.get("style_id") is not None and item["style_id"] not in styles:
            raise KnowledgeError(f"Unknown evidence style: {evidence_id}")
        count = item.get("generation_requests")
        if count is not None and (type(count) is not int or count < 0):
            raise KnowledgeError(f"Generation count must be measured or null: {evidence_id}")
        if not isinstance(item.get("subject_scope"), str) or not item["subject_scope"].strip():
            raise KnowledgeError(f"Evidence must have a bounded subject scope: {evidence_id}")
        _local_report(root, item.get("report"))


def _read_research_recipes(root):
    summary = {}
    for family in ("anima", "krea2", "pixel"):
        path = f"config/styles/recipes/{family}.yaml"
        recipes = _read(root, path).get("recipes")
        if not isinstance(recipes, dict):
            raise KnowledgeError(f"Missing mined recipe mapping: {path}")
        summary[family] = {
            "count": len(recipes),
            "offline_only": sum(1 for recipe in recipes.values() if recipe.get("offline_only") is True),
            "production_ready": 0,
        }
        # A research recipe's NORMALIZED state is not an audited production approval.
        # This reporter intentionally cannot elevate it based on any metadata.
    return summary


def build_snapshot(repository_root: str | Path) -> dict:
    """Validate and join checked-in inventories without loading or running a generator."""
    root = Path(repository_root).resolve()
    registry = _read(root, "config/workflow_registry.yaml").get("workflows")
    profiles = _read(root, "config/model_profiles.yaml").get("profiles")
    catalog = _read(root, "config/styles/catalog.yaml").get("styles")
    recipes = _read(root, "config/styles/model_recipes.yaml").get("recipes")
    models = _read(root, "config/knowledge/model_catalog.yaml").get("models")
    evidence = _read(root, "config/knowledge/experiment_evidence.yaml").get("evidence")
    if any(not isinstance(part, dict) for part in (registry, profiles, catalog, recipes)):
        raise KnowledgeError("Registry, profiles, styles, and recipes must be mappings")
    owners = _validate_models(models, registry)
    _validate_evidence(root, evidence, registry, models, catalog)
    results = {}
    for style_id, style in sorted(catalog.items()):
        if not isinstance(style, dict) or style.get("status") not in STYLE_STATES:
            raise KnowledgeError(f"Unknown style status: {style_id}")
        available = recipes.get(style_id, {})
        if not isinstance(available, dict):
            raise KnowledgeError(f"Malformed style recipe group: {style_id}")
        entries = {}
        for workflow_id, recipe in sorted(available.items()):
            if workflow_id not in registry or not isinstance(recipe, dict):
                raise KnowledgeError(f"Unknown workflow in recipe: {style_id}/{workflow_id}")
            if recipe.get("status") not in STYLE_STATES:
                raise KnowledgeError(f"Unrecognized recipe status: {style_id}/{workflow_id}")
            entries[workflow_id] = {
                "model_id": owners[workflow_id], "state": recipe["status"],
                "has_stated_evidence": bool(recipe.get("evidence")),
                "art_quality": "UNKNOWN", "project_approved": False,
            }
        descriptors = {}
        for field in ("expression", "colors", "linework", "shading", "texture"):
            value = style.get(field)
            if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
                raise KnowledgeError(f"Invalid visual style descriptors: {style_id}/{field}")
            descriptors[field] = value
        sources = style.get("sources")
        if not isinstance(sources, list):
            raise KnowledgeError(f"Unattributed visual style: {style_id}")
        results[style_id] = {
            "status": style["status"], "version": style.get("version"),
            "visual_grammar": descriptors,
            "required_capabilities": style.get("required_capabilities", []),
            "forbidden_elements": style.get("forbidden_elements", []),
            "source_claims_not_quality_evidence": sources,
            "recipes": entries, "art_quality": "UNKNOWN",
        }
    bad_styles = sorted(set(recipes) - set(catalog))
    if bad_styles:
        raise KnowledgeError(f"Unrecognized style IDs in recipes: {bad_styles}")
    # JSON graphs can exist without a registry entry. Surface, never route them.
    declared_graphs = set()
    for workflow_id, workflow in registry.items():
        if workflow.get("engine", "comfyui") != "comfyui":
            continue
        graph = workflow.get("workflow_file")
        if not isinstance(graph, str) or not graph.startswith("config/workflows/"):
            raise KnowledgeError(f"ComfyUI workflow graph path missing: {workflow_id}")
        graph_path = (root / graph).resolve()
        if not graph_path.is_relative_to((root / "config/workflows").resolve()) or not graph_path.is_file():
            raise KnowledgeError(f"ComfyUI workflow graph missing or unsafe: {workflow_id}")
        declared_graphs.add(graph_path.relative_to(root).as_posix())
    graphs_on_disk = {file.resolve().relative_to(root).as_posix()
                      for file in (root / "config/workflows").glob("*.json") if file.is_file()}
    unregistered_graphs = sorted(graphs_on_disk - declared_graphs)
    workflow_info = {}
    for workflow_id, wf in sorted(registry.items()):
        profile = wf.get("model_profile")
        if profile and profile not in profiles:
            raise KnowledgeError(f"Workflow uses unknown prompt profile: {workflow_id}")
        if not isinstance(wf.get("capabilities"), dict):
            raise KnowledgeError(f"Missing workflow capabilities: {workflow_id}")
        adapter = profiles.get(profile, {}) if profile else {}
        workflow_info[workflow_id] = {
            "model_id": owners[workflow_id], "registry_state": wf.get("status"),
            "output_class": wf.get("output_class"), "prompt_profile": profile,
            "prompt_adapter": adapter.get("prompt_adapter"),
            "profile_positive_prefix": adapter.get("positive_prefix", []),
            "intended_tags_not_benchmarks": wf.get("tags", []),
            "declared_models": wf.get("models", {}),
            "declared_presets": wf.get("presets", {}),
            "declared_capabilities": wf["capabilities"],
            "engine": wf.get("engine", "comfyui"),
            "workflow_file": wf.get("workflow_file"),
            "local_runtime_verified_this_session": False,
            "art_quality": "UNKNOWN",
            "not_a_quality_ranking": True,
        }
    evidence_summary = {
        k: {"source_level": v["source_level"], "report": v["report"],
            "subject_scope": v["subject_scope"], "workflow_ids": v["workflows"],
            "model_id": v.get("model_id"), "style_id": v.get("style_id"),
            "generation_requests": v.get("generation_requests"),
            "technical_qa": v["technical_qa"], "semantic_review": v["semantic_review"],
            "artistic_review": v["artistic_review"], "raw_artifacts_verified": False,
            "project_approved": False, "can_rank_models": False}
        for k, v in sorted(evidence.items())
    }
    counts = Counter(recipe["state"] for entry in results.values() for recipe in entry["recipes"].values())
    return {
        "schema_version": 1, "research_state": "INVENTORY_ONLY",
        "authority": "REPOSITORY_METADATA_AND_REPORTS_NOT_LOCAL_MEDIA",
        "generation_requests_made_by_this_command": 0,
        "side_effects": "NONE", "ranked_models": [], "approved_recommendations": [],
        "golden_recipes_approved_by_this_command": 0,
        "counts": {"workflows": len(registry), "model_variants": len(models),
                   "model_profiles": len(profiles), "styles": len(catalog),
                   "runtime_recipes": sum(counts.values()), "recipe_states": dict(counts),
                   "historical_report_records": len(evidence)},
        "models": {
            key: {"family": val["family"], "variant": val["variant"],
                  "source": val["source"], "source_kind": val["source_kind"],
                  "author_claims_not_benchmarks": val["author_claims"],
                  "workflow_ids": val["workflows"], "catalog_state": val["status"],
                  "local_installation": val["local_installation"],
                  "license_review": val["license_review"], "art_quality": "UNKNOWN"}
            for key, val in sorted(models.items())
        },
        "workflows": workflow_info, "styles": results,
        "historical_reports": evidence_summary,
        "offline_candidate_recipes": _read_research_recipes(root),
        "unregistered_workflow_graphs": unregistered_graphs,
        "limitations": [
            "No local ComfyUI/GPU inventory or model hash probe",
            "Historical reports are not original images and do not prove artwork quality",
            "No aesthetic ranking, no Golden approval, no production default changes",
            "No installed LoRA/VAE/version or commercial rights verification",
        ],
    }


def inspect(snapshot: dict, model_id: str | None = None, style_id: str | None = None) -> dict:
    """Model/style lookup with clear provenance, not a route or recommendation."""
    if model_id is not None and model_id not in snapshot["models"]:
        raise KnowledgeError(f"Unknown model variant: {model_id}")
    if style_id is not None and style_id not in snapshot["styles"]:
        raise KnowledgeError(f"Unknown style: {style_id}")
    if model_id is None and style_id is None:
        return snapshot
    workflows = set(snapshot["models"][model_id]["workflow_ids"]) if model_id else None
    result = {
        "research_state": snapshot["research_state"],
        "model": {model_id: snapshot["models"][model_id]} if model_id else {},
        "declared_workflows": {
            workflow_id: snapshot["workflows"][workflow_id]
            for workflow_id in (snapshot["models"][model_id]["workflow_ids"] if model_id else [])
        },
        "style": {style_id: snapshot["styles"][style_id]} if style_id else {},
        "relevant_reports": {},
        "art_quality": "UNKNOWN", "approved_recommendations": [],
        "generation_requests_made_by_this_command": 0,
    }
    for evid, item in snapshot["historical_reports"].items():
        model_link = bool(model_id and (item.get("model_id") == model_id or workflows.intersection(item["workflow_ids"])))
        style_link = bool(style_id and item["style_id"] == style_id)
        if (model_id is not None and style_id is not None and model_link and style_link
                or model_id is not None and style_id is None and model_link
                or style_id is not None and model_id is None and style_link):
            result["relevant_reports"][evid] = item
    return result


def scan_expected_weights(repository_root: str | Path, comfy_models_root: str | Path,
                          hash_files: bool = False, discover_unregistered: bool = False) -> dict:
    """Read-only file-presence inventory. No ComfyUI calls and no new downloads.

    comfy_models_root MUST point to the actual ComfyUI 'models' directory.
    Presence and hashing cannot validate whether the model executes correctly.
    """
    project = Path(repository_root).resolve()
    models_root = Path(comfy_models_root).resolve()
    if not models_root.is_dir():
        raise KnowledgeError(f"Configured models root does not exist: {models_root}")
    registry = _read(project, "config/workflow_registry.yaml")["workflows"]
    expected: dict[tuple[str, str], set[str]] = {}
    for workflow_id, workflow in registry.items():
        for folder, filenames in (workflow.get("models") or {}).items():
            if not isinstance(folder, str) or folder not in {
                "checkpoints", "diffusion_models", "text_encoders", "vae", "loras"
            } or not isinstance(filenames, list):
                raise KnowledgeError(f"Unsafe model inventory declarations: {workflow_id}")
            for filename in filenames:
                if not isinstance(filename, str) or not filename or filename in {".", ".."} or (
                    Path(filename).name != filename
                ):
                    raise KnowledgeError(f"Unsafe model filename in workflow {workflow_id}")
                expected.setdefault((folder, filename), set()).add(workflow_id)
        for lora in workflow.get("loras", []):
            if not isinstance(lora, dict) or not isinstance(lora.get("file"), str):
                raise KnowledgeError(f"Invalid LoRA metadata: {workflow_id}")
            filename = lora["file"]
            if Path(filename).name != filename or not filename:
                raise KnowledgeError(f"Unsafe LoRA path: {workflow_id}")
            expected.setdefault(("loras", filename), set()).add(workflow_id)
    results = []
    for (folder, filename), owners in sorted(expected.items()):
        path = models_root / folder / filename
        resolved = path.resolve()
        if not resolved.is_relative_to(models_root):
            raise KnowledgeError(f"Dependency path escapes model root: {folder}/{filename}")
        exists = resolved.is_file()
        entry = {
            "folder": folder, "filename": filename,
            "workflow_ids": sorted(owners), "presence": "PRESENT" if exists else "MISSING",
            "byte_size": resolved.stat().st_size if exists else None,
            "sha256": None, "hash_status": "NOT_REQUESTED" if not hash_files else "MISSING",
            "model_identity_verified": False, "license_cleared": False,
            "generation_validated": False,
        }
        if exists and hash_files:
            digest = hashlib.sha256()
            with resolved.open("rb") as stream:
                for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
                    digest.update(chunk)
            entry["sha256"] = digest.hexdigest()
            entry["hash_status"] = "LOCAL_BYTES_SHA256"
        results.append(entry)
    unregistered = []
    if discover_unregistered:
        # Names only. Do not read or hash unknown model files.
        discovered_count = 0
        for folder in ("checkpoints", "diffusion_models", "text_encoders", "vae", "loras"):
            base = models_root / folder
            if not base.is_dir():
                continue
            for path in base.rglob("*"):
                if not path.is_file() or path.suffix.lower() not in {
                    ".safetensors", ".ckpt", ".pt", ".pth", ".gguf"
                }:
                    continue
                discovered_count += 1
                if discovered_count > 5000:
                    raise KnowledgeError("Unregistered scan exceeded 5000 model-like files")
                resolved = path.resolve()
                if not resolved.is_relative_to(models_root):
                    raise KnowledgeError("Unregistered candidate path escapes model root")
                rel = path.relative_to(base).as_posix()
                if (folder, rel) not in expected:
                    unregistered.append({
                        "folder": folder, "relative_filename": rel,
                        "registry_state": "UNREGISTERED",
                        "runtime_available": False, "hash_status": "NOT_REQUESTED",
                    })
    return {
        "inventory_state": "LOCAL_FILENAME_INVENTORY" if not hash_files else "LOCAL_HASHED_BYTES",
        "scope": "DECLARED_WORKFLOW_DEPENDENCIES_ONLY",
        "local_models_root": str(models_root),
        "expected": len(results),
        "present": sum(1 for e in results if e["presence"] == "PRESENT"),
        "missing": sum(1 for e in results if e["presence"] == "MISSING"),
        "files": results,
        "unregistered_candidates": sorted(unregistered, key=lambda x: (x["folder"], x["relative_filename"])),
        "unregistered_count": len(unregistered),
        "generation_requests": 0,
        "installation_compatibility": "NOT_TESTED",
        "commercial_rights": "NOT_REVIEWED",
        "art_quality": "UNKNOWN",
        "side_effects": "NONE",
    }
