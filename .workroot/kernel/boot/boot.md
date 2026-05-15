# AI Workroot Boot

This is the compact startup law for AI agents.

## Identity Gate

Before formal durable work begins, confirm that `space/profile/` defines who or what this Workroot serves.

If identity is missing or too generic, ask only the missing setup questions, save the answer in `space/profile/`, then continue.

For a pure greeting, do not trigger the identity gate. Greet briefly and invite the user to say what they want help with.

When speaking to ordinary users, translate the internal identity gate into usage direction:

- what the user does
- what they mainly want help with
- how the AI should collaborate

Avoid asking "who does this workspace represent?" unless the user is already comfortable with the workspace concept.

Before asking a setup question, use a simple usage-direction frame:

```text
Tell me what you do and what you mainly want help with.
Then I can fit your work better and we can start the first real thing.
```

For a lightweight usage-direction update, such as a role label or collaboration preference, avoid full setup:

- read at most the visible profile file if needed
- write at most the visible profile file unless the user explicitly provides roles, values, preferences, or team rules
- do not scan the project
- do not narrate the internal read/write
- confirm the new collaboration direction in one short reply and ask what to do first

## User Experience

Keep the user experience simple:

```text
user says what they want -> AI helps -> useful result is preserved -> future work can continue
```

Do not require ordinary users to understand `.workroot/`, registries, schemas, indexes, task folders, or context budgets before useful work starts.

Do not expose internal file names, storage paths, registry names, or protocol terms in ordinary-user replies unless the user asks for implementation details.

Do not use "identity", "profile", "kernel", "runtime", "registry", or "workspace represents" as ordinary-user onboarding language. Prefer "what you do", "what you want help with", and "how I should work with you".

Respond in the language the user is currently using. If the user explicitly requests a language, use that language. Keep repository docs and machine-readable keys in English.

## Context Budget

Load only the smallest useful context by default:

- root agent entrypoint
- human start guide
- this boot file
- concise profile files
- current context and handoff
- relevant registry rows when needed

For greetings and short chat, load nothing beyond the already-read startup instructions.

For lightweight usage-direction updates, load at most concise profile content. Do not load roles, values, preferences, runtime context, handoff, registries, or docs unless the user asks or the update requires conflict resolution.

Do not load old scratch files, archives, generated databases, caches, released context, tombstones, or extension details by default.

When the user asks what tasks have been done before, read local task history and summarize what is available. Do not rely only on chat memory.

## Work And Preservation

For goal-oriented work, create or update internal work records under `.workroot/runtime/work/` without asking the user to manage them.

User-visible outputs belong in `space/work/`.

Reusable knowledge, memory, principles, decisions, patterns, invalidations, released context, and tombstones belong in `space/mind/`.

## Extension Loading

Extensions are never startup context unless the boot contract explicitly says so.

Load extension details only when the active task needs them, the user asks for them, or a registry/manifest makes them relevant.

## Sensitive Actions

Ask concise confirmation before sensitive, destructive, networked, secret-related, external-account, durable-memory, or kernel-writing actions.

Generated stores are rebuildable accelerators. They must not become the only source of durable truth.
