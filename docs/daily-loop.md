# Daily Loop

AI Workroot is not only a structure. It is a daily rhythm for working with AI without losing continuity.

The loop is simple:

```text
orient -> choose -> work -> preserve -> promote -> release -> handoff
```

Users do not need to think about every step. AI agents should quietly help keep the loop alive.

## 1. Orient

Start by understanding the subject and current state.

Ask:

- Who or what does this Workroot serve?
- What is active now?
- Is there an active task or handoff?
- What matters most in this moment?

Use:

- `space/profile/`
- `.workroot/runtime/context/current.md`
- `.workroot/runtime/context/handoff.md`
- `space/work/continue.md`
- relevant registry rows

## 2. Choose

Decide what kind of work this is.

It may be:

- a quick question
- an inbox item
- tracked work
- recurring work
- a project
- a reflection
- knowledge or memory maintenance

Not every thought needs to become tracked work. But work with a goal, expected result, or future value should usually be organized by the AI agent behind the scenes.

## 3. Work

Do the work with AI.

Keep the user experience simple:

- clarify the goal
- take action
- produce a result
- make decisions explicit
- keep the next step visible

The user should focus on the work. The agent should maintain the structure.

## 4. Preserve

When something matters, write it into the Workroot.

Preserve:

- task state
- decisions
- outputs
- useful evidence
- handoff context
- links between related objects

Do not leave durable context only in chat.

## 5. Promote

Turn useful results into durable Mind entries when they should help future work.

Promote:

- experience into `space/mind/memory/`
- reusable understanding into `space/mind/knowledge/`
- operating commitments into `space/mind/principles/`
- important choices into `space/mind/decisions/`
- repeated signals into `space/mind/patterns/`
- deeper reviews into `space/mind/reflections/`
- obsolete beliefs into `space/mind/invalidated/`

Promotion is how work becomes growth.

## 6. Release

After the useful lesson is preserved, some old context may no longer need to remain active.

Release can mean:

- keep it quiet
- archive it
- keep a small tombstone
- redact painful or sensitive detail
- delete it by explicit user choice

Release should not erase responsibility. It should keep the lesson while letting unnecessary pain leave normal recall.

## 7. Handoff

Before ending a session, leave a small continuation path.

Update:

- active task `brief.md`
- active task `todo.md`
- active task `decisions.md`
- active task `handoff.md`
- `.workroot/runtime/context/handoff.md`
- `space/work/continue.md`
- relevant registries

The next agent should not need to reconstruct state from chat history.

The user-facing continuation should stay in plain language. Keep registry details behind the scenes unless the user asks for internal mechanics.

When resuming a complex task, prefer this retrieval order:

```text
current context -> handoff -> task registry row -> task brief -> task handoff -> task index -> latest checkpoint -> latest valid run -> retrieval cards
```

## Meaning And Execution

AI Workroot separates meaning from execution, then reconnects them through reflection and promotion.

- `space/profile/` answers: who is this for?
- `space/mind/principles/` answers: what should guide choices?
- `.workroot/runtime/work/` answers: what are we doing now?
- `space/work/` answers: what should the user see?
- `space/mind/decisions/` answers: what did we choose and why?
- `space/mind/reflections/` answers: what does this experience mean?
- `space/mind/knowledge/` answers: what can be reused later?
- `space/mind/released/` answers: what no longer needs active recall?

This separation matters because doing the wrong thing efficiently is still wrong.

The Workroot should help the subject choose more clearly, act more steadily, learn more deeply, and continue tomorrow.
