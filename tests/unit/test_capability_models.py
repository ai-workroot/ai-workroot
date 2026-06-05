from __future__ import annotations

import unittest

from ai_workroot.capabilities.assets.model import Asset, AssetPublication, AssetSurface
from ai_workroot.capabilities.context.model import ContextBudget
from ai_workroot.shared.extensions import Capability
from ai_workroot.capabilities.relationships.model import RelationshipEdge, RelationshipEvidence, SourceRef
from ai_workroot.capabilities.release.model import DeletionRecord, Redaction, ReleaseTargetRef, Tombstone
from ai_workroot.capabilities.retrieval.model import IndexManifest
from ai_workroot.capabilities.work.model import Task


class CoreModelsTest(unittest.TestCase):
    def test_task_close_validates_transition(self) -> None:
        task = Task(task_id="task_1", title="Ship package skeleton", status="active")

        self.assertTrue(task.can_transition_to("closed"))
        self.assertTrue(task.can_transition_to("archived"))
        task.close()

        self.assertEqual(task.status, "closed")
        self.assertFalse(task.can_transition_to("active"))
        self.assertTrue(task.can_transition_to("archived"))

    def test_asset_publish_records_surface_and_target(self) -> None:
        asset = Asset(asset_id="asset_1", workroot_id="wr_demo", asset_type="spec", title="Spec")
        surface = AssetSurface(
            surface_id="surface_docs",
            workroot_id="wr_demo",
            path="docs/specs",
            surface_type="project-native",
            allowed_asset_types=("spec", "adr"),
            git_policy="tracked",
            created_by="codex",
        )

        publication = asset.publish(surface, "docs/specs/001-demo.spec.md", published_by="codex")

        self.assertIsInstance(publication, AssetPublication)
        self.assertEqual(asset.publication_status, "published")
        self.assertEqual(asset.surface_id, "surface_docs")
        self.assertEqual(asset.current_path, "docs/specs/001-demo.spec.md")

    def test_asset_mark_missing_preserves_previous_path(self) -> None:
        asset = Asset(
            asset_id="asset_1",
            workroot_id="wr_demo",
            asset_type="code",
            title="Module",
            current_path="src/module.py",
        )

        asset.mark_missing("2026-05-20T00:00:00Z")

        self.assertEqual(asset.lifecycle_status, "missing")
        self.assertEqual(asset.current_path, "src/module.py")
        self.assertEqual(asset.missing_since, "2026-05-20T00:00:00Z")

    def test_tombstone_allows_explicit_review_without_protecting_content(self) -> None:
        target = ReleaseTargetRef(target_type="task", target_id="task_1", workroot_id="wr_demo")
        tombstone = Tombstone(
            tombstone_id="tomb_1",
            workroot_id="wr_demo",
            target_ref=target,
            title="Old approach",
            symbolic_note="Remember why this was retired.",
        )

        self.assertTrue(tombstone.allows_explicit_review())
        self.assertFalse(tombstone.strictly_protects_content())

    def test_redaction_and_deletion_strictly_protect_content(self) -> None:
        target = ReleaseTargetRef(target_type="asset", target_id="asset_1", workroot_id="wr_demo")

        redaction = Redaction(
            redaction_id="red_1",
            workroot_id="wr_demo",
            target_ref=target,
            redacted_fields=("summary", "body"),
            redaction_reason="sensitive",
        )
        deletion = DeletionRecord(
            deletion_id="del_1",
            workroot_id="wr_demo",
            target_ref=target,
            minimum_audit_note="deleted by request",
        )

        self.assertTrue(redaction.strictly_protects_content())
        self.assertTrue(deletion.strictly_protects_content())
        self.assertNotIn("asset_1", deletion.minimum_audit_note)

    def test_relationship_edge_attach_evidence(self) -> None:
        edge = RelationshipEdge(
            edge_id="edge_1",
            workroot_id="wr_demo",
            from_node_id="task_1",
            to_node_id="asset_1",
            relationship_type="produces",
            created_by="codex",
        )
        evidence = RelationshipEvidence(
            evidence_id="ev_1",
            edge_id="edge_1",
            evidence_type="source",
            source_ref=SourceRef(source_type="file", source_id="docs/specs/001-demo.spec.md"),
        )

        edge.attach_evidence(evidence)

        self.assertEqual(edge.evidence, (evidence,))

    def test_relationship_edge_rejects_evidence_for_other_edge(self) -> None:
        edge = RelationshipEdge(
            edge_id="edge_1",
            workroot_id="wr_demo",
            from_node_id="task_1",
            to_node_id="asset_1",
            relationship_type="produces",
            created_by="codex",
        )
        evidence = RelationshipEvidence(
            evidence_id="ev_1",
            edge_id="edge_2",
            evidence_type="source",
            source_ref=SourceRef(source_type="file", source_id="README.md"),
        )

        with self.assertRaises(ValueError):
            edge.attach_evidence(evidence)

    def test_index_manifest_staleness(self) -> None:
        manifest = IndexManifest(
            index_id="idx_1", index_kind="fts", source_high_watermark="10", built_high_watermark="9"
        )

        self.assertTrue(manifest.is_stale())

        manifest.mark_built("10")
        self.assertFalse(manifest.is_stale())

    def test_context_budget_requires_trim_and_final_fallback(self) -> None:
        budget = ContextBudget(target_tokens=100, hard_token_limit=120)

        self.assertTrue(budget.requires_trim(121))
        self.assertFalse(budget.requires_trim(120))
        self.assertEqual(budget.final_fallback("x" * 1000), "x" * 120)

    def test_core_extensions_keeps_stable_capability_concept_only(self) -> None:
        import ai_workroot.shared.extensions as extensions

        capability = Capability(capability_id="cap_demo", name="Demo")

        self.assertEqual(capability.status, "reserved")
        self.assertFalse(hasattr(extensions, "manifest"))
        self.assertFalse(hasattr(extensions, "BATCH_OPERATIONS"))
        self.assertFalse(hasattr(extensions, "legacy_manifest"))


if __name__ == "__main__":
    unittest.main()
