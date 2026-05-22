# Current Development TODOs

## Work Continuity Control And Agent Operation Entry

Status: pending design.

Background:
AI Workroot currently has Work, checkpoint, handoff, and Context Control concepts, but the active Clean Workroot path does not yet provide a strong operation surface for long-task continuation after compaction, interruption, or agent handoff.

Next design pass:
- Define Work Continuity Control as the active managed-state capability for long-task resume.
- Keep Native Agent Entry files short and point agents to `workroot continue --cwd .` and `workroot context --agent <agent> --cwd .`.
- Add a machine-readable agent operation manifest, for example `workroot agent manifest --format json`.
- Make critical writes go through package runtime and CLI, not agent-authored internal files.
- Add CLI/API surfaces for `workroot work ...`, `workroot checkpoint ...`, `workroot handoff ...`, and `workroot continue`.
- Ensure Context Control prioritizes active work state, current step, latest checkpoint, next action, and required context refs.
- Keep all managed state under `AI_WORKROOT_HOME`; do not write task control state into the user-selected directory by default.
- Add compact/resume regression tests and live-agent E2E coverage before considering the capability complete.
