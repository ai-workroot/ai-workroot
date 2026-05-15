#!/usr/bin/env python3
"""Thin CLI wrapper for the AI Workroot file-first client."""

from __future__ import annotations

import argparse

from workroot_client import WorkrootClient, OWNER_SCOPES, PROCESS_LEVELS, VISIBILITIES, now_utc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="resource", required=True)

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

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    client = WorkrootClient()

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

    parser.error("unsupported command")


if __name__ == "__main__":
    main()
