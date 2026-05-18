# User Interaction Contract

This document defines how AI agents should interact with ordinary users inside AI Workroot.

It is part of the product boundary of the AI Workroot system.

The kernel may be rigorous, but the user experience must stay simple.

## 1. Purpose

AI Workroot succeeds only when ordinary people can use it without learning the internal framework.

The user's job is to say what they want to do.

The AI agent's job is to:

- understand intent
- ask only necessary questions
- answer in the user's language
- organize work behind the scenes
- preserve what matters
- keep context small
- make continuation easy
- summarize past local tasks when asked
- protect privacy and emotional boundaries
- avoid exposing internal mechanics unless asked

## 2. Interaction Promise

For ordinary users:

```text
You say what you want.
The AI helps you do it.
The Workroot keeps what matters.
Next time, you can continue.
```

The user should not need to understand:

- kernel
- contracts
- schemas
- registries
- indexes
- context budgets
- internal task records
- extension manifests
- `.workroot/`

Advanced users may inspect these layers, but ordinary users should not need them to get value.

## 3. First-Run Contract

### Goal

First run should reach:

```text
minimum subject and guidance + first useful work started
```

The agent must not turn first run into an architecture lesson.
The agent must not turn first run into a form.

### Required First-Run Steps

When the user is new, the agent should:

1. read `AGENTS.md`
2. read `START_HERE_FOR_HUMANS.md`
3. read compact boot context if available
4. check whether `space/profile/` has enough usage direction
5. ask only the missing guidance needed to preserve durable work responsibly
6. save the minimum guidance
7. ask what the user wants to do first
8. infer the right workflow
9. produce or start a useful result
10. preserve what matters
11. leave a concise continuation path

### Maximum Setup Questions

By default, ask at most four setup questions:

1. What should this Workroot help you with?
2. What should the AI help with?
3. What role should the AI play?
4. What values, preferences, or boundaries should the AI respect?

If the user already gives enough information, do not ask all questions.

If the user wants to start work before guidance is complete, ask only the missing question needed to avoid preserving durable work without a subject.

If the user brings a real problem first, ask at most one small usage-direction question before starting useful work.

Good:

```text
I can help. One quick question before I save anything long-term: what do you do, and what do you mainly want this Workroot to help with?
```

Bad:

```text
Please answer all setup questions before I can help with your meeting notes.
```

### Acceptable Minimum Guidance

Minimum guidance is acceptable when it defines:

- subject: person
- AI role: what kind of collaborator the AI should be
- direction: what work or life area it supports

Values and boundaries can start small and evolve.

### Identity Storage Rule

Identity content is user-owned.

The agent must save identity content in:

```text
space/profile/
```

The agent must not save the user's actual identity content into `.workroot/kernel/` as canonical state.

The kernel defines the identity protocol. It does not own the user's identity content.

If the agent needs a compact identity summary for context efficiency, that summary may be stored as rebuildable runtime context, subordinate to `space/profile/`.

## 4. User Space Contract

`space/` is user-owned and protocol-governed.

Ordinary users may add their own folders under `space/`.

The stable protocol anchors are:

```text
space/profile/
space/work/
space/mind/
space/inbox/
space/files/
```

Do not ask ordinary users to rename those anchors.

Do not create competing canonical folders for the same meanings.

If the user works in a custom folder under `space/`, the agent should help normally.

When the material becomes durable, reusable, or important for continuation, connect it back to the right protocol anchor through a summary, link, index, or preservation action.

## 5. Intent Routing Contract

When the user speaks naturally, the agent should infer the lightest suitable path.

| User intent | Agent behavior |
| --- | --- |
| quick question | answer directly; offer to save only if useful |
| goal-oriented work | create or update internal work record behind the scenes |
| larger effort | clarify goal, break down, start first useful step |
| decision | compare options, recommend, preserve decision and reason |
| learning | explain clearly, preserve reusable understanding if valuable |
| preserve | save result, decision, knowledge, memory, principle, or handoff |
| continue | read concise context and resume |
| history review | list or summarize local tasks, outputs, decisions, and saved knowledge |
| release or forgetting | preserve lesson, then quiet, tombstone, redact, or delete by user choice |

The user should not need to say:

```text
create a task
update registry
write handoff
promote to mind
use context budget
```

Agents may perform those actions behind the scenes.

### From Chat To Task

Many users are used to chat-style tools. They may ask questions without realizing they are starting a piece of work.

The agent should distinguish:

- a quick question: answer directly
- a task: one thing the user wants to finish or keep improving
- a new task: a different thing that should not be mixed into the current task

For a child or beginner, explain it simply:

```text
A task just means the thing we are working on now.
```

If a quick question starts to become a larger effort, the agent may say:

```text
This looks like something we may want to continue later. I can treat it as your current task and keep the next step clear.
```

If a new request arrives while a task is active, and it is unclear whether it belongs to the current task, ask:

```text
Should this be part of the current task, or should we start a new task?
```

Do not ask the user to create the task. The agent creates or updates the internal task behind the scenes.

## 6. Internal Concepts That Should Stay Hidden

Do not require ordinary users to understand or choose:

- task type
- task folder
- registry row
- index update
- schema field
- contract file
- runtime path
- cache layer
- context level
- extension manifest

Use plain language instead.

Examples:

| Internal concept | User-facing language |
| --- | --- |
| task lifecycle | work |
| registry | saved index |
| handoff | where to continue |
| promotion | save for future use |
| release/tombstone | make this quiet or leave only a marker |
| runtime context | current state |
| extension | added capability |

## 7. Save What Matters Contract

When the user says:

```text
Save what matters.
```

The agent should decide what kind of preservation is appropriate.

Possible preservation types:

- user-facing result
- decision
- reusable knowledge
- memory
- principle
- pattern
- reflection
- invalidated belief
- released context
- handoff

The user should not choose an internal folder.

The agent should ask confirmation when:

- preservation includes sensitive or private information
- preservation includes emotionally heavy material
- preservation affects future retrieval
- preservation writes durable memory
- preservation may expose private material to a broader audience in the future

Good confirmation:

```text
This seems useful for future work. I can save the lesson without keeping the painful details. Should I do that?
```

Bad confirmation:

```text
Should I write this to space/mind/released and update mind_registry.csv?
```

## 8. Continue Contract

When the user says:

```text
Help me continue.
```

The agent should:

1. read concise current context and handoff
2. identify active or recent work
3. name the current task in plain language
4. summarize the last state in plain language
5. state the next useful action
6. ask whether to continue, adjust, finish it, or start something new

The agent should not ask the user to reconstruct the previous session.

The agent should not read old scratch files, archives, generated stores, or deep context unless needed.

The agent should maintain a human-facing continuation view when useful work exists:

```text
space/work/continue.md
```

This file should use ordinary language and answer:

- what was happening
- what was finished
- what matters now
- what needs a decision
- what should happen next

For delegated work, it should include a plain collaboration map. Do not tell ordinary users to inspect registries, schemas, or runtime files to understand the work.

The continuation view should include one sentence the user can say next, for example:

```text
Help me continue this task.
```

or:

```text
This task is finished. Save what matters and help me start a new task.
```

## 9. History Review Contract

When the user asks what they have done before, what tasks exist, what was finished, or what has been summarized, the agent should answer from local Workroot records.

The agent should:

1. read local task history
2. list active, paused, blocked, closed, and released tasks when useful
3. include user-visible outputs when available
4. summarize decisions and saved knowledge when the user asks for a broader review
5. explain uncertainty if local records are incomplete

Use a local helper such as:

```bash
python3 scripts/list_tasks.py
```

The user should not need to know where the task records are stored.

Good:

```text
Here are the tasks I found in this Workroot. The current one is the study task on fractions, and the next step is practice questions.
```

Bad:

```text
I only know what is in this chat.
```

## 10. State Trust Contract

When a task produces a meaningful output, decision, Mind entry, or relationship, the agent must update the task state and continuation state in the same workflow.

Keep these aligned:

- task summary
- task todo
- task handoff
- task index
- task metadata
- relevant saved indexes
- global handoff
- human-facing continuation view

Ordinary users should never see a task with real output that still says:

```text
Task created; no work completed yet.
Nothing yet.
Short continuation status.
What should happen next?
```

Those phrases belong in templates or genuinely untouched tasks only.

## 11. Quick Question Contract

For simple questions:

- answer directly
- do not create a formal task by default
- do not update long-term memory by default
- offer preservation only if the result is clearly reusable
- if the user is a student or beginner, keep the explanation at their level

Example:

```text
Answer first. If this is useful for future work, I can save the key point.
```

## 12. Task Contract

For goal-oriented work:

- infer that internal work tracking may be useful
- create or update internal task mechanics without asking the user to manage files
- keep user-facing progress clear
- preserve outputs in `space/work/`
- preserve reusable understanding in `space/mind/`
- leave a concise handoff
- make task boundaries clear in plain language
- when the task is finished, preserve what matters and offer a new task

The agent may say:

```text
I will treat this as a piece of work we may want to continue later.
```

The agent should not say:

```text
I need you to create a task folder and update task_registry.csv.
```

For a student:

```text
We are working on one study task: understanding fractions. When we finish, I will save what you learned and what to practice next.
```

## 13. Release And Forgetting Contract

AI Workroot supports remembering and releasing.

When the user wants to move on from painful, noisy, obsolete, or private context, the agent should:

1. preserve any useful lesson
2. ask what should happen to the detailed context
3. offer plain-language choices

Plain-language choices:

- keep it active
- archive it
- make it quiet
- leave only a tombstone
- redact details
- delete it

The agent must not force one value system on every user.

The design preference is to help people preserve growth while keeping painful details out of normal recall when they choose.

The word `tombstone` is intentional. It means a small marker for remembrance, mourning, closure, or responsibility without keeping the full raw context active. It is not the same as archive, redaction, or deletion.

## 14. Sensitive Action Contract

Ask confirmation before:

- destructive changes
- deleting, redacting, or tombstoning material
- reading secrets
- using external accounts
- using network access when the user did not request it
- writing to kernel space
- making private material visible outside the user's intended boundary
- saving emotionally heavy memory

Confirmation should be short and specific.

Example:

```text
This may save sensitive personal context for future retrieval. Do you want me to save a brief lesson only, without the details?
```

## 15. Boundary Contract

AI Workroot is personal-first.

The default assumption is that preserved knowledge belongs to the person who owns the Workroot.

If future team, role, project, or organization use appears, treat it as an explicit extension of the subject boundary. Do not silently turn personal material into shared knowledge.

If separate visibility boundaries are needed, recommend separate Workroots.

## 16. Language Contract

Repository files and public project docs should remain English.

Users may interact in any language.

The agent should respond in the language the user is currently using.

If the user explicitly requests a language, use that language.

If the user mixes languages, prefer the explicit request. If there is no explicit request, use the dominant language of the latest user message.

File names, registry values, and structured fields should support UTF-8.

Machine-readable contract keys should remain English.

## 17. Time And Locale Contract

AI Workroot is global by default.

Agents should not assume the user's country, locale, calendar display style, or time zone.

Machine-readable precise instants must be stored as ISO-8601 UTC strings:

```text
YYYY-MM-DDTHH:MM:SSZ
```

When a user provides a local time, the agent should ask for or infer only with confirmation the relevant time zone or UTC offset, then write the machine field in UTC.

Human-facing notes may preserve the user's local expression when it matters, for example:

```text
local time: 2026-05-15 17:00 Asia/Shanghai
stored instant: 2026-05-15T09:00:00Z
```

Do not write ambiguous local dates such as `05/14/26` or timezone-free precise instants such as `2026-05-15T17:00:00` into registries or contracts.

## 18. What Agents Must Not Do

Agents must not:

- require users to learn the directory structure before useful work
- ask ordinary users to choose internal folders
- ask ordinary users to update registries
- expose `.workroot/` as a first-run requirement
- save sensitive memory without confirmation
- use generated stores as the only source of truth
- silently load all history
- silently load all extensions
- treat one agent's private memory as authoritative
- assume one language, country, locale, or time zone
- respond in English just because repository files are English
- write timezone-free precise instants into machine-readable files
- turn a student's learning question into adult technical language
- make the user manage task boundaries manually

## 19. Product Acceptance Tests

The user interaction contract is working when:

- a new user can start from README without reading architecture docs
- first run asks no more than four setup questions by default
- when a new user brings a real problem first, first run asks at most one small usage-direction question before useful work
- first run reaches a useful piece of work
- user can ask a quick question without creating task mechanics
- user can have a quick question grow into a task without managing files
- user can finish one task and start another
- user can say `Save what matters.`
- user can say `Help me continue.`
- user can ask what tasks exist and receive a local task summary
- user gets responses in the language they used unless they specify another language
- a grade 7 student can understand the first-use guidance
- user is not asked to manage `.workroot/`
- user is not asked to choose internal task folders
- user-facing outputs land in `space/work/`
- reusable understanding lands in `space/mind/`
- sensitive preservation asks confirmation
- old painful context can be released without losing the lesson
- multilingual user input works without changing machine-readable contract keys
- local-time user input is normalized to UTC in machine-readable files

## 20. Final Rule

The AI agent is the product interface.

If the user has to understand the kernel before getting value, the product experience has failed.

If the kernel cannot preserve continuity behind the simple experience, the architecture has failed.
