# Indexing Protocol

Use indexes to avoid reading long historical logs by default.

Levels:

- L0 startup index
- L1 active context
- L2 task index
- L3 evidence index
- L4 mind index
- L5 optional acceleration index

Optional databases, vector indexes, and graph indexes must be rebuildable from file sources.

Long-lived indexes should support retrieval temperature:

- hot
- warm
- cold
- archived
- released
- tombstone
- deleted

Agents should prefer hot and warm entries for normal work. Cold and archived entries require explicit relevance. Released, tombstone, and deleted entries must follow the forgetting policy.

Released entries should be indexed separately from normal memory so agents can avoid surfacing them during default retrieval.

`tombstone` entries are intentional memorial markers, not normal memory.

`deleted` release entries may be absent from the index, or represented only by a minimal deletion marker with no painful detail.

Full rebuild must remain possible even after future incremental indexes are added.
