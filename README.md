# Hook Router

**One request. Different models. Ordered execution. One parent conversation.**

Hook Router is a small, configurable **Codex plugin with lifecycle hooks** that assigns parts of a request to different model/reasoning profiles. A routing model produces a JSON plan; Python validates and executes it sequentially; the parent assistant receives the report and delivers it to you. Its plugin name is `route`; no skill or MCP server is required.

It is a standalone implementation with **no project-specific services, databases, personal paths, credentials, or workflow records**. Python standard library only. MIT licensed.

> **Platform:** Linux or WSL2, Python 3.9+, and an authenticated Codex CLI with `UserPromptSubmit`, `Interrupt`, `--output-schema`, and `exec resume` support. CLI integration developed against **Codex 0.160.0**. Native Windows/macOS are not supported by this version's `/proc` process supervision.

## Architecture

![Hook Router architecture: parent conversation, JSON routing, sequential workers, and return to parent](docs/architecture.png)

*Generated with GPT Image. The [full generation prompt](docs/architecture-image-prompt.md) is included. The module descriptions and source below are authoritative.*

### Follow the numbered modules

| # | Diagram module | Source | Responsibility |
|---|---|---|---|
| 1 | Hook entry | [`cli.py`](hook_router/cli.py), [`config.py`](hook_router/config.py) | Match `@route`, load the configured profiles, associate the request with its parent session and turn. Ordinary prompts pass through without launching models. |
| 2 | Router model | [`engine.py: router_prompt`](hook_router/engine.py) | Ask a small/cheap model for a **structured plan only**. It must not perform the requested tasks. Profiles are configurable, not inferred from pricing. |
| 3 | Validate + coordinate | [`contracts.py`](hook_router/contracts.py), [`engine.py`](hook_router/engine.py) | Validate supported model/effort pairs and exact source coverage, merge adjacent equal profiles, and run the plan in its original order. |
| 4 | Sequential workers | [`processes.py`](hook_router/processes.py) | Run `codex exec` for each group, switching model/effort while resuming **one persistent worker thread per parent session**. Pass preceding results and evidence forward. |
| 5 | Collect + relay | [`engine.py: report / relay`](hook_router/engine.py) | Add model headers in Python and return `hookSpecificOutput.additionalContext`. **The parent assistant forwards the report**; workers do not answer the user directly. |
| 6 | Private checkpoints | [`storage.py`](hook_router/storage.py), [`engine.py`](hook_router/engine.py) | Atomic plan/state files, per-session lock, thread ID, step results, and private report files. Completed steps are skipped on resume. |
| 7 | Cancellation supervision | [`processes.py`](hook_router/processes.py), [`guardian.py`](hook_router/guardian.py) | Match an `Interrupt` to its session/turn, terminate the active process group, and watch for caller death even when normal cleanup cannot run. |

[`router.py`](router.py) is the portable entrypoint. [`install.py`](hook_router/install.py) merges the two hook definitions into your hooks file while preserving unrelated hooks and backing up the previous file.

### Why consecutive grouping matters

For `A → B → C → D → E`, suppose A/B/C/E use the routine profile and D needs deeper analysis:

```json
{
  "steps": [
    {"model": "gpt-6.1-sol", "effort": "low", "commands": ["A, ", "B, ", "C, "]},
    {"model": "gpt-6.1-sol", "effort": "medium", "commands": ["D, "]},
    {"model": "gpt-6.1-sol", "effort": "low", "commands": ["E"]}
  ]
}
```

**E stays after D.** The router cannot group all low-effort tasks together if that changes the order. Concatenating the command fragments must reproduce the original request *exactly*, including whitespace and separators. Semantic routing is still an AI judgment: exact coverage does not prove the chosen model or task interpretation is correct.

## Quick start

```bash
git clone https://github.com/InfolabAI/hook_router.git
cd hook_router
codex login
python3 router.py --init-config
```

Edit `~/.config/codex-hook-router/config.json` to select **model IDs available to your account**. The included example uses Sol low / Sol medium / Astra high; these are examples, not an availability guarantee. You can use one model with different reasoning efforts, or replace all profiles.

```bash
python3 router.py --check
codex plugin marketplace add "$PWD"
codex plugin add route@hook-router
```

If you previously used this checkout's `python3 router.py --install`, run `python3 router.py --uninstall` after installing the plugin to remove the duplicate personal hooks. It preserves your configuration and session history.

Restart Codex, open **`/hooks` and review/trust the plugin's `UserPromptSubmit` and `Interrupt` definitions**. This is a Codex requirement; installation does not bypass hook trust. Type `@route`, select **Route** (Plugin), and append your request. The picker inserts `@Route`; serialized `plugin://route@...` mentions are also recognized. Selection alone does not run anything; submitting the request starts the hook before the parent model.

The repository root is the plugin package: `.codex-plugin/plugin.json` supplies its identity and menu description, `hooks/hooks.json` registers both lifecycle events using `${PLUGIN_ROOT}`, and `.agents/plugins/marketplace.json` makes this checkout installable. Installed code is cached by Codex; reinstall after updating the source. The personal config and state remain outside the plugin. The bundled hook timeout is 960 seconds (Interrupt: 3); keep `total_timeout` below that or update the hook definition and review trust again.

For a standalone installation without a plugin menu entry, use `python3 router.py --install` instead of the plugin commands. Use only one registration method at a time.

Then, in any Codex workspace:

```text
@route Summarize the supplied notes, extract the action items, review the proposed experiment, then draft a short reply. Do not send it.
```

The parent receives an instruction to forward the report verbatim, with headers such as:

```text
[Model: gpt-6.1-sol | Reasoning: low]

Step 1/3: completed
...
```

The parent relay is an instruction to the parent model, not a deterministic output renderer. Execution order, validation, and checkpointing are enforced by Python.

## Configuration

Start with [`examples/config.json`](examples/config.json). No package installation or API SDK is required.

| Setting | Meaning |
|---|---|
| `trigger` | Prefix to intercept, default `@route`. |
| `router` | Model and effort for the planner. |
| `profiles` | Allowed worker model/effort pairs, names, and descriptions explaining when to use each. |
| `instructions` | Workflow-specific rules given to every worker. Add your own skill/document paths here if needed. |
| `sandbox` | `read-only` by default; `workspace-write` enables normal workspace edits. |
| `network_access` | Default `false`. For network-enabled workers, use `workspace-write` and set this to `true`. |
| `writable_roots` | Optional extra writable directories. The workspace from the hook event is the worker's working directory. |
| `state_dir` | Private state root; default `~/.local/share/codex-hook-router`. |
| `total_timeout` | Total planning + execution budget, default 900 seconds. |
| `router_timeout` / `worker_timeout` | Per-call caps, also bounded by remaining total time. |

For file editing and authorized network operations:

```json
{
  "sandbox": "workspace-write",
  "network_access": true,
  "writable_roots": [],
  "instructions": "Follow this workspace's AGENTS.md. Make only the changes explicitly requested. Verify results and report evidence."
}
```

Merge those keys into your config; keep your profiles and other settings. Worker authorization still comes from the user. Enabling network access is not permission to send messages or modify external systems.

The worker uses `--ignore-user-config`, disables hooks/apps/nested agents, and reuses your **Codex login files**. It does not inherit arbitrary MCP/app configuration. Secret-looking environment variables (including API keys) are removed. Environment-only API authentication is therefore not supported; use `codex login` or supported file-backed Codex authentication.

A new parent Codex session gets a new worker thread. Later routed requests in the same parent session resume that worker thread. The parent's entire conversation is **not** automatically copied: give important context in the routed request or accessible workspace files. Workers retain their own conversation and receive the previous step results explicitly.

### Resume configuration pitfall

All `-c` overrides are placed **after `resume <thread_id>`** when resuming. Splitting overrides before and after `resume` caused network access to revert to disabled in the tested CLI. The regression test preserves this ordering without disabling the sandbox.

## Failure, interruption, and recovery

Worker results have `status`, `report_markdown`, and `evidence`. A successful process exit alone is insufficient: Python validates the result contract and requires `completed` before advancing.

- Invalid router output: one contract retry, then stop without executing workers.
- Failed, blocked, malformed, or timed-out worker: stop all later steps and preserve the checkpoint.
- **ESC / Interrupt:** the installed `Interrupt` handler targets only the matching session/turn and terminates the active guardian/Codex process group. The guardian also watches caller identity and the cancellation marker.
- **Caller killed:** the guardian detects its disappearance and terminates the worker group. Linux PID start times prevent stale records from targeting a reused PID.
- Completed effects are not undone. Local process cancellation is prompt, but provider-side generation/billing may take time to stop. Arbitrarily detached programs that create new sessions are outside process-group supervision.

```text
@route --resume
@route --cancel-plan
```

`--resume` skips completed steps and instructs the interrupted worker to inspect actual effects before continuing. If the worker thread ID was lost, the coordinator refuses to invent a replacement session. `--cancel-plan` cancels only the remaining plan and preserves existing effects/history.

**This is not an exactly-once transaction system.** A remote send can succeed before its receipt is recorded. Use domain-specific idempotency keys and effect verification for messaging, payments, deployments, or other external writes. The generic router cannot prove those effects itself.

## State and privacy

Runtime data stays outside the repository by default:

```text
~/.local/share/codex-hook-router/
  sessions/<hashed-parent-id>/
    lock
    active.json             # current turn + PID identities; removed on normal exit
    state.json              # persistent thread + pending run
    run-*/
      request.txt
      route.json
      plan.json
      router-*/
      step-*/
      report.md
  reports/relay-*/report.md  # complete report for the parent to read
```

Private files use mode 600; created runtime directories use 700. Requests, prompts, results, and persistent Codex worker history can contain sensitive data. They are not deleted automatically. Do not commit them or put `state_dir` in a public checkout. Raw worker event traces are not saved by this wrapper; Codex maintains its own non-ephemeral worker history.

Short reports are included in additional context; long reports are passed by private file path. The parent is told to read the complete file and never rerun the original work. Infrastructure failures fail closed rather than accidentally letting the parent duplicate partially completed work.

The repository includes no credentials or live datasets. Publishing this source does not publish your local config or runtime state. No claim is made that the sandbox blocks access to every readable private file: configure your workspace and task scope appropriately.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

Offline tests use fake Codex processes. They cover source preservation, sequential grouping, persistent-thread handoff, failure/resume, schema validation, networking override placement, installer preservation, parent relay, interrupt cleanup, and cleanup after a forcibly killed caller. No account credentials, student data, external messages, or paid model calls are required.

For a live smoke test after installation, use a synthetic task with no side effects:

```text
@route Use only this fixture; do not access files, network, or external systems. Use routine for A: list two colors. Use analysis for B: explain why one experimental run cannot establish reproducibility. Use routine for C: summarize B in one sentence.
```

## Uninstall

```bash
python3 router.py --uninstall
```

Only this checkout/config command's two hook entries are removed. Other hooks are preserved. State, reports, and Codex worker history remain for inspection; delete them separately only when you choose. `--hooks-file PATH` supports an alternate hooks file for testing or custom setups.

## Documentation

- [Codex hooks and hook trust](https://learn.chatgpt.com/docs/hooks)
- [Architecture image generation prompt](docs/architecture-image-prompt.md)
- [Module source](hook_router/)

The router uses your Codex authentication and account usage allowance. Planner calls, worker calls, retained worker context, and the parent relay all consume usage. Choosing cheaper workers can reduce cost but is not a fixed subscription-limit multiplier.
