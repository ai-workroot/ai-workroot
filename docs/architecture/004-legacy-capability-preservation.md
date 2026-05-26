# Legacy Capability Preservation Matrix

This matrix prevents regression during the architecture reset. Codex must not delete a preserved capability without mapping it into the new structure and tests.

Status values:

- `preserve`: keep capability with same semantics.
- `rename`: keep capability under a better name.
- `merge`: merge into a broader concept.
- `retire`: intentionally remove as active architecture.
- `defer`: reserve boundary but do not fully implement now.

| Old capability/location | New module | New concept | Status | Acceptance requirement |
|---|---|---|---|---|
| `space/` active layout | docs/history or fixtures | Public Seed history | retire | Root active tree no longer contains tracked `space/`. |
| `.workroot/` active runtime | docs/history or fixtures | Public Seed history | retire | Root active tree no longer contains tracked `.workroot/`. |
| root `AGENTS.md` / `CLAUDE.md` | `agent_entry/` + `templates/native_agent_entry` | Native Agent Entry templates | rename | Root files generated locally and ignored, not tracked. |
| `task_registry.csv` | `work/model.py`, `state/sqlite.py` | Task | preserve | Task status/kind/process level preserved. |
| `process_level=L0/L1/L2` | `work/model.py` | TaskProcessLevel | preserve | L0/L1/L2 semantics documented and tested. |
| task kind values | `work/model.py` | TaskKind | preserve | TaskKind behavior documented and tested. |
| decomposition heuristics | `work/model.py` | TaskDecompositionPolicy | preserve | Large work can request decomposition without exposing DDD internals. |
| owner/scope hints | capability-local models | OwnerScope / Visibility | preserve | Personal-first behavior remains explicit. |
| quick/session/daily tasks | `work/model.py` | TaskKind=session | preserve | Session task does not automatically publish assets. |
| long-running/project task | `work/model.py` | TaskKind=project | preserve | TaskDecompositionPolicy exists. |
| `run_registry.csv` | `work/model.py` | AgentRun | preserve | AgentRun can be recorded and related to Task. |
| `action_registry.csv` | `work/model.py` | WorkAction | preserve | Actions keep type/risk/evidence fields. |
| action type values | `work/model.py` | ActionType | preserve | Action type validation exists. |
| risk labels | `work/model.py` or owning capability model | RiskLevel | preserve | Risk metadata remains available for diagnostics. |
| `checkpoint_registry.csv` | `work/model.py` | WorkCheckpoint | preserve | Checkpoints can be recorded and recalled. |
| `retrieval_card_registry.csv` | `retrieval/providers/` + `retrieval/model.py` | Context Card / ContextRecallHint | rename | ContextRecallHint is the canonical recall anchor. |
| `invalidation_registry.csv` | `work/model.py` / `assets/model.py` | InvalidationRecord | preserve | Invalidation affects relationships/assets/context policy. |
| `artifact_registry.csv` | `assets/model.py` | Asset | merge | Artifact becomes Asset. |
| `decision_registry.csv` | `assets/model.py` | Asset(type=decision) | merge | No top-level Decision domain. |
| `mind_registry.csv` | `assets/model.py` + `release/model.py` | Asset subtypes / Release Control | merge | No formal Mind/Memory terms. |
| `forgetting-policy` | `release/model.py` | ReleasePolicy / Tombstone / Redaction / DeletionRecord | rename | Tombstone is first-class; redaction/deletion protected. |
| tombstone entries | `release/model.py` | Tombstone | preserve | Entity named Tombstone, not TombstoneMarker. |
| released/deleted/redacted records | `release/model.py` | ReleaseRecord / DeletionRecord / Redaction | preserve | Derived indexes must not leak deleted/redacted content. |
| `link_registry.csv` | `relationships/model.py` | RelationshipEdge | rename | Relationship Network replaces Graph domain wording. |
| SQLite `graph_nodes`/`graph_edges` | `state/sqlite.py` + `relationships/model.py` | relationship nodes/edges | rename | Business docs use Relationship Network. |
| `global-index/workroots.index.jsonl` | `retrieval/global_indexes.py` | GlobalWorkrootIndex | preserve | Environment scope index exists. |
| `global-index/tasks.index.jsonl` | `retrieval/global_indexes.py` | GlobalTaskIndex | preserve | Global task navigation index is supported. |
| `global-index/assets.index.jsonl` | `retrieval/global_indexes.py` | GlobalAssetIndex | preserve | Asset metadata can be queried globally. |
| `knowledge.index.jsonl` | `retrieval/global_indexes.py` | Asset index filtered by type | merge | Knowledge is Asset subtype. |
| `decisions.index.jsonl` | `retrieval/global_indexes.py` | Asset index filtered by type=decision | merge | Decision is Asset subtype. |
| `AI_WORKROOT_HOME/config.json` | `state/model.py` + `state/environment.py` | EnvironmentConfig | preserve | Environment config remains canonical. |
| `registry/workroots.jsonl` | `state/jsonl.py` + `state/registry.py` | WorkrootRegistry / WorkrootRegistration | preserve | Registry writes are locked and tested. |
| `registry/directory-bindings.jsonl` | `state/jsonl.py` + `state/registry.py` | WorkrootDirectoryBinding | preserve | Duplicate directory binding rejected. |
| `registry/aliases.jsonl` | `state/jsonl.py` + `state/registry.py` | WorkrootAlias | preserve | Alias rows preserved or explicitly migrated. |
| `registry/relationships.jsonl` | `state/jsonl.py` + `state/registry.py` | WorkrootRelationship | preserve | Cross-Workroot management relationships preserved. |
| registry lock | `state/locks.py` | registry lock | preserve | Concurrent init/bootstrap safe. |
| preferences/policy files | `state/model.py` + `state/environment.py` | GlobalPreferences / GlobalPolicyDefaults | rename | No global user profile body store. |
| global cache DB | `state/sqlite.py` + `retrieval/` | GlobalCacheState | preserve | Global cache is not knowledge. |
| environment migrations | `state/migrations.py` | EnvironmentMigrationState | preserve | Migration records retained. |
| FTS indexed files/chunks | `retrieval/providers/sqlite_fts.py` | AssetTextIndex / FTS provider | preserve | FTS works locally; no vector/remote dependency. |
| Context Candidates | `retrieval/model.py` | ContextCandidateIndex | preserve | Candidate is read model, not Asset. |
| Context Guide Builder | `context/model.py` + `context/builder.py` | Context Control | rename | CLI remains `workroot context`. |
| Context Package history | `context/model.py` | ContextPackage | preserve | Not user asset by default. |
| Debug Trace | `context/model.py` + `diagnostics/model.py` | ContextTrace | preserve | Not user asset by default. |
| Doctor | `diagnostics/model.py` + `diagnostics/doctor.py` | System Health | preserve | Doctor read-only by default. |
| schema migrations | `state/migrations.py` | MigrationRecord | preserve | Migration state is recorded. |
| capability registry | `shared/extensions.py` | Capability | defer | Boundary preserved, full plugin system deferred. |
| skill registry | `shared/extensions.py` | Skill | defer | Boundary preserved. |
| agent adapters | `shared/extensions.py` + `agent_entry/model.py` | AgentAdapter | defer | Boundary preserved. |
| storage extensions | `shared/extensions.py` + `shared/contracts/` | StorageDriver | defer | Boundary preserved. |
| retrieval extensions | `shared/extensions.py` + `shared/contracts/` | RetrievalDriver | defer | Boundary preserved. |
| MCP interface | `shared/extensions.py` + `agent_entry/model.py` | McpBridge | defer | Boundary preserved. |
| permission hints | `agent_entry/model.py` / `shared/contracts/` | PermissionHint | preserve | Agent and safety specs retain permission rules. |
| storage-policy | `diagnostics/model.py` + state specs | StoragePolicy | preserve | Canonical vs derived stores documented. |
| export/import interface | extensions/system health | ExportImportDriver / future manifest | defer | Boundary documented, not fully implemented. |
| bootstrap-dev | `commands/bootstrap_dev.py` + `agent_entry/native.py` | bootstrap-dev dogfood | preserve | No commit/tag/push; local entries ignored. |
| install scripts | `install/` | user installation | preserve | Moved from scripts to install. |
| `scripts/*.py` product logic | `src/ai_workroot/*` | command and capability packages | rename | Scripts become wrappers/dev tools only. |

Codex must update this matrix if it discovers additional legacy capabilities. New discoveries must not be silently dropped.
