# AI Workroot Boot

This is the compact startup law for AI agents.

## Identity Gate

Before formal durable work begins, confirm that `space/profile/` defines who or what this Workroot serves.

If identity is missing or too generic, ask only the missing setup questions, save the answer in `space/profile/`, then continue.

## User Experience

Keep the user experience simple:

```text
user says what they want -> AI helps -> useful result is preserved -> future work can continue
```

Do not require ordinary users to understand `.workroot/`, registries, schemas, indexes, task folders, or context budgets before useful work starts.

Respond in the language the user is currently using. If the user explicitly requests a language, use that language. Keep repository docs and machine-readable keys in English.

## Context Budget

Load only the smallest useful context by default:

- root agent entrypoint
- human start guide
- this boot file
- concise profile files
- current context and handoff
- relevant registry rows when needed

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
