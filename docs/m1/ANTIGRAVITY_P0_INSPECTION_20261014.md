# Antigravity P0 inspection and source integration — 2026-10-14

Reference for pipeline developers and operators. This records the first local,
non-generating inspection requested after the
[provider design](ANTIGRAVITY_NANO_BANANA_PROVIDER_DESIGN_20261014.md).

State: **P0_PARTIAL / INTERNAL_ATTEMPT_BUDGET_UNVERIFIED / NO_GENERATION_RUN**.
No provider adapter, workflow registration, routing change or operational runtime
replacement is included in this work.

## Latest integration and preservation

Local `main` fast-forwarded from `e910208` to `f6212c6` after fetching origin.
This includes PR #19 local plugin packaging, PR #20 canonical Grok session
collection and PR #22 Antigravity design, including its attempt-budget correction.
New work uses `codex/antigravity-p0-inspection-20261014`; main is not directly committed.

The 82 pre-existing modified/untracked files were archived before integration in
`workspace/maintenance/20261014/local-before.zip`, with original hashes and a
binary patch. Tracked changes also remain in stash
`caf5f4a1bf6d0d43bd561e6c91b182216aa1041e` after application.

77 local files retain identical bytes. Two provider overlaps retain the merged
PR #20 implementation, which incorporates the previous local Windows fixes and
adds canonical-cwd correlation. The pre-existing untracked Windows regression
file is now supplied by upstream; contents match after newline/trailing-whitespace
normalization. Its exact original bytes also remain separately archived.
Two historical local plugin notes had four broken relative links after the
stricter package validation arrived. Only those link targets were repaired to
documents actually bundled in `references/`; their original bytes remain backed up.
All 4,702 files present in the operating-runtime baseline retain identical hashes.
This comparison is against the start of this task, **not a renewal of the older
release seal or an activation approval**.

## Code, runtime and evidence

| Item | Observed result | Limit |
| --- | --- | --- |
| Installed executable | `C:\Users\seung\AppData\Local\agy\bin\agy.exe` | Host installation only |
| CLI version | `1.3.4`, exit 0 | Does not pin the image backend |
| Executable SHA-256 | `7ebd139553a276ea9399d429a77bc2802c9941dd3cecbe8ee6ad7776c50abcb1` | Fingerprint at inspection time |
| Print options | `--print`, `--output-format`, `--print-timeout`, `--disable-slash-commands`, `--sandbox` listed in local help | Help is not effective permission enforcement evidence |
| Host metadata probes | `models` and `agents` exit 0 in a fresh temporary cwd outside project trees | Does not prove image access, reference consumption, account budget or generation success |
| Initial sandbox probes | Home/log access errors and a not-logged-in diagnostic | Not a reliable statement about the real host login |
| Hard internal attempt bound | Not established | Paid dispatch remains blocked |
| Image event/path correlation | Not established | No generated file was collected |
| Registry and default selection | No new provider/workflow entry | Existing providers and review gates remain |
| MCP protocol | initialize, exact six complete schemas and negative path cases PASS | Separate owned offline process; capability readiness stubbed |

The controlled host probe used `assetpipe-agy-p0-*` under the OS temporary
directory, with no prompt, reference, project directory or generation command.
It issued version/help/models/agents only. Child CLI exits were observed; no
process termination was used. CLI metadata commands may maintain their own
profile caches/logs. Secret-bearing raw home/auth logs were not archived.

Local evidence: `workspace/maintenance/20261014/agy-probe.json`, `before.json`,
`verification.json`, and `protocol-final/protocol_report.json`. Evidence under
`workspace/` remains outside tracked source. Host query exit codes do not imply
the language server's full permission surface has been audited.

### Official contract review

The [headless reference](https://antigravity.google/docs/cli/headless/) describes
conversation IDs, streaming tool events and terminal results. It also documents
soft permission denial with exit 0 and automatic workspace file access. These
events are a proposed parser basis, not observed image-generation evidence.

The [SDK tools reference](https://antigravity.google/docs/sdk/tools/) exposes
`CapabilitiesConfig.enabled_tools`/`disabled_tools`, including a distinct image
tool. The [policy reference](https://antigravity.google/docs/sdk/policies/)
documents explicit allow/deny rules. This makes a restricted typed SDK worth
investigating; it does not prove control over attempts inside the image tool.

The [official changelog](https://antigravity.google/docs/changelog?tab=cli)
records up to three image-generator attempts in v1.2.16. No enforceable
one-image-attempt control was established by the inspected local help or these
references. This is an evidence gap, not a claim that such control is impossible
in every SDK version. Keep the dispatch block until enforcement is demonstrated.

## Existing uncommitted work

Portrait extension/repair, fusion/video, project style settings, research sources,
plugin skill edits and their fixtures remain local and uncommitted. They are not
implicitly included in a provider release. Preserve their evidence and review
states. Experimental research remains separate from production defaults.

## Priorities and completion gates

1. Finish P0 by inspecting enforceable CLI/SDK tool restrictions and internal
   image-generator child attempts. Natural-language requests for one attempt do
   not establish a bound. Do not invoke image generation to discover this limit.
2. Establish an event contract for request/session identity, tool execution,
   terminal status, exact artifact paths, image count and reference consumption.
   Windows long paths and nested reparse aliases must be covered.
3. Choose CLI versus typed SDK only when restriction and evidence requirements
   are attainable. If unresolved, retain `INTERNAL_ATTEMPT_BUDGET_UNVERIFIED`.
4. Then implement P1 against fake fixtures only: authentication failures, exit-0
   soft denial, missing calls, over-attempts, foreign/ambiguous/corrupt outputs,
   references, secrets, recursion, timeout and concurrency. Preserve P1/P2
   containment gates and exactly six MCP schemas.
5. P2 real T2I/edit cohorts need separate explicit request and budget, followed
   by QA and human review. No tests or CLI metadata query substitute for E2E.

## Validation and approval boundary

Editable installation with `.[dev,motion]` succeeded on the host after the
sandboxed build-dependency download failed due to DNS restrictions. CLI help
passed; Python imports resolve to this checkout's `src/assetpipe` through
`.venv/Scripts/python.exe`.

The sandboxed full pytest reported 226 failures, 69 errors, 356 passes and 12
skips, including file-replacement/resolve permission errors. The first host
rerun reported 658 passes and 5 failures: its temporary directory was mistakenly
inside this repository and too long for a Windows fixture (2 failures), and the
four historical local-document links broke package checks (3 failures).
The final host run uses a short, unique temporary directory outside the source
tree, after the link-only repairs: **663 PASS / 0 FAIL / 0 ERROR / 0 SKIP**
in 207.32 seconds (`pytest-host-final.xml`). This includes local uncommitted
portrait/fusion/video fixtures in addition to the upstream tests. These counts
describe this preserved working tree, not a clean-checkout PR-only test cohort.
No failing assertions, gates or tests were relaxed.

Generation requests: **0**. No operational MCP restart/replacement, real image
collection, Golden approval, provider ACTIVE promotion or SOT change occurred.
The inspected Antigravity candidate remains **BLOCKED for paid dispatch**.
