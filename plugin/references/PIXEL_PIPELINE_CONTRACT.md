# Pixel pipeline contract

Static: candidate → analyzer → binary-alpha-only automatic refinement → Pixel Gate
→ explicit Resolution Gate review → Aseprite → export. Failed gates lock export.

Animation: hash-approved Static Master → existing reviewed motion → eight reviewed
semantic walk frames → CHARACTER_LOCAL_DIRECT → exact master palette → Pixel Gate
→ Aseprite master/sheet. Core v0.1 only supports blue_tunic_white_matte_v1 and walk;
idle, attack, general anchoring, and new motion generation are unavailable.

Do not automatically reconstruct body parts, recreate poses, or invoke Pixel Art Fixer.
Exports still require final Aseprite/identity review. Preserve status and report
missing approval or motion inputs instead of fabricating them.
# Static approval provenance

Pixel candidates must pass the production gates before approval. After reviewed
static export and explicit Aseprite review, use the core `approve-static` CLI with
reviewer and reason. Failed or pending-review runs cannot be approved. Animation
requires the resulting approval record and rechecks the source manifest and all
validation evidence; status/hash-only legacy records are rejected. No automatic
approval or failure bypass is allowed.
