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
| root `AGENTS.md` / `CLAUDE.md` | `agent/` + resources templates | Native Agent Entry templates | rename | Root files generated locally and ignored, not tracked. |
| `task_registry.csv` | `core/work.py`, storage schema | Task | preserve | Task status/kind/process level preserved. |
| `process_level=L0/L1/L2` | `core/work.py` | TaskProcessLevel | preserve | L0/L1/L2 semantics documented and tested. |
| task kind values | `core/work.py` | TaskKind | preserve | TaskKind behavior documented and tested. |
| decomposition heuristics | `core/work.py` | TaskDecompositionPolicy | preserve | Large work can request decomposition without exposing DDD internals. |
| owner/scope hints | `core/work.py` + `core/common.py` | OwnerScope / Visibility | preserve | Personal-first behavior remains explicit. |
| quick/session/daily tasks | `core/work.py` | TaskKind=session | preserve | Session task does not automatically publish assets. |
| long-running/project task | `core/work.py` | TaskKind=project | preserve | TaskDecompositionPolicy exists. |
| `run_registry.csv` | `core/work.py` | AgentRun | preserve | AgentRun can be recorded and related to Task. |
| `action_registry.csv` | `core/work.py` | WorkAction | preserve | Actions keep type/risk/evidence fields. |
| action type values | `core/work.py` | ActionType | preserve | Action type validation exists. |
| risk labels | `core/common.py` + `core/work.py` | RiskLevel | preserve | Risk metadata remains available for diagnostics. |
| `checkpoint_registry.csv` | `core/work.py` | WorkCheckpoint | preserve | Checkpoints can be recorded and recalled. |
| `retrieval_card_registry.csv` | `core/work.py` + `indexing/` | RetrievalCard | preserve | Retrieval cards mapped to retrieval/index records. |
| `invalidation_registry.csv` | `core/work.py` / `core/assets.py` | InvalidationRecord | preserve | Invalidation affects relationships/assets/context policy. |
| `artifact_registry.csv` | `core/assets.py` | Asset | merge | Artifact becomes Asset. |
| `decision_registry.csv` | `core/assets.py` | Asset(type=decision) | merge | No top-level Decision domain. |
| `mind_registry.csv` | `core/assets.py` + `core/release.py` | Asset subtypes / Release Control | merge | No formal Mind/Memory terms. |
| `forgetting-policy` | `core/release.py` | ReleasePolicy / Tombstone / Redaction / DeletionRecord | rename | Tombstone is first-class; redaction/deletion protected. |
| tombstone entries | `core/release.py` | Tombstone | preserve | Entity named Tombstone, not TombstoneMarker. |
| released/deleted/redacted records | `core/release.py` | ReleaseRecord / DeletionRecord / Redaction | preserve | Derived indexes must not leak deleted/redacted content. |
| `link_registry.csv` | `core/relationships.py` | RelationshipEdge | rename | Relationship Network replaces Graph domain wording. |
| SQLite `graph_nodes`/`graph_edges` | `storage/sqlite` + `core/relationships.py` | relationship nodes/edges | rename | Business docs use Relationship Network. |
| `global-index/workroots.index.jsonl` | `indexing/global_indexes.py` | GlobalWorkrootIndex | preserve | Environment scope index exists. |
| `global-index/tasks.index.jsonl` | `indexing/global_indexes.py` | GlobalTaskIndex | preserve | Global task navigation index is supported. |
| `global-index/assets.index.jsonl` | `indexing/global_indexes.py` | GlobalAssetIndex | preserve | Asset metadata can be queried globally. |
| `knowledge.index.jsonl` | `indexing/global_indexes.py` | Asset index filtered by type | merge | Knowledge is Asset subtype. |
| `decisions.index.jsonl` | `indexing/global_indexes.py` | Asset index filtered by type=decision | merge | Decision is Asset subtype. |
| `AI_WORKROOT_HOME/config.json` | `core/environment.py` + storage | EnvironmentConfig | preserve | Environment config remains canonical. |
| `registry/workroots.jsonl` | storage + runtime | WorkrootRegistry / WorkrootRegistration | preserve | Registry writes are locked and tested. |
| `registry/directory-bindings.jsonl` | storage + runtime | WorkrootDirectoryBinding | preserve | Duplicate directory binding rejected. |
| `registry/aliases.jsonl` | storage + runtime | WorkrootAlias | preserve | Alias rows preserved or explicitly migrated. |
| `registry/relationships.jsonl` | storage + runtime | WorkrootRelationship | preserve | Cross-Workroot management relationships preserved. |
| registry lock | storage | registry lock | preserve | Concurrent init/bootstrap safe. |
| preferences/policy files | `core/environment.py` + storage | GlobalPreferences / GlobalPolicyDefaults | rename | No global user profile body store. |
| global cache DB | storage/indexing | GlobalCacheState | preserve | Global cache is not knowledge. |
| environment migrations | storage | EnvironmentMigrationState | preserve | Migration records retained. |
| FTS indexed files/chunks | `indexing/fts.py` | AssetTextIndex / FTS provider | preserve | FTS works locally; no vector/remote dependency. |
| Context Candidates | `indexing/candidates.py` | ContextCandidateIndex | preserve | Candidate is read model, not Asset. |
| Context Guide Builder | `core/context.py` + `runtime/context.py` | Context Control | rename | CLI remains `workroot context`. |
| Context Package history | `core/context.py` | ContextPackage | preserve | Not user asset by default. |
| Debug Trace | `core/context.py` + `core/health.py` | ContextTrace | preserve | Not user asset by default. |
| Doctor | `core/health.py` + `runtime/doctor.py` | System Health | preserve | Doctor read-only by default. |
| schema migrations | `storage/sqlite/migrations.py` | MigrationRecord | preserve | Migration state is recorded. |
| capability registry | `core/extensions.py` | Capability | defer | Boundary preserved, full plugin system deferred. |
| skill registry | `core/extensions.py` | Skill | defer | Boundary preserved. |
| agent adapters | `core/extensions.py` + `agent/` | AgentAdapter | defer | Boundary preserved. |
| storage extensions | `core/extensions.py` + contracts | StorageDriver | defer | Boundary preserved. |
| retrieval extensions | `core/extensions.py` + contracts | RetrievalDriver | defer | Boundary preserved. |
| MCP interface | `core/extensions.py` + `agent/` | McpBridge | defer | Boundary preserved. |
| permission hints | `core/agent.py` / contracts | PermissionHint | preserve | Agent and safety specs retain permission rules. |
| storage-policy | `core/health.py` + storage specs | StoragePolicy | preserve | Canonical vs derived stores documented. |
| export/import interface | extensions/system health | ExportImportDriver / future manifest | defer | Boundary documented, not fully implemented. |
| bootstrap-dev | `runtime/bootstrap.py` + `agent/` | bootstrap-dev dogfood | preserve | No commit/tag/push; local entries ignored. |
| install scripts | `install/` | user installation | preserve | Moved from scripts to install. |
| `scripts/*.py` product logic | `src/ai_workroot/*` | core/runtime/storage/indexing/agent/cli | rename | Scripts become wrappers/dev tools only. |

Codex must update this matrix if it discovers additional legacy capabilities. New discoveries must not be silently dropped.
