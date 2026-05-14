# Runtime Work

This folder holds internal work mechanics.

Ordinary users should not manage this folder manually. The AI agent creates and updates internal work records when a request has a goal, expected result, future value, or continuation need.

User-visible outputs, reports, and summaries belong in `space/work/`.

## Structure

```text
active/
closed/
_templates/
```

## Recommended Internal Files

```text
task.json
task.md
brief.md
decisions.md
todo.md
index.md
scratch.md
handoff.md
outputs/
archive/
```

`scratch.md` is an optional working scratchpad. It should not become a startup requirement.

`handoff.md` is the task-level continuation card. Keep it short enough for the next agent to resume without reading the full task history.

When a task closes, compress it into durable summaries, decisions, outputs, links, and promoted Mind entries. Move noisy process material into `archive/` so long-term context stays small.
