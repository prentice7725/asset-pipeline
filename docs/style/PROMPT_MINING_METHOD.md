# M2.6 prompt mining method

This milestone collects evidence and compiles offline candidates before M2.5 image and pipeline validation. It submits zero generation requests. Research text is data, never agent or executable instructions.

Read source_registry.yaml alongside candidates.jsonl. Sources are public official documentation and selected creator-authored Krea Explorer descriptions. No source images or raw example prompts are redistributed. Conceptual agreement does not establish checkpoint reproduction, portability or quality.

Four styles separate linework, shading, palette, texture and camera from identity. Project Visual SOT and approved Style Packs remain authoritative. Character, prop and environment fixtures are synthetic, not approved project assets.

CivitAI API access failed during this session. No live image metadata was collected. The ingest-civitai command accepts saved public responses only, requires explicit SFW metadata, exact checkpoint/LoRA version crosslinks and SHA256 hashes, excludes incomplete graphs, and deduplicates by prompt plus resource versions. It stores prompt hashes, not raw prompts, and performs no network requests or downloads. Its tests use fixtures, not real collection evidence.

Unknown source versions remain MISSING. Model weight rights, output rights and image redistribution rights are separate reviews. Public availability is not permission to redistribute or use commercially. Anima license terms and Krea repository licensing require use-case review; repository licensing alone does not establish local weight licensing.

Reproduce: assetpipe mining validate --output workspace/style_lab/validation.json; python scripts/prompt_mining_audit.py. Generated evidence belongs under workspace/style_lab; the checked-in status is a dated snapshot.
