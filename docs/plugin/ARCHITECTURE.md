# Architecture

The plugin is an interface/orchestration layer; assetpipe is the production engine.
integrations/mcp validates requests and configured-root references, delegates to
assetpipe.api, launches the existing fixed CLI for generation, and reads manifests.
No workflow routing, image processing, palette, frame, or Aseprite logic is copied
into the adapter. The registry remains authoritative.

Core changes are limited to a high-level API, exposing existing required capabilities,
and extracting existing animation input checks into a reusable preflight function.
The verified pixel arithmetic and provider bridges remain unchanged.

Long operations launch the installed assetpipe CLI with fixed argv, shell=false,
and hidden Windows subprocesses. A launch receipt links a UUID to the existing
core run manifest; there is no queue, DB, scheduler, or retry engine. Inspect reads
the core manifest. Closing MCP does not cancel a running core CLI process.
Unexpected process termination can leave the core manifest RUNNING; this adapter
does not infer completion or provide an administrative cancellation tool.

Security: host-controlled core/source/output roots; resolved paths reject traversal
and symlink escapes; tool arguments cannot choose executable/config roots, raw
workflow JSON, Python code, or shell commands. Requests and outputs are retained
only inside the configured output root. Registry/config changes remain host operations.

Local stdio support and SDK smoke are implemented. Plugin Creator and actual
host installation are separate gates. No ChatGPT remote deployment is introduced.
