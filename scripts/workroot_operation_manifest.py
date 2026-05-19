"""Agent-facing operation manifest for AI Workroot CLI usage.

The manifest is the operation contract agents should read before normal
Workroot writes. It keeps agents from reverse-engineering workroot_client.py.
"""

from __future__ import annotations

from copy import deepcopy

from workroot_client import (
    MIND_TYPES,
    OWNER_SCOPES,
    PROCESS_LEVELS,
    TASK_STATUSES,
    VISIBILITIES,
)


ACTION_TYPES = [
    "api_call",
    "browser_research",
    "command",
    "database_query",
    "deployment",
    "file_edit",
    "manual_check",
    "model_generation",
    "other",
    "test_run",
]
ARTIFACT_AUDIENCES = ["evidence", "internal", "public", "user"]


def field(type_: str, *, required: bool = False, default: object = "", description: str = "") -> dict[str, object]:
    payload: dict[str, object] = {
        "type": type_,
        "required": required,
        "optional": not required,
    }
    if default != "":
        payload["default"] = default
    if description:
        payload["description"] = description
    return payload


PATH_LIST_DESCRIPTION = "Batch JSON accepts either a string or an array of paths; arrays are stored as semicolon-separated paths."


BATCH_OPERATIONS: dict[str, dict[str, object]] = {
    "task.create": {
        "summary": "Create a task under .workroot/runtime/work/tasks/<task-id>/ and append task_registry.csv.",
        "writes": ["task-local", "task_registry"],
        "fields": {
            "op": field("string", required=True, default="task.create"),
            "title": field("string", required=True),
            "task_id": field("string"),
            "process_level": field("enum", default="L0", description="One of L0, L1, L2."),
            "goal": field("string", default="What are we trying to accomplish?"),
            "why": field("string", default="Why is this worth doing?"),
            "expected": field("string", default="What should exist when this task is done?"),
            "next_action": field("string", default="Define next step"),
            "owner_scope": field("enum", default="personal"),
            "visibility": field("enum", default="internal"),
            "priority": field("string"),
            "created_at": field("instant"),
            "user_visible_output_path": field("path"),
        },
    },
    "task.update": {
        "summary": "Update task-local state. It does not update global continuation.",
        "writes": ["task-local", "task_registry"],
        "fields": {
            "op": field("string", required=True, default="task.update"),
            "task_id": field("string", required=True),
            "status": field("enum", description="One of active, paused, blocked, closed, released."),
            "updated_at": field("instant"),
            "next_action": field("string"),
            "user_visible_output_path": field("path"),
            "brief_current_state": field("string"),
            "brief_latest_result": field("string"),
            "handoff_status": field("string"),
            "handoff_latest_result": field("string"),
            "index_outputs": field("array[path]"),
            "mind_paths": field("array[path]"),
        },
    },
    "run.add": {
        "summary": "Record one execution run for a task.",
        "writes": ["run_registry", "task-local"],
        "fields": {
            "op": field("string", required=True, default="run.add"),
            "task_id": field("string", required=True),
            "run_id": field("string", required=True),
            "title": field("string", required=True),
            "status": field("string", default="active"),
            "validity": field("string"),
            "validity_reason": field("string"),
            "superseded_by": field("string"),
            "started_at": field("instant"),
            "completed_at": field("instant"),
            "output_dir": field("path"),
            "primary_artifact": field("path_or_id"),
            "validation": field("string"),
            "conclusion_preview": field("string"),
        },
    },
    "artifact.add": {
        "summary": "Register an artifact and optionally create the artifact file.",
        "writes": ["artifact_registry", "task-local"],
        "fields": {
            "op": field("string", required=True, default="artifact.add"),
            "artifact_id": field("string", required=True),
            "task_id": field("string", required=True),
            "run_id": field("string"),
            "action_id": field("string"),
            "type": field("string"),
            "path": field("path", required=True),
            "audience": field("enum", default="internal"),
            "status": field("string", default="active"),
            "size": field("string"),
            "checksum": field("string"),
            "created_at": field("instant"),
            "create_file": field("boolean", description="CLI flag outside batch; in batch use content or content_file."),
            "content": field("string", description="Batch can create the file from this content."),
            "content_file": field("path", description="Batch can create the file from this source file."),
            "compute_metadata": field("boolean", default=False),
        },
    },
    "action.add": {
        "summary": "Record a meaningful operation or evidence step.",
        "writes": ["action_registry", "task-local"],
        "fields": {
            "op": field("string", required=True, default="action.add"),
            "task_id": field("string", required=True),
            "action_id": field("string", required=True),
            "run_id": field("string"),
            "type": field("enum"),
            "status": field("string", default="active"),
            "summary": field("string"),
            "tool": field("string"),
            "input_ref": field("path_or_url"),
            "output_ref": field("path_or_url"),
            "approval_ref": field("path_or_url"),
            "risk_level": field("string"),
            "created_at": field("instant"),
        },
    },
    "checkpoint.add": {
        "summary": "Record a continuation checkpoint for a task.",
        "writes": ["checkpoint_registry", "task-local"],
        "fields": {
            "op": field("string", required=True, default="checkpoint.add"),
            "task_id": field("string", required=True),
            "checkpoint_id": field("string", required=True),
            "current_status": field("string", required=True),
            "last_valid_run_id": field("string"),
            "next_action": field("string"),
            "required_context_paths": field("path_list", description=PATH_LIST_DESCRIPTION),
            "created_at": field("instant"),
        },
    },
    "retrieval_card.add": {
        "summary": "Record a small retrieval card for source context.",
        "writes": ["retrieval_card_registry", "task-local"],
        "fields": {
            "op": field("string", required=True, default="retrieval_card.add"),
            "task_id": field("string", required=True),
            "card_id": field("string", required=True),
            "freshness": field("string", default="hot"),
            "source_paths": field("path_list", description=PATH_LIST_DESCRIPTION),
            "created_at": field("instant"),
        },
    },
    "invalidation.add": {
        "summary": "Record a claim/result invalidation for a task.",
        "writes": ["invalidation_registry", "task-local"],
        "fields": {
            "op": field("string", required=True, default="invalidation.add"),
            "task_id": field("string", required=True),
            "invalidation_id": field("string", required=True),
            "run_id": field("string"),
            "artifact_id": field("string"),
            "invalidated_claim": field("string"),
            "reason": field("string"),
            "replacement_ref": field("path_or_id"),
            "path": field("path", description="Optional explicit invalidation record path."),
            "created_at": field("instant"),
        },
    },
    "mind.add": {
        "summary": "Promote reusable memory, knowledge, principle, decision, pattern, reflection, invalidation, release, or tombstone entry.",
        "writes": ["mind_registry", "link_registry", "space/mind", "task-local"],
        "fields": {
            "op": field("string", required=True, default="mind.add"),
            "mind_id": field("string", required=True),
            "title": field("string", required=True),
            "type": field("enum", required=True, description="One of the manifest mind_types."),
            "status": field("string", default="active"),
            "temperature": field("string", default="warm"),
            "privacy_level": field("string", default="internal"),
            "release_level": field("string", default="active"),
            "retrieval_rule": field("string"),
            "summary": field("string"),
            "path": field("path", description="Mind entry path. Prefer this over deprecated source_path."),
            "from_paths": field("array[path]"),
            "from_task_ids": field("array[string]"),
            "source_path": field("path", description="Deprecated alias for path."),
            "set_task_output": field("boolean", default=False),
            "related_task_id": field("string"),
            "replaces_mind_id": field("string"),
            "created_at": field("instant"),
        },
    },
    "session.summarize": {
        "summary": "Write session/global continuation for one or more tasks.",
        "writes": ["space/work/continue.md", ".workroot/runtime/context/current.md", ".workroot/runtime/context/handoff.md"],
        "fields": {
            "op": field("string", required=True, default="session.summarize"),
            "task_ids": field("array[string]", required=True),
            "from_registry": field("boolean", default=False, description="CLI flag outside batch; in batch use explicit task_ids."),
            "summary": field("string", required=True),
            "next_action": field("string", required=True),
        },
    },
}


RECIPES: dict[str, dict[str, object]] = {
    "task-l0-report": {
        "format": "commands",
        "commands": [
            'python3 scripts/workroot_cli.py task create "Simple task" --process-level L0 --id TASK',
            "python3 scripts/workroot_cli.py task complete --process-level L0 --task-id TASK --report-path space/work/reports/report.md --report-content-file report.md",
        ],
    },
    "task-l1-report": {
        "format": "commands",
        "commands": [
            'python3 scripts/workroot_cli.py task create "Report task" --process-level L1 --id TASK',
            "python3 scripts/workroot_cli.py task complete --process-level L1 --task-id TASK --report-path space/work/reports/report.md --report-content-file report.md",
        ],
    },
    "task-l2-evidence": {
        "format": "commands",
        "commands": [
            'python3 scripts/workroot_cli.py task create "Evidence task" --process-level L2 --id TASK',
            "python3 scripts/workroot_cli.py task complete --process-level L2 --task-id TASK --report-path space/work/reports/report.md --report-content-file report.md --checkpoint",
        ],
    },
}


def batch_12_tasks_recipe() -> dict[str, object]:
    operations: list[dict[str, object]] = []
    task_ids: list[str] = []
    for i in range(1, 13):
        task_id = f"batch-demo-{i:02d}"
        task_ids.append(task_id)
        report_path = f"space/work/reports/{task_id}.md"
        operations.extend(
            [
                {
                    "op": "task.create",
                    "title": f"Batch demo task {i:02d}",
                    "task_id": task_id,
                    "process_level": "L0",
                    "goal": f"Complete demo work item {i:02d}.",
                    "expected": f"A user-visible report at {report_path}.",
                    "next_action": "Review the generated report.",
                    "user_visible_output_path": report_path,
                },
                {
                    "op": "artifact.add",
                    "artifact_id": f"{task_id}-report",
                    "task_id": task_id,
                    "type": "report",
                    "path": report_path,
                    "audience": "user",
                    "content": f"# Batch Demo Task {i:02d}\n\nResult: demo task {i:02d} completed.\n",
                    "compute_metadata": True,
                },
                {
                    "op": "task.update",
                    "task_id": task_id,
                    "status": "closed",
                    "brief_current_state": "Task is closed.",
                    "brief_latest_result": f"Report completed: {report_path}.",
                    "handoff_status": "Task is closed.",
                    "handoff_latest_result": f"Report completed: {report_path}.",
                    "next_action": "No next action.",
                    "index_outputs": [report_path],
                },
            ]
        )
    operations.append(
        {
            "op": "session.summarize",
            "task_ids": task_ids,
            "summary": "Twelve demo tasks were completed through one batch operation.",
            "next_action": "Review the reports and choose the next real task.",
        }
    )
    return {
        "format": "batch-json",
        "description": "Create 12 L0 tasks, 12 reports, close the tasks, and write session continuation.",
        "operations": operations,
    }


def recipes() -> dict[str, dict[str, object]]:
    payload = deepcopy(RECIPES)
    payload["batch-12-tasks"] = batch_12_tasks_recipe()
    return payload


def manifest() -> dict[str, object]:
    return {
        "manifest_id": "agent-operation-manifest",
        "manifest_version": "1.0.0",
        "purpose": "Machine-readable operation contract for AI agents using AI Workroot.",
        "normal_mode": {
            "read_first": [
                "AGENTS.md",
                ".workroot/kernel/boot/agent-fast-start.md",
                "scripts/workroot_cli.py manifest --format json",
            ],
            "do_not_read": [
                "scripts/workroot_client.py",
                "scripts/validate_kernel.py",
                "docs/plans/",
            ],
            "source_code_exception": "Read implementation source only when debugging or changing AI Workroot itself.",
        },
        "legacy_mode": {
            "description": "task, run, action, artifact, retrieval-card, checkpoint, invalidation, mind, session, continue, and batch commands are legacy public-seed agent-operation commands. The 0.9.529 Clean Mode user path is init, context, doctor, status, list, and bootstrap-dev for developer dogfooding.",
            "commands": [
                "task",
                "run",
                "action",
                "artifact",
                "retrieval-card",
                "checkpoint",
                "invalidation",
                "mind",
                "session",
                "continue",
                "batch",
            ],
        },
        "commands": {
            "quickstart": "Print short human-readable CLI path.",
            "manifest --format json": "Print this operation contract.",
            "schema --format json": "Print enums and batch operation fields.",
            "recipe batch-12-tasks --format json": "Print a directly usable batch JSON example.",
            "session summarize --from-registry --recent N": "Write global continuation from active and recent registry tasks without passing every task id.",
            "doctor": "Run kernel validation.",
        },
        "enums": {
            "task_statuses": sorted(TASK_STATUSES),
            "process_levels": sorted(PROCESS_LEVELS),
            "owner_scopes": sorted(OWNER_SCOPES),
            "visibilities": sorted(VISIBILITIES),
            "action_types": ACTION_TYPES,
            "artifact_audiences": ARTIFACT_AUDIENCES,
            "mind_types": sorted(MIND_TYPES),
        },
        "batch": {
            "command": "python3 scripts/workroot_cli.py batch apply --file plan.json",
            "transaction_journal_path": ".workroot/runtime/transactions/",
            "rollback_status": "rolled_back",
            "committed_status": "committed",
            "notes": [
                "Batch is not a workflow engine.",
                "Batch snapshots index, task, session continuation, space/work, and space/mind paths it can touch.",
                "Use session.summarize for global continuation.",
                "Task updates do not overwrite global continuation.",
            ],
        },
        "batch_operations": deepcopy(BATCH_OPERATIONS),
        "unsupported_batch_operations": [
            "decision.add",
            "release operations",
            "forget/tombstone operations",
        ],
        "recipes": recipes(),
    }


def schema() -> dict[str, object]:
    data = manifest()
    return {
        "manifest_id": data["manifest_id"],
        "enums": data["enums"],
        "batch": data["batch"],
        "batch_operations": data["batch_operations"],
        "unsupported_batch_operations": data["unsupported_batch_operations"],
    }


def recipe(name: str) -> dict[str, object]:
    all_recipes = recipes()
    if name not in all_recipes:
        valid = ", ".join(sorted(all_recipes))
        raise SystemExit(f"unknown recipe: {name}; valid recipes: {valid}")
    return deepcopy(all_recipes[name])
