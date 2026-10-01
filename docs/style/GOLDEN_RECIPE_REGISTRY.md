# Golden recipe registry

Golden recipes: **0**. Every M2.6 recipe remains NORMALIZED, offline_only, production_state NOT_RUN, approved_for empty. Candidate schema forbids self-approval, local generation claims and pipeline claims.

The editable candidate recipes live in config/styles/recipes/anima.yaml, krea2.yaml and pixel.yaml. They do not replace config/styles/model_recipes.yaml and cannot become production defaults through the offline CLI. Common style catalog additions are UNTESTED. No preference or quality score is fabricated.

A future promotion requires immutable source provenance, exact dependency hashes, measured generation and pipeline records, and an explicit human approval tied to recipe/style versions, output class and reviewed images. Changes invalidate previous approval. Approved-for scope must remain narrow. Neither official documentation nor filename inventory qualifies as measured evidence.

Current snapshot: M26_STATUS.json. M2.5 generation and full pixel/nonpixel validation have not run.
