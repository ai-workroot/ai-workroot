from __future__ import annotations

import unittest


class SourceLayoutImportsTest(unittest.TestCase):
    def test_state_modules_expose_managed_state_entrypoints(self) -> None:
        from ai_workroot.state import environment
        from ai_workroot.state import jsonl
        from ai_workroot.state import layout
        from ai_workroot.state import locks
        from ai_workroot.state import migrations
        from ai_workroot.state import registry
        from ai_workroot.state import sqlite

        self.assertTrue(callable(environment.initialize_environment))
        self.assertTrue(callable(jsonl.read_jsonl))
        self.assertTrue(callable(layout.resolve_ai_workroot_home))
        self.assertTrue(callable(locks.file_lock))
        self.assertTrue(callable(migrations.MigrationRunner))
        self.assertTrue(callable(registry.list_workroots))
        self.assertTrue(callable(sqlite.initialize_workroot_sqlite))

    def test_agent_entry_and_diagnostics_modules_expose_entrypoints(self) -> None:
        from ai_workroot.capabilities.system_health import doctor
        from ai_workroot.capabilities.system_health import release_validation
        from ai_workroot.entrypoints.native_agent import native

        self.assertTrue(callable(native.render_native_agent_entry))
        self.assertTrue(callable(doctor.run_doctor))
        self.assertTrue(callable(doctor.run_release_doctor))
        self.assertTrue(callable(release_validation.validate_release_surface))

    def test_capability_modules_expose_runtime_entrypoints(self) -> None:
        from ai_workroot.capabilities.assets import operations as asset_operations
        from ai_workroot.capabilities.context import builder as context_builder
        from ai_workroot.capabilities.handoff import operations as handoff_operations
        from ai_workroot.capabilities.relationships import operations as relationship_operations
        from ai_workroot.capabilities.release import filter as release_filter
        from ai_workroot.capabilities.release import operations as release_operations
        from ai_workroot.capabilities.retrieval import global_indexes
        from ai_workroot.capabilities.retrieval.providers import candidate_provider
        from ai_workroot.capabilities.work import operations as work_operations
        from ai_workroot.capabilities.work import time

        self.assertTrue(callable(asset_operations.create_internal_asset))
        self.assertTrue(callable(context_builder.build_context_package))
        self.assertTrue(callable(handoff_operations.create_handoff))
        self.assertTrue(callable(relationship_operations.create_relationship_node))
        self.assertTrue(callable(release_filter.load_release_filter_report))
        self.assertTrue(callable(release_operations.create_release_record))
        self.assertTrue(callable(global_indexes.refresh_global_workroot_index))
        self.assertTrue(callable(candidate_provider.upsert_context_candidate))
        self.assertTrue(callable(work_operations.create_task))
        self.assertTrue(callable(time.record_time_event))

    def test_shared_and_local_models_are_importable(self) -> None:
        from ai_workroot.capabilities.assets import model as assets_model
        from ai_workroot.capabilities.context import model as context_model
        from ai_workroot.capabilities.handoff import model as handoff_model
        from ai_workroot.capabilities.relationships import model as relationships_model
        from ai_workroot.capabilities.release import model as release_model
        from ai_workroot.capabilities.retrieval import model as retrieval_model
        from ai_workroot.capabilities.system_health import model as system_health_model
        from ai_workroot.capabilities.work import model as work_model
        from ai_workroot.entrypoints.native_agent import model as native_agent_model
        from ai_workroot.shared import extensions
        from ai_workroot.state import model as state_model

        self.assertTrue(callable(native_agent_model.PermissionHint))
        self.assertTrue(callable(assets_model.Asset))
        self.assertTrue(callable(context_model.ContextBudget))
        self.assertTrue(callable(system_health_model.HealthCheckResult))
        self.assertTrue(callable(handoff_model.HandoffPackage))
        self.assertTrue(callable(relationships_model.RelationshipEdge))
        self.assertTrue(callable(release_model.ReleaseTargetRef))
        self.assertTrue(callable(retrieval_model.IndexManifest))
        self.assertTrue(callable(extensions.Capability))
        self.assertTrue(callable(state_model.WorkrootEnvironment))
        self.assertTrue(callable(work_model.Task))


if __name__ == "__main__":
    unittest.main()
