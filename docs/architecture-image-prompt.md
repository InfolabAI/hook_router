# Architecture image prompt

Generated with the built-in GPT Image tool. This is the exact intended diagram specification; implementation details in the README and source remain authoritative.

## Prompt

Create one exceptionally legible, polished software architecture infographic for an open-source GitHub README called “Hook Router”. Landscape canvas, approximately 2400 by 1600 pixels, high resolution, crisp typography, generous whitespace, warm off-white background, dark navy text, thin precise connector lines. Use flat vector-like technical illustration rendered as a PNG, not photorealism. No logos, no private names, no account identifiers, no filesystem paths tied to a person. All visible text must be English. Clearly readable at full size; prefer short labels rather than tiny paragraphs. Rounded rectangular cards with subtle borders, small numbered circular badges, understated shadows. Color coding: parent conversation blue, deterministic Python coordinator charcoal/teal, router model amber, worker steps green/purple/green, cancellation coral, persistent storage muted slate.

Headline at top: “Hook Router”
Subtitle: “Plan once. Execute in order. Return results to the parent.”

The central conceptual message MUST be unmistakable: a user gives a request to a parent Codex conversation; before that parent responds, a UserPromptSubmit hook runs a cheap routing model; deterministic Python validates and executes the router's plan sequentially through model-specific Codex workers; their results return to the SAME parent conversation via additionalContext; ONLY the parent delivers the final answer to the user. The router does not execute tasks. Worker outputs are NOT sent directly to the user. The parent does NOT rerun the tasks. Represent the parent conversation as one large blue band spanning the top with a left “Request received” region and a right “Parent relays result” region, explicitly connected and labeled “Same parent conversation”. A user icon above the left region supplies “@route A, B, C, D, E”; a response bubble above the right receives “Final answer + model headers”. A clear downward arrow from the left parent region is labeled “UserPromptSubmit”. A clear upward return arrow into the right parent region is labeled “additionalContext”. No direct arrow from workers to the user.

Arrange the processing area below this parent band in the following readable left-to-right lanes:

Badge 1: “Hook entry” with file label “cli.py”. Small supporting line “Match trigger + session + turn”. A small configuration card above or beside it labeled “config.py” and “Profiles • trigger • permissions” points toward the hook and planner.

Badge 2: amber “Router model” card with file owner “engine.py” and supporting line “Structured JSON plan”. Inside the card, three short explicit stacked plan entries:
“1  low: A, B, C”
“2  medium: D”
“3  low: E”
Caption: “Merge adjacent tasks only”. Show the distinction that the router proposes a plan but a Python module owns execution.

Badge 3: teal/dark “Validate + coordinate” card labeled “contracts.py + engine.py”. Supporting text, each concise: “Exact source coverage”, “Allowed model / effort pairs”, “Preserve task order”. Its outgoing arrow feeds a visibly sequential worker lane, NOT parallel fan-out.

Badge 4: a clearly bracketed lane titled “Sequential Codex workers — one persistent thread”. File label “processes.py”. Three cards in a strict horizontal sequence with bold arrows between them:
“Step 1” / “Sol • low” / “A → B → C”
“Step 2” / “Sol • medium” / “D”
“Step 3” / “Sol • low” / “E”
Put “resume same thread” above the arrows between worker cards. Add a small lower caption “Previous results + evidence passed forward”. A small note by this lane: “Stop on failed / blocked / interrupted”. No visual suggestion of concurrent execution.

Badge 5: “Collect + relay” card with file label “engine.py”. Supporting lines “Model headers added by Python” and “Parent forwards report verbatim”. This card is the origin of the upward additionalContext arrow to the same parent conversation. A tiny result strip can read “[Model: … | Reasoning: …]”. Keep it legible and clearly an example.

Below the processing area place a horizontal storage band with a database icon and badge 6, labeled “Private checkpoints” and “storage.py”. Three short segments: “plan + step status”, “thread ID + reports”, “active process identity”. Dashed write/read connectors from coordinator and workers. Caption “Resume skips completed steps; uncertain effects require inspection”. Do not imply guaranteed exactly-once execution or rollback.

At the bottom place a coral cancellation lane with badge 7, labeled “Cancellation supervision” and file labels “processes.py + guardian.py”. Left: “ESC / Interrupt”. Center: “Match session + turn” then “Signal worker process group”. Right: “Parent exit monitor”. Dashed coral arrows point up toward the active worker lane, never toward unrelated sessions. Supporting text “Stop clients + descendants; prevent later steps”. A small caveat “Already completed effects are preserved” below it. Do not claim instantaneous server billing cancellation. Indicate the guardian watches the caller and cancellation marker even when the caller is killed.

A small footer note in subdued gray: “Linux / WSL2 • Python standard library • Codex CLI”. A compact legend differentiates solid arrows “Execution / result flow”, dashed gray “State”, dashed coral “Cancellation”. Visually balance all seven numbered modules, align cards on a grid, avoid connector collisions, do not crowd text. Every requested file name must be spelled correctly. Avoid decorative filler, robots, vague clouds, extraneous services, or unrelated databases. The architecture should be understandable without reading the README but must remain faithful to the described actual module boundaries.

## Correction pass

Make one precise correction to the otherwise finished architecture diagram. Preserve every card, all text, numbering, colors and overall layout. The downward blue UserPromptSubmit connector currently lands on module 3, Validate + coordinate. Redirect it from Parent Codex conversation / Request received to module 1, Hook entry / cli.py, with a clean elbow connector through the open whitespace above modules 1 and 2. Its arrowhead must land on module 1. Remove the old downward arrow into module 3. Keep the main horizontal chain 1 → 2 → 3 → 4 → 5 unchanged. Also make the coral cancellation connectors visually target the active worker lane (module 4), using a dashed coral path around the storage band, with an unambiguous arrowhead on the bottom edge of module 4. No other content changes.
