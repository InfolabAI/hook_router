# Verification

Validated on Linux with Python 3.9 and Codex CLI 0.160.0.

## Automated checks

`python3 -m unittest discover -s tests -v`

Ten offline tests cover contract validation, exact source reconstruction, adjacent grouping, low → medium → low sequencing, shared worker thread continuity, context handoff, failure/resume, refusal to replay when thread identity is missing, installer idempotency, private relay storage, and actual process cleanup.

The process integration tests run fake local Codex executables. They check both a matching Interrupt event and SIGKILL of the caller, asserting that the fake worker and its ordinary child process exit. A mismatched turn must not interrupt the worker. These tests do not call paid models or use credentials.

## Live smoke test

A synthetic request using no tools, files, network, or external effects ran through real Codex:

1. Sol low: name two colors.
2. Sol medium: explain why a single experiment cannot establish reproducibility.
3. Sol low: summarize the preceding explanation.

The router produced three ordered groups. All completed in one persistent worker thread. The third step used the second step's result. Python added model headers and emitted a UserPromptSubmit additionalContext envelope for the parent to relay.

The first smoke test exposed an ambiguity between JSON encoding quotes and request text. The router instructions were clarified to decode the input JSON string once. Source-preservation validation rejected both incorrect plans before any worker task executed.

Local tests verify the hook output contract. Actual parent wording and graphical ESC behavior depend on the installed Codex client and hook trust; there is no claim of byte-for-byte model relay enforcement or instantaneous provider-side cancellation.

## Publication review

The public checkout contains source, synthetic fixtures, example configuration, documentation, the GPT Image diagram, and its generation prompt. Runtime state, authentication, live prompts/results, personal paths, private messages, and workflow databases are excluded. Commit metadata uses a generic contributor identity.
