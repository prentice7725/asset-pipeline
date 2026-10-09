# Project portrait routing

Use the existing prepared Asset Brief with its registered `project_id`.
`project_contract_required: true` prevents an unregistered project from using the
common catalog. No new MCP tool is needed; pass the prepared Brief to `asset_route`.

For isekai examiner portraits use `project_id: isekai_examiner` and
`asset_type: character_portrait`. The engine resolves the source-backed portrait
adaptation from `config/styles/projects/isekai_examiner/visual_sot.yaml`, with an
UNTESTED project recipe. It does not apply the common bold/saturated STYLE-104
contract or impose portrait rules on environments. Environment routing is not
given portrait-specific rules.

The selected Day 01 backwall Brief uses `asset_type: environment_background_layer`
and `art_style: watercolor_storybook`. STYLE MENU v1 resolves this to STYLE-111 /
Krea2. The project Visual SOT provides its environment-only descriptor adaptation
and recipe; route output identifies `PROJECT_VISUAL_SOT` as the style definition
source and separately identifies `config/styles/style_menu_v1.yaml` as the menu
binding source. The current menu's CAND-011 is shown only as its recorded exemplar.
Both recipe and style remain UNTESTED / REVIEW_REQUIRED.

Use `subject_integrity.class: character_portrait`, explicit source-required visible
parts, `physically_connected_body: true`, and `whole_subject_required: false`.
Preserve source crop, identity, clothing and forbidden requirements. Do not mix
project free-text style with `prompt_spec.style_contract_id: STYLE-104`, which
selects the unchanged common structured contract.

The portrait project permits positive natural-language exclusions plus mandatory
itemized human review. Native negative and transparency capabilities remain false.
The portrait path requires a configured hash-verified local segmentation model and
the `portrait` dependency extra. The opaque environment wall has no alpha operation;
it uses the approved negative-instruction policy only for prompt compilation.
Technical route status does not certify style quality or forbidden absence.
`required_capabilities` lists all requirements; `missing_capabilities` lists only
unsupported ones. `constraint_issues` reports delivery dimensions separately.
No generation, fallback, model replacement, constraint removal or art approval is
authorized by a route or this reference.
