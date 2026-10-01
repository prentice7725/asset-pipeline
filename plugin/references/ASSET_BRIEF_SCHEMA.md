# Asset Brief contract

Required fields: asset_id, asset_type, output_class, purpose, source, identity,
constraints, animation, workflow_preferences, forbidden_elements,
unspecified_elements, and source_notes. The installed core schema is authoritative.

Source types: PROMPT, REFERENCE_IMAGE, DOCUMENTS. Preserve source paths/references.
Canonical and visual traits remain separate. Constraints record resolution,
transparency, palette, silhouette, and style; unknowns stay null or unspecified.
Animation records action, frame_target, and motion_constraints.

For documents, the host reads sources before creating a prepared brief. Every
source note cites a supplied document and is EXPLICIT, DERIVED, or UNSPECIFIED.
Calling the builder without extracted facts creates a validated unresolved brief;
generation stays BLOCKED until source-backed canonical traits are supplied.
Project canon remains outside Asset Pipeline.

M2 optional `style_id` references shared style knowledge for NONPIXEL_IMAGE.
`project_id` selects configured project Visual SOT/Style Pack.
`workflow_preferences.model_profile` explicitly selects a configured model profile;
it cannot contradict `workflow_preferences.id`. Existing briefs need no new field.
Read [Style Intelligence](STYLE_INTELLIGENCE.md) for provenance and approval rules.
