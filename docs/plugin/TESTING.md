# Testing

```powershell
.venv/Scripts/python.exe -m pytest
.venv/Scripts/python.exe scripts/plugin_m0_smoke.py
.venv/Scripts/python.exe scripts/package_plugin.py
```

The suite includes original core regression plus schema, path boundary, workflow
selection, missing approval, argument validation, API delegation, and read-only
inspection tests. Packaging checks are structural validation, not Creator validation.

The real SDK stdio smoke script executes exactly the four requested M0 flows:

- A: capabilities match the actual registry and local providers respond.
- B: one ACTIVE Anima Base nonpixel image; no quality comparison.
- C: approved legacy fixture + existing video, eight exact RGBA frames, Pixel Gate,
  real Aseprite export, and review-required status. No new motion generation.
- D: source-extracted document brief through builder and router; no generation.

Real smoke requires local ComfyUI, Aseprite, FFmpeg, and the adjacent legacy fixture
data. Evidence and logs remain under workspace/plugin_m0. Packaging refuses to run
without four passed MCP smokes. It checks manifest paths, six schemas, skill references,
fixed stdio wiring, and a single-root ZIP without production code or raw artifacts.

Overall ASSET_PIPELINE_PLUGIN_M0_PASS is withheld until the official Creator
validation and actual target-host installation gates are verified.
