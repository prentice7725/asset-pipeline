"""Controlled Anima family baseline/pilot pipeline.

Builds the same synthetic NONPIXEL fixture from model-neutral style semantics,
compiles it through the configured Anima profile, and can execute a reserved
no-retry cohort on local ComfyUI.

Nothing here downloads weights or falls back to another workflow.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
STYLE_RESEARCH = ROOT / "config/style_menu/nonpixel_prompt_research_v0.yaml"
REGISTRY = ROOT / "config/workflow_registry.yaml"
MODEL_PROFILES = ROOT / "config/model_profiles.yaml"

WORKFLOWS = ("anima_base_rebuilt", "anima_turbo")
DEFAULT_STYLES = ("STYLE-001", "STYLE-004")
SEED = 7725
COHORT = "ANIMA_FAMILY_R2_20261005"
R1_EVIDENCE_COMMIT = "267529838ab989c58868277f1a850fb963468eb4"
EXPECTED = {
    "anima_base_rebuilt": {
        "profile": "anima-base-rebuilt",
        "checkpoint": "anima-base-v1.0.safetensors",
        "steps": 30,
        "cfg": 4.0,
        "sampler": "er_sde",
    },
    "anima_turbo": {
        "profile": "anima-turbo",
        "checkpoint": "anima-turbo-v1.1.safetensors",
        "steps": 10,
        "cfg": 1.0,
        "sampler": "euler",
    },
}
OFFICIAL_POSITIVE = ["masterpiece", "best quality", "score_7", "safe"]
OFFICIAL_NEGATIVE = [
    "worst quality", "low quality", "score_1", "score_2", "score_3",
    "artist name", "blurry", "jpeg artifacts", "chromatic aberration",
]


def _yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected YAML mapping: {path}")
    return value


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def inspect(root: Path = ROOT, models_root: Path | None = None, hash_models: bool = False) -> dict[str, Any]:
    root = Path(root).resolve()
    from assetpipe.registry import load_registry

    registry = load_registry(root)
    profiles = _yaml(root / "config/model_profiles.yaml")["profiles"]
    result: dict[str, Any] = {
        "status": "PIPELINE_CONFIG_VALID",
        "generation_requests": 0,
        "workflows": {},
        "model_files": {},
    }
    for workflow_id in WORKFLOWS:
        if workflow_id not in registry:
            raise ValueError(f"Missing Anima family workflow: {workflow_id}")
        workflow = registry[workflow_id]
        expected = EXPECTED[workflow_id]
        if workflow["output_class"] != "NONPIXEL_IMAGE":
            raise ValueError(f"{workflow_id} must stay NONPIXEL_IMAGE")
        if workflow["status"] != "EXPERIMENTAL" or workflow.get("selection") != "explicit_only":
            raise ValueError(f"{workflow_id} must remain explicit-only EXPERIMENTAL until reviewed")
        if workflow["model_profile"] != expected["profile"]:
            raise ValueError(f"{workflow_id} profile mismatch")
        profile = profiles[workflow["model_profile"]]
        if profile.get("prompt_adapter") != "anima_hybrid":
            raise ValueError(f"{workflow_id} must use anima_hybrid")
        if profile.get("positive_prefix") != OFFICIAL_POSITIVE:
            raise ValueError(f"{workflow_id} official positive prefix drift")
        if profile.get("negative_prefix") != OFFICIAL_NEGATIVE:
            raise ValueError(f"{workflow_id} official negative prefix drift")
        if workflow["models"].get("loras") != []:
            raise ValueError(f"{workflow_id} baseline may not apply LoRA")
        if workflow["models"]["diffusion_models"] != [expected["checkpoint"]]:
            raise ValueError(f"{workflow_id} checkpoint mismatch")
        if workflow["models"]["text_encoders"] != ["qwen_3_06b_base.safetensors"]:
            raise ValueError(f"{workflow_id} text encoder mismatch")
        if workflow["models"]["vae"] != ["qwen_image_vae.safetensors"]:
            raise ValueError(f"{workflow_id} VAE mismatch")
        preset = workflow["presets"]["pilot_b1_compatible"]
        for key in ("steps", "cfg", "sampler"):
            if preset[key] != expected[key]:
                raise ValueError(f"{workflow_id} {key} drift: {preset[key]} != {expected[key]}")
        if preset["width"] != 512 or preset["height"] != 768:
            raise ValueError(f"{workflow_id} pilot comparison resolution must be 512x768")
        result["workflows"][workflow_id] = {
            "profile": workflow["model_profile"],
            "workflow_hash": workflow["hash"],
            "checkpoint": expected["checkpoint"],
            "preset": dict(preset),
            "real_generation": workflow.get("validation", {}).get("real_generation", "NOT_RUN"),
        }

    if models_root is not None:
        models_root = Path(models_root).expanduser().resolve()
        if not models_root.is_dir():
            raise ValueError(f"ComfyUI models root does not exist: {models_root}")
        expected_paths = {
            "anima-base-v1.0.safetensors": models_root / "diffusion_models/anima-base-v1.0.safetensors",
            "anima-turbo-v1.1.safetensors": models_root / "diffusion_models/anima-turbo-v1.1.safetensors",
            "qwen_3_06b_base.safetensors": models_root / "text_encoders/qwen_3_06b_base.safetensors",
            "qwen_image_vae.safetensors": models_root / "vae/qwen_image_vae.safetensors",
        }
        missing = [name for name, path in expected_paths.items() if not path.is_file()]
        for name, path in expected_paths.items():
            if path.is_file():
                item = {"path": str(path), "bytes": path.stat().st_size, "present": True}
                if hash_models:
                    item["sha256"] = _sha(path)
                result["model_files"][name] = item
            else:
                result["model_files"][name] = {"path": str(path), "present": False}
        if missing:
            result["status"] = "BLOCKED_MISSING_MODEL_FILES"
            result["missing"] = missing
        else:
            result["local_model_preflight"] = "PASS"
    return result


def _fixture(style_id: str, style: dict[str, Any], workflow_id: str) -> dict[str, Any]:
    from assetpipe.brief import make, validate

    semantics = style.get("anima_base", {})
    # Style menu semantics may contain subject-shape cues (for example STYLE-004
    # historically contains "small body"). The controlled adult fixture locks body
    # identity/proportions, so such cues are not allowed to leak into the prompt.
    subject_mutation_tags = {"small body", "chibi", "super deformed", "child", "teen"}
    # Only model-facing visual semantics enter the prompt. Internal menu axis
    # labels such as CINEMATIC_STYLIZED/RED_CHARCOAL remain metadata and are not
    # treated as learned Anima tokens.
    descriptors = [
        tag for tag in semantics.get("positive_tags", [])
        if tag.casefold() not in subject_mutation_tags
    ]

    brief = make(
        asset_id=f"{style_id}_{workflow_id}_r2".replace("-", "_"),
        output_class="NONPIXEL_IMAGE",
        prompt="synthetic Anima family controlled fixture",
    )
    brief.pop("prompt", None)
    trait = "exactly one brass compass visibly held in the subject's anatomical left hand"
    brief["identity"] = {
        "canonical_traits": ["adult traveler", "short dark brown hair", "plain blue coat", trait],
        "visual_traits": [],
    }
    brief["constraints"].update({
        "resolution": [512, 768],
        "style": None,
        "silhouette": "complete head-to-toe human silhouette with both feet visible",
    })
    brief["workflow_preferences"] = {
        "id": workflow_id,
        "preset": "pilot_b1_compatible",
        "allow_experimental": True,
    }
    brief["source_notes"] = [{
        "classification": "DERIVED",
        "text": "Synthetic controlled fixture for model/prompt baseline comparison; not project canon.",
        "source": "anima-family-pipeline",
    }]
    brief["unspecified_elements"] = ["project identity", "project lore"]
    brief["prompt_spec"] = {
        "subject": "Exactly one adult traveler with short dark brown hair, wearing a plain blue coat.",
        "appearance": ["short dark brown hair", "plain blue coat", trait],
        "pose": "standing naturally in a front view",
        "composition": "complete full body centered in frame, head to toe, both feet visible, with clear ground margin below the footwear",
        "environment": "uncluttered background treatment consistent with the selected style direction, with no crowd",
        "lighting": "use the selected style lighting while keeping the face, coat, hands, and required equipment readable",
        "mood": "follow the selected style direction while keeping the subject legible",
        "style": list(dict.fromkeys(descriptors)),
        "constraints": [
            "single character",
            "do not crop the head or feet",
            "background detail remains subordinate to the traveler",
        ],
        "negative": [],
        "subject_integrity": {
            "class": "full_character",
            "identity_source": "synthetic controlled fixture",
            "whole_subject_required": True,
            "physically_connected_body": True,
            "mandatory_parts": ["head", "torso", "both arms", "both hands", "both legs", "both feet"],
            "camera_view": "front",
            "equipment": [{
                "source_trait": trait,
                "relationship": "carried",
                "visible_count": 1,
                "location": "left",
            }],
            "forbidden_substitutions": [],
        },
    }
    return validate(brief)


def plan(root: Path = ROOT, output: Path | None = None, styles: tuple[str, ...] = DEFAULT_STYLES,
         seed: int = SEED) -> dict[str, Any]:
    root = Path(root).resolve()
    state = inspect(root)
    research = _yaml(root / "config/style_menu/nonpixel_prompt_research_v0.yaml")["recipes"]
    from assetpipe.registry import load_registry
    from assetpipe.prompts import compile_prompt, workflow_values

    registry = load_registry(root)
    jobs = []
    for style_id in styles:
        if style_id == "STYLE-005":
            raise ValueError("Pixel style is HOLD and cannot enter Anima nonpixel cohort")
        if style_id not in research:
            raise ValueError(f"Unknown research style: {style_id}")
        for workflow_id in WORKFLOWS:
            brief = _fixture(style_id, research[style_id], workflow_id)
            compiled = compile_prompt(brief, registry[workflow_id], root)
            values = workflow_values(compiled, registry[workflow_id], brief)
            jobs.append({
                "job_id": f"{style_id}_{workflow_id}",
                "style_id": style_id,
                "workflow_id": workflow_id,
                "model_profile": registry[workflow_id]["model_profile"],
                "seed": seed,
                "brief": brief,
                "compiled_prompt": compiled,
                "workflow_inputs": values,
                "generation_status": "NOT_RUN",
                "retry_budget": 0,
                "golden_approval": False,
            })
    payload = {
        "schema_version": 1,
        "cohort": COHORT,
        "status": "PREPARED_NOT_EXECUTED",
        "purpose": "R2 pipeline correction: remove fixture/style conflicts and equipment-prompt duplication before comparing Base-rebuilt vs Turbo.",
        "supersedes_r1_evidence_commit": R1_EVIDENCE_COMMIT,
        "styles": list(styles),
        "workflows": list(WORKFLOWS),
        "seed": seed,
        "reserved_calls_required": len(jobs),
        "generation_requests": 0,
        "pixel_generation": 0,
        "lora_changes": 0,
        "vae_changes": 0,
        "jobs": jobs,
        "pipeline_check": state,
    }
    if output:
        output = Path(output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload


def execute(root: Path, plan_path: Path, models_root: Path, output_dir: Path,
            authorization_note: str, confirm_generation: bool) -> dict[str, Any]:
    if not confirm_generation:
        raise ValueError("Generation requires --confirm-generation")
    if not authorization_note.strip():
        raise ValueError("Generation requires a nonempty --authorization-note")
    root = Path(root).resolve()
    plan_data = json.loads(Path(plan_path).read_text(encoding="utf-8"))
    if plan_data.get("cohort") != COHORT:
        raise ValueError("Unexpected cohort plan")
    jobs = plan_data.get("jobs", [])
    if len(jobs) != 4 or plan_data.get("reserved_calls_required") != 4:
        raise ValueError("R2 is fixed to four no-retry calls")
    local = inspect(root, models_root=models_root, hash_models=True)
    if local["status"] != "PIPELINE_CONFIG_VALID" or local.get("local_model_preflight") != "PASS":
        raise ValueError("Local model preflight must PASS before any dispatch")

    from assetpipe.pipelines import create
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=False)
    ledger_path = output_dir / "reservation.json"
    ledger = {
        "cohort": plan_data["cohort"],
        "authorization_note": authorization_note,
        "reserved_calls": 4,
        "attempted_calls": 0,
        "completed_calls": 0,
        "failed_calls": 0,
        "retries_allowed": 0,
        "models_preflight": local,
    }
    ledger_path.write_text(json.dumps(ledger, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    results = []
    for job in jobs:
        # Re-validate all invariants immediately before each request.
        inspect(root)
        ledger["attempted_calls"] += 1
        ledger_path.write_text(json.dumps(ledger, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        run_dir = output_dir / "runs" / job["job_id"]
        try:
            manifest = create(job["brief"], root, output=run_dir, seed=job["seed"])
            ledger["completed_calls"] += 1
            results.append({"job_id": job["job_id"], "status": "COMPLETED", "manifest": str(manifest)})
        except Exception as exc:
            ledger["failed_calls"] += 1
            results.append({"job_id": job["job_id"], "status": "FAILED", "error": str(exc), "run_dir": str(run_dir)})
        finally:
            ledger_path.write_text(json.dumps(ledger, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    summary = {
        "cohort": plan_data["cohort"],
        "status": "EXECUTED_REVIEW_REQUIRED",
        "generation_requests": ledger["attempted_calls"],
        "completed": ledger["completed_calls"],
        "failed": ledger["failed_calls"],
        "retries": 0,
        "golden_approval": False,
        "results": results,
    }
    (output_dir / "results.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return summary


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check")
    check.add_argument("--models-root", type=Path)
    check.add_argument("--hash-models", action="store_true")
    check.add_argument("--output", type=Path)

    prep = sub.add_parser("plan")
    prep.add_argument("--output", type=Path, required=True)
    prep.add_argument("--style", action="append", choices=DEFAULT_STYLES)
    prep.add_argument("--seed", type=int, default=SEED)

    run = sub.add_parser("execute")
    run.add_argument("--plan", type=Path, required=True)
    run.add_argument("--models-root", type=Path, required=True)
    run.add_argument("--output-dir", type=Path, required=True)
    run.add_argument("--authorization-note", required=True)
    run.add_argument("--confirm-generation", action="store_true")

    args = parser.parse_args(argv)
    if args.command == "check":
        result = inspect(args.root, args.models_root, args.hash_models)
        payload = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(payload, encoding="utf-8")
        print(payload, end="")
        return 0 if result["status"] == "PIPELINE_CONFIG_VALID" else 2
    if args.command == "plan":
        result = plan(args.root, args.output, tuple(args.style or DEFAULT_STYLES), args.seed)
        print(json.dumps({"status": result["status"], "jobs": len(result["jobs"]), "output": str(args.output)}, ensure_ascii=False))
        return 0
    result = execute(args.root, args.plan, args.models_root, args.output_dir, args.authorization_note, args.confirm_generation)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["failed"] == 0 else 3


if __name__ == "__main__":
    raise SystemExit(main())
