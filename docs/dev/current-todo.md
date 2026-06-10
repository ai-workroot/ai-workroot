# Current Development TODOs

## Work Continuity Control And Agent Operation Entry

Status: superseded by 0.9.531 Agent Protocol, Task Continuity, and Context Strategy implementation work.

Background:
AI Workroot now has the first implemented operation surface for long-task continuation: `workroot context`, `workroot agent sync`, and `workroot agent commit`.

Current active guidance:

- Keep Native Agent Entry files short and point agents to `workroot agent sync --agent <agent> --cwd . --query "<current user request>" --format packet`.
- `workroot agent sync` is the normal meaningful-turn entry and returns compact context plus the lease/contract for durable work.
- `workroot context` is read-only auxiliary behavior for startup recovery, manual recall, and debugging.
- `workroot agent commit` is the only Agent fact entry for tasks, checkpoints, assets, decisions, handoff, and state updates.
- Critical writes go through package runtime and CLI/MCP-equivalent protocol adapters, not agent-authored internal files.
- Managed runtime state stays under `AI_WORKROOT_HOME`; user-space writes are limited to authorized Native Agent Entry and user-visible outputs such as `workroot-output/START_HERE.txt`.

Future work:

- Optional agent manifest/discovery surface.
- MCP-native entrypoint over the same protocol semantics.
- Further context recall strategy improvements.
