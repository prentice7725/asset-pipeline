# Workflow status rules

ACTIVE is the only automatic selection status. VALIDATED can be explicitly requested.
EXPERIMENTAL requires an explicit ID and allow_experimental=true. REJECTED never runs.
Experimental recovery must not be automatically substituted for a failed gate.
Use capabilities and the core registry for current names and supported input modes.
A CLI provider cannot be ACTIVE without recorded real-generation evidence. BLOCKED (not signed in) and UNAVAILABLE
(not installed) are reported as-is; never work around them with API keys, other tools, or substitute images.
