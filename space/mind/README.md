# Mind

`space/mind/` is the long-term externalized mind of the subject.

It includes memory, knowledge, principles, decisions, patterns, reflections, invalidated beliefs, and released past context.

## Subdirectories

- `_templates/` contains starter templates for durable Mind entries.
- `memory/` records what happened.
- `knowledge/` records what has been learned and can be reused.
- `principles/` records rules, values, boundaries, and operating commitments.
- `decisions/` records important choices and their reasons.
- `patterns/` records repeated behaviors, constraints, strengths, and successful approaches.
- `reflections/` records reviews and deeper thinking.
- `invalidated/` records what should no longer be believed or reused.
- `released/` records what the subject chooses not to actively carry forward.

## Core Distinction

Memory answers:

> What happened?

Knowledge answers:

> What do I understand now and reuse later?

Knowledge should cite or link back to memory, tasks, resources, or evidence.

## Knowledge Organization

`space/mind/knowledge/` may be organized by the subject's real life, work, role, or team domains.

AI Workroot intentionally does not force a universal second-level taxonomy. A person, writer, tester, product team, executive team, or research group may create the knowledge directories that match how they actually think and work.

Examples of valid organization patterns:

- `space/mind/knowledge/writing/`
- `space/mind/knowledge/health/`
- `space/mind/knowledge/product/`
- `space/mind/knowledge/testing/`
- `space/mind/knowledge/company-strategy/`
- `space/mind/knowledge/ai-workflows/`

Each durable knowledge area should remain understandable and discoverable:

- add a local `README.md` or `_index.md` when a directory becomes important
- keep reusable knowledge under `space/mind/knowledge/`
- link knowledge back to source memory, tasks, resources, decisions, or evidence
- update the knowledge index for important entries
- do not mix raw task logs, raw data dumps, or active task state into knowledge directories

## Remembering And Releasing

AI Workroot should help the subject remember what matters and release what no longer needs to remain active.

When a difficult experience has already produced useful learning, the lesson can stay in `knowledge/`, `decisions/`, or `patterns/`, while the painful source context can move to `released/`.

Released material should not be part of normal startup or retrieval. It should only be surfaced when the user asks, or when a serious safety, legal, or integrity reason requires it.
