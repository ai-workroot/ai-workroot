# Active Authoring Surfaces

0.9.530 keeps the primary authoring implementation inside `src/ai_workroot/`.
The current milestone exposes these surfaces as package-owned runtime APIs rather than broad user-facing CLI groups.

## Runtime APIs

Use these active runtime modules for new Clean Workroot implementation work:

| Domain | Runtime module | Active entry points | Notes |
|---|---|---|---|
| Work | `ai_workroot.runtime.work` | `create_task`, `record_agent_run`, `record_work_action`, `create_checkpoint`, `create_handoff`, `record_invalidation` | Writes active Work records and index invalidations. |
| Asset | `ai_workroot.runtime.assets` | `create_internal_asset`, `record_asset_publication`, `publish_asset_to_surface`, `mark_asset_missing`, `query_assets` | `record_asset_publication` is metadata-only. `publish_asset_to_surface` is the explicit file-writing operation. |
| Release Control | `ai_workroot.runtime.release` | `create_release_record`, `create_tombstone`, `create_redaction`, `create_deletion_record`, `resolve_release_state_for_target` | Strict release levels sanitize derived indexes and invalidate affected retrieval surfaces. |
| Relationship Network | `ai_workroot.runtime.relationships` | `create_relationship_node`, `create_relationship_edge`, `attach_relationship_evidence`, `query_relationships` | Writes relationship records and invalidates relationship traversal projections. |
| Retrieval & Index Control | `ai_workroot.indexing.global_indexes` | `refresh_global_workroot_index`, `refresh_global_task_index`, `refresh_global_asset_index`, `refresh_global_time_index` | Global indexes are navigation/index surfaces, not global knowledge stores. |
| Context Control | `ai_workroot.runtime.context` | `build_context_package` | Local-first context rendering with release-aware filtering, mode plans, trace, FTS, relationship signals, and ContextRecallHint support. |
| System Health | `ai_workroot.runtime.doctor` | `run_doctor`, `run_release_doctor` | Read-only health checks for Clean Workroot state and release surface. |

## CLI Status

The Clean Workroot user CLI remains intentionally small:

```text
workroot init
workroot list
workroot status
workroot context
workroot doctor
workroot bootstrap-dev
```

The runtime APIs above are the active authoring surface for this milestone. Broad CLI groups such as `workroot task ...`, `workroot asset ...`, `workroot release ...`, `workroot relationship ...`, and `workroot index ...` are deferred until the product workflow requires them.

## Legacy Compatibility

Legacy script and seed commands remain compatibility surfaces. New Clean Workroot product logic should not be added only under `scripts/` or legacy seed modules.

Compatibility paths may call into `src/ai_workroot/` over time, but compatibility removal is a separate phase after active package parity is verified.
