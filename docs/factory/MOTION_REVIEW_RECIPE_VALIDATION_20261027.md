# Motion review recipe validation — 2026-10-27

Branch: `codex/motion-review-recipe-20261027`, base `1ebf8e6`.
Scope: [explicit offline recipe and review contracts](MOTION_REVIEW_RECIPE.md).

## Real existing-asset replay

The installed CLI actually ran plan → apply → inspect against the original
56-frame package from the single user-authorized generation. The recipe selected
13..32 and explicitly applied the white-border mask and reviewed lower-body pale
cleanup regions. No re-generation, provider retry or live runtime change occurred.

| Measurement | Actual result |
| --- | --- |
| CLI plan digest | `daa3c78acb746c36384c23313a39aac7ff2ee58c7af61b043660267d8064770f` |
| Replay receipt SHA-256 | `c32be6128be278672921bb465a22fffde01296cd017b99a3effc49c15c4bc5d3` |
| Selected frames/FPS | 20 / 24, original frames 13..32 |
| Final RGBA equivalence | All 20 equal previous manual cleanup-v2 frame pixels |
| Atlas equivalence | Same RGBA pixels as the prior manual candidate |
| Protected files | 320 before/after hashes match |
| Inspect | `ARTIFACT_INTEGRITY_PASS_REVIEW_REQUIRED` |
| New generations / human approvals | 0 / 0 |

The replay is byte/pixel provenance evidence for this explicit recipe. It does
not establish automatic loop selection, universally safe rectangles, a new
quality score, additional engine testing or Aseprite review. Previous halo,
headroom, anatomical pivot and startup timing limitations remain documented;
new `review.json` is pending with every human check null.

Ignored evidence is under `workspace/motion-review-recipe-20261027/`: original
recipe, installed CLI plan/apply/inspect logs, replay receipt/intermediates,
pixel/hash verification, installation/help and regression logs. Live source
references used the same explicitly allowed configuration, selected static-run
and historical generated-image directories as the original research evidence.

## Software checks

Required editable `.[dev,motion]` install and installed `assetpipe --help` passed.
The initial restricted-environment focus run had **5 failures / 10 passes /
20 fixture errors**, all at the shared Windows JSON replacement operation.
No retry or permission-bypass code was added. The same suite was rerun with
normal local execution permissions and a fresh bounded test directory.

That normal run exposed one test assertion comparing RGB-vs-RGBA PNG file hashes
for a preserve operation; the actual requirement is equal decoded RGBA pixels.
The fixture/check now also covers existing partial alpha, and the subsequent
focus run was **35 passed** (12.68s), including unchanged original codec/package
tests. Source-drift, root-escape and relative-reference snapshot cases were then
added to the full regression.

Final full regression: **743 passed / 1 skipped / 0 failed**, 744 collected,
**442.25s**, Windows Python 3.11.9 / pytest 9.1.1. All 23 recipe cases, existing
motion/package/executor, roots/security, still/pixel/SFX/style and six-MCP-contract
tests passed. The skip is the existing unavailable local migration benchmark;
historical frame-equivalence evidence is not relabeled as a new pass.

Command: `.venv/Scripts/python -m pytest --basetemp C:/workspace/asset-pipeline/workspace/mr27fullA`.
The test directory was checked absent before execution. Log: `pytest-full.log`
under the evidence directory. `git diff --check` also passed.

Verdict: **OFFLINE_CONTRACT_PASS / EXISTING_ASSET_REPLAY_EQUIVALENT /
HUMAN_REVIEW_REQUIRED / GENERATION_NOT_RUN**. Quality improvement beyond faithful
replay is **NOT_MEASURED**; no new model, art, engine or human-approval claim.

The tests cover rejected/unknown contracts, source/recipe/plan drift, stale or
missing artifacts, spoofed review/receipt changes, output containment, failed
transforms/intermediate preservation, no-overwrite and exact inherited pixels.
They do not call models or synthesize real user art/approval evidence.

Tracked changes: `motion/recipe.py`, CLI, shared atlas-packing extraction in
`motion/package.py`, schema/example, recipe tests and usage/evidence docs plus
README/CHANGELOG. Existing algorithms, six MCP contracts and production defaults
are preserved. Rollback and evidence-retention instructions are in the usage doc.
