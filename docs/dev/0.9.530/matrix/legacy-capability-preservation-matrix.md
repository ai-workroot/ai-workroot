# Legacy Capability Preservation Matrix

This matrix prevents capability loss during the 0.9.530 reset.

| Old capability / location | New concept | New module | Status | Required acceptance |
|---|---|---|---|---|
| Public Seed root `space/` | Historical Public Seed | docs/history or tests/fixtures | retired/quarantined | Not active root; preserved if useful |
| Public Seed root `.workroot/` | Historical runtime contracts/fixtures | docs/history or tests/fixtures | retired/quarantined | Not active root |
| Root `AGENTS.md` | Native Agent Entry template/local generated entry | agent + templates | renamed | Root file not tracked; template committed |
| Root `CLAUDE.md` | Native Agent Entry template/local generated entry | agent + templates | renamed | Root file not tracked; template committed |
| `task_registry.csv` | Task / Task index | core/work + runtime/work + indexing | preserved; active path started | Task model, runtime, and index tests |
| old task kind conventions | TaskKind | core/work | preserved | TaskKind values and routing tests |
| old task process levels | TaskProcessLevel | core/work | preserved | L0/L1/L2 semantics tested |
| ad hoc task decomposition | TaskDecompositionPolicy | core/work | preserved/renamed | Decomposition decisions tested |
| owner/user/team hints | OwnerScope | core/work + core/common | preserved/renamed | Personal-first scope tested; team collaboration not introduced |
| public/private/internal hints | Visibility | core/common + core/assets | preserved/renamed | Visibility affects release/index/context policy |
| `run_registry.csv` | AgentRun | core/work + runtime/work | preserved; active path started | run persistence/runtime tests |
| `action_registry.csv` | WorkAction | core/work + runtime/work | preserved; active path started | action model/runtime tests |
| action type values | ActionType | core/work | preserved | ActionType validation tests |
| risk labels | RiskLevel | core/common + core/work | preserved/renamed | Risk metadata preserved for diagnostics |
| `artifact_registry.csv` | Asset | core/assets + runtime/assets | merged; active path started | asset model/runtime supports result/generated/source |
| `decision_registry.csv` | Asset(asset_type=decision) | core/assets + runtime/assets | merged; active path started | no top-level decision domain required |
| `retrieval_card_registry.csv` | Context Card / ContextRecallHint, legacy alias RetrievalCard | indexing/providers + core/retrieval | preserved/renamed | context_recall_hints schema and materialization tests; legacy retrieval_cards table retained |
| `checkpoint_registry.csv` | WorkCheckpoint | core/work + runtime/work | preserved; active path started | checkpoint persistence/runtime test |
| `invalidation_registry.csv` | InvalidationRecord | core/work/assets/release + runtime/work | preserved; active path started | invalidation/release runtime test |
| `mind_registry.csv` | Asset + Release Control | core/assets + runtime/assets + core/release | renamed/merged; active path started | no Memory/Mind official term |
| old `knowledge` records | Asset(asset_type=knowledge) | core/assets | merged | no canonical knowledge_items table |
| old `released/tombstone/deleted` | ReleaseRecord / Tombstone / DeletionRecord | core/release + runtime/release | preserved; active path started | redaction/deletion protections and authoring tests |
| `link_registry.csv` | RelationshipEdge | core/relationships + runtime/relationships | renamed; active path started | relationship authoring/query tests |
| graph tables/signals | Relationship Network / traversal projection | relationships + indexing | renamed; active path started | docs use Relationship Network |
| batch transaction journal | OperationTransaction | core/work/runtime | preserved | rollback/transaction record test |
| old batch rollback behavior | OperationTransaction rollback | runtime + storage | preserved | Partial failure rollback tests |
| scripted task recipes | WorkflowRecipe | core/work + runtime | deferred | Recipe boundary documented |
| run validity state | RunValidity | core/work | preserved | AgentRun validity tests |
| session summarize | Work summary / Context Trace / Asset optional | runtime/context/work | preserved/deferred | no loss of summarization capability |
| continue/handoff | Handoff + ContextPackage | core/work + core/context | preserved | handoff tests |
| context-policy | ContextControl policy | core/context | preserved | context mode/budget tests |
| forgetting-policy | Release Control policy | core/release | renamed | tombstone/redaction/deletion tests |
| storage-policy | Storage policy | core/common + storage | preserved | canonical/derived tests |
| permission hints | Agent Interface / Policy | core/agent | preserved | native entry permission tests |
| privacy policy | Release/Asset/Agent policy | core/common/release/assets | preserved | redaction tests |
| globalization policy | Common/time/localization policy | core/common | preserved/deferred | docs mention policy |
| extension policy | Extensions | core/extensions | preserved/deferred | capability boundary exists |
| test policy | System Health / release validation | core/health + docs/specs | preserved | validation docs/tests |
| global-index | Global indexes / GlobalWorkrootIndex | indexing/global_indexes | preserved; Workroot index active | global Workroot index test |
| global task index | GlobalTaskIndex | indexing/global_indexes | preserved; active path started | global task index test |
| global asset index | GlobalAssetIndex | indexing/global_indexes | preserved; active path started | global asset index test |
| global time index | GlobalTimeIndex / WorkrootTimeIndex | indexing/global_indexes + runtime/time | preserved; active path started | `time_events` schema/runtime and global time index tests |
| time-based recall hints | TimeEvent / TimeRange / TemporalScope | core/common + runtime/time | preserved/deferred | value-object and runtime time event tests |
| global-cache | Global cache state | storage/indexing | preserved | not knowledge store |
| `AI_WORKROOT_HOME/config.json` | EnvironmentConfig | core/environment + storage | preserved | Config merge/migration tests |
| `registry/workroots.jsonl` | WorkrootRegistry / WorkrootRegistration | storage + runtime | preserved | Registry write/read tests |
| `registry/directory-bindings.jsonl` | WorkrootDirectoryBinding | storage + runtime | preserved | Duplicate binding tests |
| `registry/aliases.jsonl` | WorkrootAlias | storage + runtime | preserved | Alias validation tests |
| `registry/relationships.jsonl` | WorkrootRelationship | storage + runtime | preserved | Cross-Workroot management relationship tests |
| registry file lock | registry lock | storage | preserved | Concurrent init/bootstrap tests |
| old preferences | GlobalPreferences / operator preferences | core/environment + storage | renamed | No global user profile body store |
| policy defaults | GlobalPolicyDefaults | core/environment + storage | preserved | Defaults merge tests |
| global index catalog | GlobalIndexCatalog | indexing | preserved | Catalog/index health tests |
| `global-cache/global.sqlite` | GlobalCacheState | storage/indexing | preserved | Global cache is not knowledge |
| global migrations | EnvironmentMigrationState | storage | preserved | Global migration records tests |
| per-workroot metadata | `workroots/<id>/workroot.json` | storage + runtime | preserved | Workroot metadata tests |
| capability registry | Capability | core/extensions | preserved/deferred | capability model reserved |
| skill registry | Skill | core/extensions | deferred | Skill boundary documented |
| agent adapter registry | AgentAdapter | core/extensions + agent | deferred | Agent adapter boundary documented |
| storage extension hook | StorageDriver | core/extensions + contracts | deferred | Reserved protocol only |
| retrieval extension hook | RetrievalDriver | core/extensions + contracts | deferred | Reserved protocol only |
| export/import extension hook | ExportImportDriver | core/extensions + contracts | deferred | Reserved protocol only |
| MCP interface | McpBridge | core/extensions/agent | preserved/deferred | reserved docs |
| export/import interface | ExportImportDriver | core/extensions/storage | preserved/deferred | reserved docs |
| install scripts | install/unix + install/windows | install | preserved | parse/smoke test |
| bootstrap-dev | Clean Workroot dogfood | runtime/bootstrap + agent | preserved | idempotent smoke |
| doctor | System Health | core/health + runtime/doctor | preserved | doctor tests |
| SQLite schema | storage schema | storage/sqlite | preserved/rewritten | schema tests |
| FTS indexing | FTS provider | indexing/providers | preserved | FTS tests |
| Context Candidates | Candidate index/read model | indexing + core/retrieval | preserved | candidate tests |
| Debug trace | ContextTrace / Diagnostics Evidence | core/context + health | preserved | trace tests |
