#!/usr/bin/env python3
"""Thin CLI wrapper for the AI Workroot file-first client."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from workroot_operation_manifest import manifest as operation_manifest
from workroot_operation_manifest import recipe as operation_recipe
from workroot_operation_manifest import schema as operation_schema
from workroot_operation_manifest import recipes as operation_recipes
from workroot_bootstrap import bootstrap_dev
from workroot_context import ContextRequest, build_context_package
from workroot_doctor import render_json as render_doctor_json
from workroot_doctor import render_text as render_doctor_text
from workroot_doctor import resolve_state_record
from workroot_doctor import run_doctor
from workroot_client import (
    MIND_TYPES,
    OWNER_SCOPES,
    PROCESS_LEVELS,
    TASK_STATUSES,
    VISIBILITIES,
    WorkrootClient,
    now_utc,
    slugify,
)
from workroot_paths import resolve_ai_workroot_home
from workroot_sqlite import initialize_workroot_sqlite
from workroot_state import initialize_workroot_state, read_jsonl


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="resource", required=True)

    subparsers.add_parser("quickstart")
    init = subparsers.add_parser("init")
    init.add_argument("--name", required=True)
    init.add_argument("--directory", required=True)
    init.add_argument("--id", dest="workroot_id")
    init.add_argument("--no-native-agent-entry", action="store_true")
    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("--format", choices=["text", "json"], default="text")
    status = subparsers.add_parser("status")
    status.add_argument("--cwd", default=".")
    bootstrap = subparsers.add_parser("bootstrap-dev")
    bootstrap.add_argument("--dry-run", action="store_true")
    context = subparsers.add_parser("context")
    context.add_argument("--agent", choices=["codex", "claude"], required=True)
    context.add_argument("--cwd", default=".")
    context.add_argument("--query", default="")
    context.add_argument("--debug", action="store_true")
    manifest_parser = subparsers.add_parser("manifest")
    manifest_parser.add_argument("--format", choices=["text", "json"], default="text")
    schema_parser = subparsers.add_parser("schema")
    schema_parser.add_argument("--format", choices=["text", "json"], default="text")
    recipe = subparsers.add_parser("recipe")
    recipe.add_argument("name", choices=sorted(operation_recipes()))
    recipe.add_argument("--format", choices=["text", "json"], default="text")
    doctor = subparsers.add_parser("doctor")
    doctor.add_argument("--format", choices=["text", "json"], default="text")
    doctor.add_argument("--cwd", default=".")

    task = subparsers.add_parser("task")
    task_sub = task.add_subparsers(dest="action", required=True)
    task_create = task_sub.add_parser("create")
    task_create.add_argument("title")
    task_create.add_argument("--id", dest="task_id")
    task_create.add_argument("--process-level", choices=sorted(PROCESS_LEVELS), default="L0")
    task_create.add_argument("--goal", default="What are we trying to accomplish?")
    task_create.add_argument("--why", default="Why is this worth doing?")
    task_create.add_argument("--expected", default="What should exist when this task is done?")
    task_create.add_argument("--next", dest="next_action", default="Define next step")
    task_create.add_argument("--owner-scope", choices=sorted(OWNER_SCOPES), default="personal")
    task_create.add_argument("--visibility", choices=sorted(VISIBILITIES), default="internal")
    task_create.add_argument("--priority", default="")
    task_create.add_argument("--created-at", default=now_utc())
    task_create.add_argument("--user-visible-output-path", default="")
    task_update = task_sub.add_parser("update")
    task_update.add_argument("--task-id", required=True)
    task_update.add_argument("--status", choices=sorted(TASK_STATUSES))
    task_update.add_argument("--updated-at", default="")
    task_update.add_argument("--next-action")
    task_update.add_argument("--user-visible-output-path")
    task_update.add_argument("--brief-current-state")
    task_update.add_argument("--brief-latest-result")
    task_update.add_argument("--handoff-status")
    task_update.add_argument("--handoff-latest-result")
    task_update.add_argument("--index-output", action="append", default=[])
    task_update.add_argument("--mind-path", action="append", default=[])
    task_update.add_argument("--continue-summary")
    task_complete = task_sub.add_parser("complete")
    task_complete.add_argument("--task-id", required=True)
    task_complete.add_argument("--process-level", choices=sorted(PROCESS_LEVELS), default="")
    task_complete.add_argument("--report-path", required=True)
    task_complete.add_argument("--report-content-file", required=True)
    task_complete.add_argument("--next-action", default="")
    task_complete.add_argument("--checkpoint", action="store_true")

    run = subparsers.add_parser("run")
    run_sub = run.add_subparsers(dest="action", required=True)
    run_add = run_sub.add_parser("add")
    run_add.add_argument("--task-id", required=True)
    run_add.add_argument("--run-id", required=True)
    run_add.add_argument("--title", required=True)
    run_add.add_argument("--status", default="active")
    run_add.add_argument("--validity", default="")
    run_add.add_argument("--validity-reason", default="")
    run_add.add_argument("--superseded-by", default="")
    run_add.add_argument("--started-at", default=now_utc())
    run_add.add_argument("--completed-at", default="")
    run_add.add_argument("--output-dir", default="")
    run_add.add_argument("--primary-artifact", default="")
    run_add.add_argument("--validation", default="")
    run_add.add_argument("--conclusion-preview", default="")
    run_update = run_sub.add_parser("update")
    run_update.add_argument("--run-id", required=True)
    run_update.add_argument("--status")
    run_update.add_argument("--validity")
    run_update.add_argument("--validity-reason")
    run_update.add_argument("--superseded-by")
    run_update.add_argument("--completed-at")
    run_update.add_argument("--output-dir")
    run_update.add_argument("--primary-artifact")
    run_update.add_argument("--validation")
    run_update.add_argument("--conclusion-preview")
    run_update.add_argument("--updated-at")

    action = subparsers.add_parser("action")
    action_sub = action.add_subparsers(dest="action", required=True)
    action_add = action_sub.add_parser("add")
    action_add.add_argument("--task-id", required=True)
    action_add.add_argument("--action-id", required=True)
    action_add.add_argument("--run-id", default="")
    action_add.add_argument("--type", dest="record_type", default="")
    action_add.add_argument("--status", default="active")
    action_add.add_argument("--summary", default="")
    action_add.add_argument("--tool", default="")
    action_add.add_argument("--input-ref", default="")
    action_add.add_argument("--output-ref", default="")
    action_add.add_argument("--approval-ref", default="")
    action_add.add_argument("--risk-level", default="")
    action_add.add_argument("--created-at", default=now_utc())

    artifact = subparsers.add_parser("artifact")
    artifact_sub = artifact.add_subparsers(dest="action", required=True)
    artifact_add = artifact_sub.add_parser("add")
    artifact_add.add_argument("--artifact-id", required=True)
    artifact_add.add_argument("--task-id", required=True)
    artifact_add.add_argument("--run-id", default="")
    artifact_add.add_argument("--action-id", default="")
    artifact_add.add_argument("--type", dest="record_type", default="")
    artifact_add.add_argument("--path", required=True)
    artifact_add.add_argument("--audience", default="internal")
    artifact_add.add_argument("--status", default="active")
    artifact_add.add_argument("--size", default="")
    artifact_add.add_argument("--checksum", default="")
    artifact_add.add_argument("--created-at", default=now_utc())
    artifact_add.add_argument("--create-file", action="store_true")
    artifact_add.add_argument("--content", default="")
    artifact_add.add_argument("--compute-metadata", action="store_true")

    card = subparsers.add_parser("retrieval-card")
    card_sub = card.add_subparsers(dest="action", required=True)
    card_add = card_sub.add_parser("add")
    card_add.add_argument("--task-id", required=True)
    card_add.add_argument("--card-id", required=True)
    card_add.add_argument("--freshness", default="hot")
    card_add.add_argument("--source-paths", default="")
    card_add.add_argument("--created-at", default=now_utc())

    checkpoint = subparsers.add_parser("checkpoint")
    checkpoint_sub = checkpoint.add_subparsers(dest="action", required=True)
    checkpoint_add = checkpoint_sub.add_parser("add")
    checkpoint_add.add_argument("--task-id", required=True)
    checkpoint_add.add_argument("--checkpoint-id", required=True)
    checkpoint_add.add_argument("--current-status", required=True)
    checkpoint_add.add_argument("--last-valid-run-id", default="")
    checkpoint_add.add_argument("--next-action", default="")
    checkpoint_add.add_argument("--required-context-paths", default="")
    checkpoint_add.add_argument("--created-at", default=now_utc())

    invalidation = subparsers.add_parser("invalidation")
    invalidation_sub = invalidation.add_subparsers(dest="action", required=True)
    invalidation_add = invalidation_sub.add_parser("add")
    invalidation_add.add_argument("--task-id", required=True)
    invalidation_add.add_argument("--invalidation-id", required=True)
    invalidation_add.add_argument("--run-id", default="")
    invalidation_add.add_argument("--artifact-id", default="")
    invalidation_add.add_argument("--invalidated-claim", default="")
    invalidation_add.add_argument("--reason", default="")
    invalidation_add.add_argument("--replacement-ref", default="")
    invalidation_add.add_argument("--path", default="")
    invalidation_add.add_argument("--created-at", default=now_utc())

    mind = subparsers.add_parser("mind")
    mind_sub = mind.add_subparsers(dest="action", required=True)
    mind_add = mind_sub.add_parser("add")
    mind_add.add_argument("--mind-id", required=True)
    mind_add.add_argument("--title", required=True)
    mind_add.add_argument("--type", choices=sorted(MIND_TYPES), required=True)
    mind_add.add_argument("--status", default="active")
    mind_add.add_argument("--temperature", default="warm")
    mind_add.add_argument("--privacy-level", default="internal")
    mind_add.add_argument("--release-level", default="active")
    mind_add.add_argument("--retrieval-rule", default="")
    mind_add.add_argument("--summary", default="")
    mind_add.add_argument("--path", default="")
    mind_add.add_argument("--from-path", action="append", default=[])
    mind_add.add_argument("--from-task-id", action="append", default=[])
    mind_add.add_argument("--source-path", default="", help="Deprecated alias for --path.")
    mind_add.add_argument("--set-task-output", action="store_true")
    mind_add.add_argument("--related-task-id", default="")
    mind_add.add_argument("--replaces-mind-id", default="")
    mind_add.add_argument("--created-at", default=now_utc())

    session = subparsers.add_parser("session")
    session_sub = session.add_subparsers(dest="action", required=True)
    session_summarize = session_sub.add_parser("summarize")
    session_summarize.add_argument("--task-id", action="append", default=[])
    session_summarize.add_argument("--from-registry", action="store_true")
    session_summarize.add_argument("--recent", type=int, default=5)
    session_summarize.add_argument("--summary", required=True)
    session_summarize.add_argument("--next-action", required=True)

    cont = subparsers.add_parser("continue")
    cont_sub = cont.add_subparsers(dest="action", required=True)
    cont_rebuild = cont_sub.add_parser("rebuild")
    cont_rebuild.add_argument("--recent", type=int, default=5)

    batch = subparsers.add_parser("batch")
    batch_sub = batch.add_subparsers(dest="action", required=True)
    batch_apply = batch_sub.add_parser("apply")
    batch_apply.add_argument("--file", required=True)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    client = WorkrootClient()

    if args.resource == "quickstart":
        print("For normal agent operations, read manifest first:")
        print("python3 scripts/workroot_cli.py manifest --format json")
        print("Use JSON schema for exact fields:")
        print("python3 scripts/workroot_cli.py schema --format json")
        print("Use a directly usable batch example:")
        print("python3 scripts/workroot_cli.py recipe batch-12-tasks --format json")
        print("Use session summarize --from-registry --recent N to summarize selected registry tasks without a long task id list.")
        print("Use task complete for common task finalization.")
        print("Use schema to inspect enum and path rules.")
        print("Use recipe task-l0-report, task-l1-report, or task-l2-evidence for examples.")
        print("Use continue rebuild for human-facing continuation.")
        return

    if args.resource == "init":
        home = resolve_ai_workroot_home()
        workroot_id = args.workroot_id or f"wr_{slugify(args.name).replace('-', '_')}"
        initialized = initialize_workroot_state(
            home,
            workroot_id=workroot_id,
            name=args.name,
            user_directory=Path(args.directory),
            now=now_utc(),
        )
        initialize_workroot_sqlite(initialized.state_directory / "indexes/workroot.sqlite")
        print(initialized.state_directory)
        return

    if args.resource == "list":
        records = read_jsonl(resolve_ai_workroot_home() / "registry/workroots.jsonl")
        if args.format == "json":
            print(json.dumps(records, ensure_ascii=False, indent=2))
            return
        for record in records:
            print(f"{record.get('workrootId')} {record.get('name')} {record.get('userDirectory')}")
        return

    if args.resource == "status":
        cwd = Path(args.cwd).resolve()
        records = read_jsonl(resolve_ai_workroot_home() / "registry/workroots.jsonl")
        matches = [
            record for record in records
            if cwd == Path(str(record.get("userDirectory", ""))).resolve()
            or cwd.is_relative_to(Path(str(record.get("userDirectory", ""))).resolve())
        ]
        if not matches:
            raise SystemExit(f"no Workroot registered for cwd: {cwd}")
        match = max(matches, key=lambda record: len(str(record.get("userDirectory", ""))))
        print(f"{match.get('workrootId')} {match.get('name')} {match.get('stateDirectory')}")
        return

    if args.resource == "bootstrap-dev":
        print(bootstrap_dev(Path("."), dry_run=args.dry_run))
        return

    if args.resource == "context":
        package = build_context_package(
            ContextRequest(
                home=resolve_ai_workroot_home(),
                agent=args.agent,
                cwd=Path(args.cwd),
                query=args.query,
                debug=args.debug,
                now=now_utc(),
            )
        )
        print(package.markdown, end="")
        return

    if args.resource == "manifest":
        data = operation_manifest()
        if args.format == "json":
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            print("Agent Operation Manifest")
            print("Use: python3 scripts/workroot_cli.py manifest --format json")
            print("Normal mode: do not read scripts/workroot_client.py unless debugging or changing Workroot itself.")
            print("Batch command: python3 scripts/workroot_cli.py batch apply --file plan.json")
        return

    if args.resource == "schema":
        if args.format == "json":
            print(json.dumps(operation_schema(), ensure_ascii=False, indent=2))
            return
        print("task statuses: active, paused, blocked, closed, released")
        print("process levels: L0, L1, L2")
        print("owner scopes: personal, team, role, organization")
        print("visibility values: internal, shared, public, private")
        print("action types: command, database_query, api_call, file_edit, browser_research, model_generation, test_run, deployment, manual_check, other")
        print("artifact audiences: internal, user, public, evidence")
        print("single path fields: input_ref, output_ref, approval_ref, path, primary_artifact")
        print("multi path fields: source_paths, required_context_paths")
        print("input_ref must be one repository-relative path, URL, or empty.")
        print("Use retrieval-card source_paths for multiple source files.")
        return

    if args.resource == "recipe":
        if args.format == "json":
            print(json.dumps(operation_recipe(args.name), ensure_ascii=False, indent=2))
            return
        if args.name == "task-l2-evidence":
            print("python3 scripts/workroot_cli.py task create \"Evidence task\" --process-level L2 --id TASK")
            print("python3 scripts/workroot_cli.py task complete --process-level L2 --task-id TASK --report-path space/work/reports/report.md --report-content-file report.md --checkpoint")
        elif args.name == "task-l1-report":
            print("python3 scripts/workroot_cli.py task create \"Report task\" --process-level L1 --id TASK")
            print("python3 scripts/workroot_cli.py task complete --process-level L1 --task-id TASK --report-path space/work/reports/report.md --report-content-file report.md")
        else:
            print("python3 scripts/workroot_cli.py task create \"Simple task\" --process-level L0 --id TASK")
            print("python3 scripts/workroot_cli.py task complete --process-level L0 --task-id TASK --report-path space/work/reports/report.md --report-content-file report.md")
        return

    if args.resource == "doctor":
        home = resolve_ai_workroot_home()
        cwd = Path(args.cwd).resolve()
        should_run_kernel_doctor = (
            args.format == "text"
            and args.cwd == "."
            and resolve_state_record(home, cwd) is None
            and (cwd / "scripts/validate_kernel.py").exists()
        )
        if should_run_kernel_doctor:
            result = subprocess.run(
                [sys.executable, "scripts/validate_kernel.py"],
                text=True,
                capture_output=True,
                check=False,
            )
            print(result.stdout, end="")
            if result.returncode:
                print(result.stderr, end="", file=sys.stderr)
                raise SystemExit(result.returncode)
            return
        result = run_doctor(home, cwd=cwd)
        if args.format == "json":
            print(render_doctor_json(result))
        else:
            print(render_doctor_text(result))
        if result.has_errors():
            raise SystemExit(1)
        return

    if args.resource == "task" and args.action == "create":
        created = client.create_task(
            title=args.title,
            task_id=args.task_id,
            process_level=args.process_level,
            goal=args.goal,
            why=args.why,
            expected=args.expected,
            next_action=args.next_action,
            owner_scope=args.owner_scope,
            visibility=args.visibility,
            priority=args.priority,
            created_at=args.created_at,
            user_visible_output_path=args.user_visible_output_path,
        )
        print(created.source_path)
        return

    if args.resource == "task" and args.action == "update":
        if args.continue_summary:
            parser.error("--continue-summary no longer updates global continuation; use `session summarize` instead")
        client.sync_task_state(
            task_id=args.task_id,
            status=args.status,
            updated_at=args.updated_at or None,
            next_action=args.next_action,
            user_visible_output_path=args.user_visible_output_path,
            brief_current_state=args.brief_current_state,
            brief_latest_result=args.brief_latest_result,
            handoff_status=args.handoff_status,
            handoff_latest_result=args.handoff_latest_result,
            index_outputs=args.index_output,
            mind_paths=args.mind_path,
        )
        print(args.task_id)
        return

    if args.resource == "task" and args.action == "complete":
        client.complete_task(
            task_id=args.task_id,
            report_path=args.report_path,
            report_content_file=args.report_content_file,
            next_action=args.next_action,
            process_level=args.process_level,
            checkpoint=args.checkpoint,
        )
        print(args.report_path)
        return

    if args.resource == "run" and args.action == "add":
        record = client.add_run(
            task_id=args.task_id,
            run_id=args.run_id,
            title=args.title,
            status=args.status,
            validity=args.validity,
            validity_reason=args.validity_reason,
            superseded_by=args.superseded_by,
            started_at=args.started_at,
            completed_at=args.completed_at,
            output_dir=args.output_dir,
            primary_artifact=args.primary_artifact,
            validation=args.validation,
            conclusion_preview=args.conclusion_preview,
        )
        print(record.path)
        return

    if args.resource == "run" and args.action == "update":
        record = client.update_run(
            run_id=args.run_id,
            status=args.status,
            validity=args.validity,
            validity_reason=args.validity_reason,
            superseded_by=args.superseded_by,
            completed_at=args.completed_at,
            output_dir=args.output_dir,
            primary_artifact=args.primary_artifact,
            validation=args.validation,
            conclusion_preview=args.conclusion_preview,
            updated_at=args.updated_at,
        )
        print(record.path)
        return

    if args.resource == "action" and args.action == "add":
        record = client.add_action(
            task_id=args.task_id,
            action_id=args.action_id,
            run_id=args.run_id,
            type=args.record_type,
            status=args.status,
            summary=args.summary,
            tool=args.tool,
            input_ref=args.input_ref,
            output_ref=args.output_ref,
            approval_ref=args.approval_ref,
            risk_level=args.risk_level,
            created_at=args.created_at,
        )
        print(record.path)
        return

    if args.resource == "artifact" and args.action == "add":
        record = client.add_artifact(
            artifact_id=args.artifact_id,
            task_id=args.task_id,
            run_id=args.run_id,
            action_id=args.action_id,
            type=args.record_type,
            path=args.path,
            audience=args.audience,
            status=args.status,
            size=args.size,
            checksum=args.checksum,
            created_at=args.created_at,
            create_missing=args.create_file,
            content=args.content,
            compute_metadata=args.compute_metadata,
        )
        print(record.path)
        return

    if args.resource == "retrieval-card" and args.action == "add":
        record = client.add_retrieval_card(
            task_id=args.task_id,
            card_id=args.card_id,
            freshness=args.freshness,
            source_paths=args.source_paths,
            created_at=args.created_at,
        )
        print(record.path)
        return

    if args.resource == "checkpoint" and args.action == "add":
        record = client.add_checkpoint(
            task_id=args.task_id,
            checkpoint_id=args.checkpoint_id,
            current_status=args.current_status,
            last_valid_run_id=args.last_valid_run_id,
            next_action=args.next_action,
            required_context_paths=args.required_context_paths,
            created_at=args.created_at,
        )
        print(record.path)
        return

    if args.resource == "invalidation" and args.action == "add":
        record = client.add_invalidation(
            task_id=args.task_id,
            invalidation_id=args.invalidation_id,
            run_id=args.run_id,
            artifact_id=args.artifact_id,
            invalidated_claim=args.invalidated_claim,
            reason=args.reason,
            replacement_ref=args.replacement_ref,
            path=args.path,
            created_at=args.created_at,
        )
        print(record.path)
        return

    if args.resource == "mind" and args.action == "add":
        record = client.add_mind(
            mind_id=args.mind_id,
            title=args.title,
            type=args.type,
            status=args.status,
            temperature=args.temperature,
            privacy_level=args.privacy_level,
            release_level=args.release_level,
            retrieval_rule=args.retrieval_rule,
            summary=args.summary,
            path=args.path,
            from_paths=args.from_path,
            from_task_ids=args.from_task_id,
            set_task_output=args.set_task_output,
            source_path=args.source_path,
            related_task_id=args.related_task_id,
            replaces_mind_id=args.replaces_mind_id,
            created_at=args.created_at,
        )
        print(record.path)
        return

    if args.resource == "session" and args.action == "summarize":
        task_ids = client.select_session_task_ids_from_registry(args.recent) if args.from_registry else args.task_id
        if not task_ids and not args.from_registry:
            parser.error("session summarize requires --task-id or --from-registry")
        client.summarize_session(task_ids, args.summary, args.next_action)
        print("space/work/continue.md")
        return

    if args.resource == "continue" and args.action == "rebuild":
        client.rebuild_continue(recent=args.recent)
        print("space/work/continue.md")
        return

    if args.resource == "batch" and args.action == "apply":
        client.apply_batch(args.file)
        print(args.file)
        return

    parser.error("unsupported command")


if __name__ == "__main__":
    main()
