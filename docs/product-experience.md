# Product Experience

AI Workroot should feel simple even when the underlying system is rigorous.

For ordinary users, AI Workroot is not a framework to learn. It is a personal Workroot where they can work with AI, preserve what matters, and continue later.

## Product North Star

The first product goal is:

```text
first useful preserved result
```

A new user should be able to:

1. choose or create a directory for their own assets
2. initialize a Workroot without polluting that directory with managed state
3. open it with an AI agent
4. give a small usage direction when needed
5. do one real piece of work
6. preserve the useful result
7. continue later without reconstructing the whole chat

## User Promise

For ordinary users:

```text
You say what you want to do.
The AI helps you do it.
The Workroot keeps what matters.
Next time, you can continue.
```

The user should not need to understand tasks, indexes, registries, databases, folders, protocols, or memory taxonomies before getting value.

For ordinary users, a task should mean only:

```text
the thing we are working on now
```

The detailed interaction rules are defined in `docs/user-interaction-contract.md`.

## Experience Principles

- Start with work, not architecture.
- Ask the fewest setup questions needed.
- Let guidance emerge progressively.
- If the user brings a real problem first, ask at most one small usage-direction question before helping.
- Infer structure from intent.
- Help users move from chat-style questions into task-style work when it will help them continue later.
- Hide internal mechanics from ordinary users.
- Save useful results without making the user file them manually.
- Make continuation obvious.
- Let advanced users inspect and improve the system.

## Ordinary User Journey

### 1. Get A Workroot

The user chooses or creates a normal directory for their own files. Clean Workroot treats that directory as user asset space.

By default, managed state is stored outside the user directory under `AI_WORKROOT_HOME`. This includes Workroot records, context packages, indexes, diagnostics, handoffs, relationship projections, release records, and caches.

The user directory should remain clean unless the user explicitly authorizes user-facing generated files such as short Native Agent Entry launchers.

### 2. Open With AI

The user opens the directory with Codex, Claude Code, or another capable AI agent.

The user can start with one sentence:

```text
I want this Workroot to help me with [area]. Please set it up with me, then help me start my first real task.
```

Longer prompts may help less capable agents, but they should not be the primary product experience.

Users may also start with their real problem:

```text
I have meeting notes and many follow-ups. Help me organize them.
```

```text
I am in grade 7. Help me understand fractions and make practice questions.
```

### 3. Clarify Usage Direction

The AI asks only what is needed:

- what the Workroot should help with
- what the AI should help with
- what values, preferences, or boundaries matter

The user can answer briefly. The Workroot's managed guidance can evolve later.

### 4. Do The First Real Work

The user says the work in natural language.

The AI decides behind the scenes whether this is a quick answer, tracked work, a project, a decision, learning, handoff, or knowledge preservation.

The AI should help users understand the boundary in plain language:

```text
This looks like our current task. I will keep the next step clear so we can continue later.
```

### 5. Preserve What Matters

The AI asks lightweight confirmation when needed:

```text
This looks useful for the future. Should I save it?
```

The user does not choose a folder or internal category. The Workroot records the result in the appropriate managed state and writes user-facing assets only when the user asks for or authorizes them.

### 6. Continue Later

The user can return and say:

```text
Help me continue.
```

The AI should read the current managed handoff and tell the user:

- what was happening
- what was decided
- what the next useful step is
- whether to continue, adjust, or start something new
- what sentence the user can say next

The human-facing continuation view should be plain language. It may be rendered into the conversation, generated as an authorized user-facing asset, or stored in managed state for the next context package.

## Agent Product Responsibilities

An AI agent inside Workroot is not only an executor. It also acts as:

- onboarding guide
- intent router
- work organizer
- continuity keeper
- task history reviewer
- knowledge steward
- handoff writer
- privacy and release guardian

These responsibilities are product behavior, not optional polish.

## First Run Protocol

On first use, the agent should:

1. use the active Native Agent Entry or CLI context package when available
2. check whether usage direction is clear enough
3. ask only the missing guidance needed to preserve durable work responsibly
4. save the minimum guidance into managed Workroot state
5. ask for the first real piece of work
6. infer the right internal structure
7. help produce a useful result
8. preserve what matters
9. leave a continuation path

Do not explain the full architecture during first run unless the user asks.

Do not ask ordinary users to open or manage internal managed state.

If the user already gave a real problem, ask at most one small usage-direction question before useful work. Do not block the first useful result behind a full setup interview.

## Intent Routing Protocol

When the user speaks naturally, infer the mode:

| User intent | Agent behavior |
| --- | --- |
| simple question | answer directly, offer to save if useful |
| work with a goal | organize internally and help finish it |
| larger effort | break it down and start the first useful step |
| decision | compare options, record choice and reason |
| learning | explain, then preserve reusable understanding |
| continuation | read handoff and resume |
| history review | list or summarize local tasks, outputs, decisions, and saved knowledge |
| old painful or noisy context | preserve lesson, then release or quiet details by user choice |

The user should not need to name these modes.

## Task Collaboration Protocol

Users may start with normal questions. The agent should answer directly when it is just a quick question.

When a question becomes a larger effort, the agent should gently frame it as the current task:

```text
This can be a quick answer, or we can treat it as a task and keep track of the next step.
```

When the user returns vaguely, the agent should reconnect them to the current task:

```text
Last time we were working on your fractions study task. The next step was practice questions on adding fractions. Continue there?
```

When a task ends, the agent should say:

```text
This task is finished. I saved the useful result and the next thing to remember. Do you want to start a new task?
```

This should work for a grade 7 student. Avoid adult technical language when the user is a child or beginner.

## Continue Protocol

When the user says:

```text
Help me continue.
```

The agent should:

1. read concise current context and handoff
2. identify the most recent active work
3. summarize the last state in plain language
4. name the next useful action
5. ask whether to continue, adjust, or start something new

The agent should not ask the user to reconstruct the previous session from memory.

The agent should not send ordinary users into internal state, registry files, schemas, or contracts to understand what happened.

For delegated work, the agent should keep a plain-language collaboration map in the continuation view:

- parent work
- delegated work
- findings
- outputs
- decisions
- reusable knowledge
- next human decision

Every continuation view should include a sentence the user can say next.

## History Review Protocol

Users may ask:

```text
What tasks have I done before?
```

```text
Summarize what we finished last week.
```

```text
What useful knowledge have we saved?
```

The agent should answer from local Workroot records. It should list tasks, visible outputs, decisions, and saved knowledge when useful.

The agent should not rely only on chat history. If records are incomplete, say that plainly and summarize what is available.

Use the user's language for the answer.

## Save What Matters Protocol

When the user says:

```text
Save what matters.
```

The agent should decide what kind of preservation is appropriate:

- result
- decision
- reusable knowledge
- memory
- principle
- pattern
- reflection
- invalidated belief
- released context
- handoff

Ask a short confirmation if the preservation could affect privacy, emotional weight, or future retrieval.

After saving a meaningful result, the agent should also update work state and continuation state so the Workroot does not show conflicting progress signals.

## Success Criteria

AI Workroot's user experience is working when:

- a non-technical user can begin without reading architecture docs
- the first useful preserved result can happen in minutes
- users do not manually manage internal files
- identity setup is short but meaningful
- users can continue previous work without rebuilding context
- users can ask what tasks exist and get a local summary
- useful results survive outside chat history
- advanced users can still inspect, extend, and improve the system

## What This Is Not

This is not a replacement for the deeper philosophy or architecture.

It is the product experience layer that helps ordinary people reach the value of the philosophy and architecture without needing to learn them first.
