from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests.e2e.harness import REPO_ROOT, env_for, run_cli
from tests.e2e.safety import new_default_run_root, prepare_run_root, require_e2e_runner_active


class LiveTaskContinuityHarnessTest(unittest.TestCase):
    def test_scenario_matrix_has_five_roles_and_default_ten_rounds(self) -> None:
        from tests.e2e.live_task_continuity import live_task_continuity_scenarios

        scenarios = live_task_continuity_scenarios(round_count=10)

        self.assertEqual(len(scenarios), 5)
        self.assertTrue(all(len(role.rounds) == 10 for role in scenarios))
        self.assertTrue(any(role.mode == "temporary" for role in scenarios))
        self.assertTrue(any(role.mode == "long_cycle" for role in scenarios))
        self.assertTrue(any(round.expected_asset_paths for role in scenarios for round in role.rounds))

    def test_round_count_is_bounded_for_live_cost_control(self) -> None:
        from tests.e2e.live_task_continuity import resolve_round_count

        self.assertEqual(resolve_round_count(None), 10)
        self.assertEqual(resolve_round_count("1"), 1)
        self.assertEqual(resolve_round_count("20"), 20)
        with self.assertRaises(ValueError):
            resolve_round_count("0")
        with self.assertRaises(ValueError):
            resolve_round_count("21")

    def test_single_role_mode_allows_fifty_rounds_without_expanding_to_all_roles(self) -> None:
        from tests.e2e.live_task_continuity import live_task_continuity_scenarios, resolve_round_count

        self.assertEqual(resolve_round_count("50", single_role=True), 50)

        scenarios = live_task_continuity_scenarios(round_count=50, role_slug="live-founder-operator")

        self.assertEqual([scenario.slug for scenario in scenarios], ["live-founder-operator"])
        self.assertEqual(len(scenarios[0].rounds), 50)
        self.assertTrue(all(round_script.index == index for index, round_script in enumerate(scenarios[0].rounds, 1)))
        with self.assertRaises(ValueError):
            live_task_continuity_scenarios(round_count=50)
        with self.assertRaises(ValueError):
            live_task_continuity_scenarios(round_count=1, role_slug="missing-role")

    def test_mixed_complexity_role_has_thirty_unique_progressive_rounds(self) -> None:
        from tests.e2e.live_task_continuity import live_task_continuity_scenarios

        scenarios = live_task_continuity_scenarios(round_count=30, role_slug="live-mixed-complexity")

        self.assertEqual([scenario.slug for scenario in scenarios], ["live-mixed-complexity"])
        rounds = scenarios[0].rounds
        self.assertEqual(len(rounds), 30)
        self.assertEqual(len({round_script.label for round_script in rounds}), 30)
        self.assertGreaterEqual(sum(1 for round_script in rounds if "asset" in round_script.expected_shapes), 5)
        self.assertGreaterEqual(sum(1 for round_script in rounds if not round_script.expected_shapes), 4)
        self.assertTrue(any("--persistence temporary" in round_script.user_request for round_script in rounds))

    def test_mixed_complexity_round_metadata_uses_typed_tuple_fields(self) -> None:
        from tests.e2e.live_task_continuity import live_task_continuity_scenarios

        scenario = live_task_continuity_scenarios(round_count=30, role_slug="live-mixed-complexity")[0]

        for round_script in scenario.rounds:
            with self.subTest(round=round_script.index, label=round_script.label):
                self.assertIsInstance(round_script.expected_shapes, tuple)
                self.assertIsInstance(round_script.expected_asset_paths, tuple)
                self.assertIsInstance(round_script.expected_asset_owners, tuple)

    def test_chinese_founder_operator_role_has_progressive_rounds(self) -> None:
        from tests.e2e.live_task_continuity import live_task_continuity_scenarios

        scenario = live_task_continuity_scenarios(round_count=20, role_slug="live-chinese-founder-operator")[0]

        self.assertEqual(scenario.slug, "live-chinese-founder-operator")
        self.assertEqual(scenario.mode, "long_cycle")
        self.assertEqual(len(scenario.rounds), 20)
        self.assertTrue(all(round_script.user_request for round_script in scenario.rounds))
        self.assertTrue(any("试点" in round_script.user_request for round_script in scenario.rounds))
        self.assertTrue(any("--persistence temporary" in round_script.user_request for round_script in scenario.rounds))
        self.assertGreaterEqual(
            sum(1 for round_script in scenario.rounds if "asset" in round_script.expected_shapes), 4
        )
        self.assertGreaterEqual(
            sum(1 for round_script in scenario.rounds if "decision" in round_script.expected_shapes), 3
        )
        self.assertGreaterEqual(
            sum(1 for round_script in scenario.rounds if "continuation" in round_script.expected_shapes), 3
        )

    def test_novice_roles_use_natural_user_requests_without_protocol_terms(self) -> None:
        from tests.e2e.live_task_continuity import live_task_continuity_scenarios

        protocol_terms = (
            "workroot",
            "commit",
            "sync",
            "lease",
            "packet",
            "handoff",
            "task",
            "asset",
            "refs",
            "protocol",
            "persistence",
            "任务",
            "协议",
            "上下文",
            "接力",
        )
        role_expectations = {
            "live-novice-chinese-shop-owner": 20,
            "live-novice-english-community-builder": 10,
        }
        for role_slug, round_count in role_expectations.items():
            with self.subTest(role_slug=role_slug):
                scenario = live_task_continuity_scenarios(round_count=round_count, role_slug=role_slug)[0]
                self.assertEqual(len(scenario.rounds), round_count)
                self.assertEqual(scenario.mode, "long_cycle")
                self.assertGreaterEqual(
                    sum(1 for round_script in scenario.rounds if "asset" in round_script.expected_shapes), 2
                )
                self.assertTrue(any("decision" in round_script.expected_shapes for round_script in scenario.rounds))
                self.assertTrue(any(not round_script.expected_shapes for round_script in scenario.rounds))
                joined = "\n".join(round_script.user_request.lower() for round_script in scenario.rounds)
                for term in protocol_terms:
                    self.assertNotIn(term, joined)

    def test_novice_prompt_does_not_expose_white_box_expected_answers(self) -> None:
        from tests.e2e.live_task_continuity import _round_prompt, live_task_continuity_scenarios

        scenario = live_task_continuity_scenarios(round_count=20, role_slug="live-novice-chinese-shop-owner")[0]
        scripted_round = next(round_script for round_script in scenario.rounds if round_script.expected_shapes)

        prompt = _round_prompt(role=scenario, round_script=scripted_round)

        self.assertIn(scripted_round.user_request, prompt)
        self.assertIn("workroot agent sync", prompt)
        self.assertIn("--format packet", prompt)
        self.assertNotIn("Expected Workroot capture shape", prompt)
        self.assertNotIn("Expected user-visible asset path", prompt)
        self.assertNotIn(", ".join(scripted_round.expected_shapes), prompt)
        for path in scripted_round.expected_asset_paths:
            self.assertNotIn(path, prompt)
        self.assertNotIn("phase=switching, work_kind=task", prompt)
        self.assertNotIn("new normal work uses", prompt)

    def test_non_novice_prompt_teaches_negative_work_signal_routes(self) -> None:
        from tests.e2e.live_task_continuity import _round_prompt, live_task_continuity_scenarios

        scenario = live_task_continuity_scenarios(round_count=20, role_slug="live-mixed-complexity")[0]
        prompt = _round_prompt(role=scenario, round_script=scenario.rounds[0])

        self.assertIn("Direct answer: work_kind=quick, intended_action=answer", prompt)
        self.assertIn("Use intended_action=preserve for checkpoint or handoff", prompt)
        self.assertIn("Decision inside active work: work_kind=decision", prompt)
        self.assertIn("User-visible file for active work: work_kind=authoring", prompt)
        self.assertIn("Do not use boundary=separate_work for quick answers", prompt)
        self.assertIn("Use `workroot context` only for startup, recovery, or debugging", prompt)

    def test_round_validation_requires_packet_format_for_agent_sync(self) -> None:
        from tests.e2e.live_task_continuity import _validate_agent_sync_format

        failures = _validate_agent_sync_format(
            [
                {
                    "argv": [
                        "agent",
                        "sync",
                        "--agent",
                        "codex",
                        "--cwd",
                        ".",
                        "--query",
                        "current request",
                    ]
                }
            ]
        )

        self.assertEqual(failures, ["agent sync did not request packet format"])
        self.assertEqual(
            _validate_agent_sync_format(
                [
                    {
                        "argv": [
                            "agent",
                            "sync",
                            "--agent",
                            "codex",
                            "--cwd",
                            ".",
                            "--query",
                            "current request",
                            "--format",
                            "packet",
                        ]
                    }
                ]
            ),
            [],
        )

    def test_chinese_novice_role_has_broad_twenty_round_user_journey(self) -> None:
        from tests.e2e.live_task_continuity import live_task_continuity_scenarios

        scenario = live_task_continuity_scenarios(round_count=20, role_slug="live-novice-chinese-shop-owner")[0]

        self.assertEqual(len(scenario.rounds), 20)
        joined = "\n".join(round_script.user_request for round_script in scenario.rounds)
        for phrase in ("经营方向", "早高峰", "下午空档", "周末亲子", "朋友圈", "会员", "下周"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, joined)
        self.assertGreaterEqual(
            sum(1 for round_script in scenario.rounds if "asset" in round_script.expected_shapes), 4
        )
        self.assertGreaterEqual(
            sum(1 for round_script in scenario.rounds if "decision" in round_script.expected_shapes), 3
        )
        self.assertGreaterEqual(
            sum(1 for round_script in scenario.rounds if "continuation" in round_script.expected_shapes), 2
        )

    def test_complex_novice_chinese_service_owner_has_long_natural_twenty_round_journey(self) -> None:
        from tests.e2e.live_task_continuity import live_task_continuity_scenarios

        scenario = live_task_continuity_scenarios(
            round_count=20,
            role_slug="live-novice-chinese-service-owner",
        )[0]

        self.assertEqual(scenario.slug, "live-novice-chinese-service-owner")
        self.assertEqual(scenario.mode, "long_cycle")
        self.assertEqual(len(scenario.rounds), 20)
        self.assertGreaterEqual(sum(1 for round_script in scenario.rounds if len(round_script.user_request) >= 100), 12)
        self.assertGreaterEqual(
            sum(1 for round_script in scenario.rounds if "asset" in round_script.expected_shapes), 5
        )
        self.assertGreaterEqual(
            sum(1 for round_script in scenario.rounds if "decision" in round_script.expected_shapes), 4
        )
        self.assertGreaterEqual(
            sum(1 for round_script in scenario.rounds if "continuation" in round_script.expected_shapes), 3
        )
        self.assertTrue(
            any(round_script.expected_context_intent == "evidence_lookup" for round_script in scenario.rounds)
        )
        joined = "\n".join(round_script.user_request.lower() for round_script in scenario.rounds)
        for term in (
            "workroot",
            "commit",
            "sync",
            "lease",
            "packet",
            "handoff",
            "task",
            "asset",
            "refs",
            "protocol",
            "persistence",
            "任务",
            "协议",
            "上下文",
            "接力",
        ):
            with self.subTest(term=term):
                self.assertNotIn(term, joined)
        for phrase in ("家政", "培训", "阿姨", "客户", "现金流", "招聘", "社区活动", "下周"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, joined)

    def test_audited_wrapper_writes_outputs_under_transcript_artifacts(self) -> None:
        from tests.e2e.live_task_continuity import create_audited_workroot_wrapper, read_jsonl

        with tempfile.TemporaryDirectory() as tmp:
            sandbox_base = Path(tmp) / "sandboxes"
            run_root = prepare_run_root(new_default_run_root(base=sandbox_base), sandbox_base=sandbox_base)
            ai_home = run_root / "ai-workroot-home"
            env = env_for(ai_home)
            user_dir = run_root / "user-dirs" / "wrapper-role"
            user_dir.mkdir(parents=True)
            init = run_cli(
                (
                    "init",
                    "--name",
                    "Wrapper Role",
                    "--directory",
                    str(user_dir),
                    "--id",
                    "wr_wrapper_role",
                    "--native-agent-entry",
                ),
                env=env,
                cwd=REPO_ROOT,
            )
            self.assertEqual(init.returncode, 0, init.stderr)
            transcript_dir = run_root / "transcripts" / "live-task-continuity" / "wrapper-role" / "round-01"
            log_path = transcript_dir / "workroot-command-log.jsonl"
            artifacts_dir = transcript_dir / "command-artifacts"
            wrapper = create_audited_workroot_wrapper(run_root=run_root)

            completed = subprocess.run(
                (str(wrapper), "status", "--cwd", "."),
                cwd=user_dir,
                env={
                    **env,
                    "WORKROOT_COMMAND_LOG": str(log_path),
                    "WORKROOT_COMMAND_ARTIFACTS_DIR": str(artifacts_dir),
                },
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            records = read_jsonl(log_path)
            self.assertEqual(records[0]["argv"], ["status", "--cwd", "."])
            self.assertEqual(records[0]["returncode"], 0)
            self.assertTrue(Path(records[0]["stdoutPath"]).is_file())
            self.assertTrue(Path(records[0]["stderrPath"]).is_file())
            self.assertEqual(Path(records[0]["stdoutPath"]).parents[1], transcript_dir)

    def test_runtime_pollution_detection_allows_expected_user_assets(self) -> None:
        from tests.e2e.live_task_continuity import runtime_artifacts_in_user_directory

        with tempfile.TemporaryDirectory() as tmp:
            user_dir = Path(tmp) / "user"
            user_dir.mkdir()
            (user_dir / "results").mkdir()
            (user_dir / "results" / "plan.md").write_text("# Plan\n", encoding="utf-8")
            (user_dir / "workroot-command-log.jsonl").write_text("{}", encoding="utf-8")
            (user_dir / "runtime").mkdir()

            artifacts = runtime_artifacts_in_user_directory(
                user_dir,
                allowed_asset_paths=("results/plan.md",),
            )

            self.assertEqual(artifacts, ["runtime", "workroot-command-log.jsonl"])

    def test_protocol_query_validation_flags_context_and_sync_without_query(self) -> None:
        from tests.e2e.live_task_continuity import _validate_context_and_sync_queries

        failures = _validate_context_and_sync_queries(
            [
                {"argv": ["context", "--agent", "codex", "--cwd", "."]},
                {"argv": ["agent", "sync", "--agent", "codex", "--cwd", ".", "--query", ""]},
                {"argv": ["agent", "sync", "--agent", "codex", "--cwd", ".", "--query", "<short intent>"]},
                {
                    "argv": [
                        "agent",
                        "sync",
                        "--agent",
                        "codex",
                        "--cwd",
                        ".",
                        "--query",
                        "<current user request or short intent>",
                    ]
                },
                {"argv": ["agent", "sync", "--help"]},
                {"argv": ["agent", "sync", "--agent", "codex", "--cwd", ".", "--query", "real user request"]},
            ]
        )

        self.assertEqual(
            failures,
            [
                "context missing meaningful --query",
                "agent sync missing meaningful --query",
                "agent sync missing meaningful --query",
                "agent sync missing meaningful --query",
            ],
        )

    def test_empty_database_summary_exposes_task_protocol_and_runtime_counts(self) -> None:
        from tests.e2e.live_task_continuity import summarize_role_database

        with tempfile.TemporaryDirectory() as tmp:
            sandbox_base = Path(tmp) / "sandboxes"
            run_root = prepare_run_root(new_default_run_root(base=sandbox_base), sandbox_base=sandbox_base)
            ai_home = run_root / "ai-workroot-home"
            env = env_for(ai_home)
            user_dir = run_root / "user-dirs" / "audit-role"
            user_dir.mkdir(parents=True)
            init = run_cli(
                (
                    "init",
                    "--name",
                    "Audit Role",
                    "--directory",
                    str(user_dir),
                    "--id",
                    "wr_audit_role",
                    "--native-agent-entry",
                ),
                env=env,
                cwd=REPO_ROOT,
            )
            self.assertEqual(init.returncode, 0, init.stderr)

            summary = summarize_role_database(ai_home=ai_home, workroot_id="wr_audit_role")

            self.assertEqual(summary["counts"]["tasks"], 0)
            self.assertEqual(summary["counts"]["protocolEvents"], 0)
            self.assertEqual(summary["counts"]["assets"], 0)
            self.assertIn("sqlitePath", summary)
            self.assertIn("runtimeFileCount", summary)

    def test_one_round_smoke_accepts_active_run_without_handoff_but_full_role_requires_continuity_view(
        self,
    ) -> None:
        from tests.e2e.live_task_continuity import _validate_role_continuity, live_task_continuity_scenarios

        final_db = {
            "counts": {
                "tasks": 1,
                "taskRuns": 1,
                "protocolEvents": 1,
                "handoffsCurrent": 0,
                "taskSummariesCurrent": 0,
            }
        }
        with tempfile.TemporaryDirectory() as tmp:
            user_dir = Path(tmp)
            smoke_role = live_task_continuity_scenarios(round_count=1)[0]
            full_role = live_task_continuity_scenarios(round_count=10)[0]

            smoke_failures = _validate_role_continuity(role=smoke_role, user_directory=user_dir, final_db=final_db)
            full_failures = _validate_role_continuity(role=full_role, user_directory=user_dir, final_db=final_db)

        self.assertNotIn("no current handoff or task summary was preserved", smoke_failures)
        self.assertIn("no current handoff or task summary was preserved", full_failures)

    def test_round_validation_uses_protocol_event_status_deltas(self) -> None:
        from tests.e2e.live_task_continuity import LiveRoundScript, _validate_round

        with tempfile.TemporaryDirectory() as tmp:
            last_message = Path(tmp) / "last-message.txt"
            last_message.write_text("LIVE_TASK_CONTINUITY_OK live-founder-operator round-07\nDone.\n", encoding="utf-8")
            failures = _validate_round(
                round_script=LiveRoundScript(7, "Risk checkpoint", "Preserve risk.", ("checkpoint",)),
                user_directory=Path(tmp),
                returncode=0,
                last_message_path=last_message,
                commands=["agent sync", "agent commit"],
                db_summary={
                    "counts": {"protocolEvents": 10},
                    "protocolEventStatuses": {"applied": 7, "quarantined": 3},
                },
                before_db_summary={
                    "counts": {"protocolEvents": 9},
                    "protocolEventStatuses": {"applied": 6, "quarantined": 3},
                },
            )

        self.assertNotIn("quarantined protocol events found", failures)

    def test_round_validation_flags_new_quarantine_delta(self) -> None:
        from tests.e2e.live_task_continuity import LiveRoundScript, _validate_round

        with tempfile.TemporaryDirectory() as tmp:
            last_message = Path(tmp) / "last-message.txt"
            last_message.write_text("LIVE_TASK_CONTINUITY_OK live-founder-operator round-07\nDone.\n", encoding="utf-8")
            failures = _validate_round(
                round_script=LiveRoundScript(7, "Risk checkpoint", "Preserve risk.", ("checkpoint",)),
                user_directory=Path(tmp),
                returncode=0,
                last_message_path=last_message,
                commands=["agent sync", "agent commit"],
                db_summary={
                    "counts": {"protocolEvents": 10},
                    "protocolEventStatuses": {"applied": 6, "quarantined": 4},
                },
                before_db_summary={
                    "counts": {"protocolEvents": 9},
                    "protocolEventStatuses": {"applied": 6, "quarantined": 3},
                },
            )

        self.assertIn("new quarantined protocol events found", failures)

    def test_evidence_round_validation_requires_first_sync_work_signal(self) -> None:
        from tests.e2e.live_task_continuity import LiveRoundScript, _validate_round

        with tempfile.TemporaryDirectory() as tmp:
            last_message = Path(tmp) / "last-message.txt"
            last_message.write_text("LIVE_TASK_CONTINUITY_OK live-role round-14\nDone.\n", encoding="utf-8")
            failures = _validate_round(
                round_script=LiveRoundScript(
                    14,
                    "Evidence request",
                    "这个判断主要是从哪些现有信息看出来的？",
                    expected_context_intent="evidence_lookup",
                ),
                user_directory=Path(tmp),
                returncode=0,
                last_message_path=last_message,
                commands=["agent sync"],
                db_summary={"counts": {"protocolEvents": 1}, "protocolEventStatuses": {"applied": 1}},
                before_db_summary={"counts": {"protocolEvents": 1}, "protocolEventStatuses": {"applied": 1}},
                command_records=[
                    {
                        "argv": [
                            "agent",
                            "sync",
                            "--agent",
                            "codex",
                            "--cwd",
                            ".",
                            "--query",
                            "这个判断主要是从哪些现有信息看出来的？",
                        ],
                        "returncode": 0,
                    }
                ],
            )

        self.assertIn("evidence round sync missing needs_evidence WorkSignal", failures)

    def test_evidence_round_validation_accepts_sync_work_signal(self) -> None:
        from tests.e2e.live_task_continuity import LiveRoundScript, _validate_round

        with tempfile.TemporaryDirectory() as tmp:
            last_message = Path(tmp) / "last-message.txt"
            last_message.write_text("LIVE_TASK_CONTINUITY_OK live-role round-14\nDone.\n", encoding="utf-8")
            failures = _validate_round(
                round_script=LiveRoundScript(
                    14,
                    "Evidence request",
                    "这个判断主要是从哪些现有信息看出来的？",
                    expected_context_intent="evidence_lookup",
                ),
                user_directory=Path(tmp),
                returncode=0,
                last_message_path=last_message,
                commands=["agent sync"],
                db_summary={"counts": {"protocolEvents": 1}, "protocolEventStatuses": {"applied": 1}},
                before_db_summary={"counts": {"protocolEvents": 1}, "protocolEventStatuses": {"applied": 1}},
                command_records=[
                    {
                        "argv": [
                            "agent",
                            "sync",
                            "--agent",
                            "codex",
                            "--cwd",
                            ".",
                            "--query",
                            "这个判断主要是从哪些现有信息看出来的？",
                            "--work-signal",
                            '{"intended_action":"inspect","concerns":["needs_evidence"],"focus":"判断依据"}',
                        ],
                        "returncode": 0,
                    }
                ],
            )

        self.assertNotIn("evidence round sync missing needs_evidence WorkSignal", failures)

    def test_round_validation_rejects_context_without_sync(self) -> None:
        from tests.e2e.live_task_continuity import LiveRoundScript, _validate_round

        with tempfile.TemporaryDirectory() as tmp:
            last_message = Path(tmp) / "last-message.txt"
            last_message.write_text("LIVE_TASK_CONTINUITY_OK live-role round-01\nDone.\n", encoding="utf-8")
            failures = _validate_round(
                round_script=LiveRoundScript(1, "Start", "Please help me plan this."),
                user_directory=Path(tmp),
                returncode=0,
                last_message_path=last_message,
                commands=["context"],
                db_summary={"counts": {"protocolEvents": 0}, "protocolEventStatuses": {}},
                before_db_summary={"counts": {"protocolEvents": 0}, "protocolEventStatuses": {}},
                command_records=[
                    {
                        "argv": [
                            "context",
                            "--agent",
                            "codex",
                            "--cwd",
                            ".",
                            "--query",
                            "Please help me plan this.",
                        ],
                        "returncode": 0,
                    }
                ],
            )

        self.assertIn("round did not call agent sync", failures)
        self.assertIn("context was used without agent sync", failures)

    def test_role_protocol_usage_rejects_context_every_round(self) -> None:
        from tests.e2e.live_task_continuity import _validate_role_protocol_usage

        command_records_by_round = [
            [
                {"argv": ["context", "--agent", "codex", "--cwd", ".", "--query", "first"]},
                {"argv": ["agent", "sync", "--agent", "codex", "--cwd", ".", "--query", "first"]},
            ],
            [
                {"argv": ["context", "--agent", "codex", "--cwd", ".", "--query", "second"]},
                {"argv": ["agent", "sync", "--agent", "codex", "--cwd", ".", "--query", "second"]},
            ],
        ]

        failures = _validate_role_protocol_usage(command_records_by_round)

        self.assertIn("context was used in every round; sync-first loop regressed", failures)

    def test_round_validation_requires_expected_assets_in_workroot_asset_index(self) -> None:
        from tests.e2e.live_task_continuity import LiveRoundScript, _validate_round

        with tempfile.TemporaryDirectory() as tmp:
            user_dir = Path(tmp)
            (user_dir / "results").mkdir()
            (user_dir / "results" / "plan.md").write_text("# Plan\n", encoding="utf-8")
            last_message = user_dir / "last-message.txt"
            last_message.write_text("LIVE_TASK_CONTINUITY_OK live-role round-03\nDone.\n", encoding="utf-8")

            failures = _validate_round(
                round_script=LiveRoundScript(
                    3,
                    "Create asset",
                    "Create results/plan.md and preserve it as an asset.",
                    ("asset",),
                    expected_asset_paths=("results/plan.md",),
                ),
                user_directory=user_dir,
                returncode=0,
                last_message_path=last_message,
                commands=["agent sync", "agent commit"],
                db_summary={
                    "counts": {"protocolEvents": 2},
                    "protocolEventStatuses": {"applied": 2},
                    "assetPaths": [],
                },
                before_db_summary={
                    "counts": {"protocolEvents": 1},
                    "protocolEventStatuses": {"applied": 1},
                    "assetPaths": [],
                },
            )

        self.assertIn("expected Workroot asset missing: results/plan.md", failures)

    def test_round_validation_flags_wrong_asset_owner(self) -> None:
        from tests.e2e.live_task_continuity import LiveRoundScript, _validate_round

        with tempfile.TemporaryDirectory() as tmp:
            user_dir = Path(tmp)
            (user_dir / "results").mkdir()
            (user_dir / "results" / "plan.md").write_text("# Plan\n", encoding="utf-8")
            last_message = user_dir / "last-message.txt"
            last_message.write_text("LIVE_TASK_CONTINUITY_OK live-role round-03\nDone.\n", encoding="utf-8")

            failures = _validate_round(
                round_script=LiveRoundScript(
                    3,
                    "Create asset",
                    "Create results/plan.md and preserve it as an asset.",
                    ("asset",),
                    ("results/plan.md",),
                    (("results/plan.md", "founder"),),
                ),
                user_directory=user_dir,
                returncode=0,
                last_message_path=last_message,
                commands=["agent sync", "agent commit"],
                db_summary={
                    "assetPaths": ["results/plan.md"],
                    "assetOwners": {"results/plan.md": ["Engineering continuity task"]},
                    "counts": {"protocolEvents": 1},
                    "protocolEventStatuses": {"applied": 1},
                },
            )

        self.assertIn("expected asset results/plan.md owner containing 'founder'", "\n".join(failures))

    def test_round_validation_flags_unexpected_start_work_commit(self) -> None:
        from tests.e2e.live_task_continuity import LiveRoundScript, _validate_round

        with tempfile.TemporaryDirectory() as tmp:
            user_dir = Path(tmp)
            last_message = user_dir / "last-message.txt"
            last_message.write_text("LIVE_TASK_CONTINUITY_OK live-role round-03\nDone.\n", encoding="utf-8")

            failures = _validate_round(
                round_script=LiveRoundScript(3, "Quick answer", "What is a durable summary?"),
                user_directory=user_dir,
                returncode=0,
                last_message_path=last_message,
                commands=["agent sync", "agent commit"],
                db_summary={"protocolEventStatuses": {"applied": 1}, "assetPaths": []},
                before_db_summary={"protocolEventStatuses": {"applied": 1}},
                command_records=[
                    {
                        "argv": [
                            "agent",
                            "sync",
                            "--agent",
                            "codex",
                            "--cwd",
                            ".",
                            "--query",
                            "What is a durable summary?",
                            "--format",
                            "packet",
                        ],
                        "returncode": 0,
                        "stdoutBytes": 1800,
                    },
                    {
                        "argv": ["agent", "commit", "--shape", "start-work", "--format", "packet"],
                        "returncode": 0,
                    },
                ],
            )

        self.assertIn("unexpected start-work commit in round without expected start_work", failures)

    def test_round_validation_flags_sync_packet_size_budget(self) -> None:
        from tests.e2e.live_task_continuity import LiveRoundScript, _validate_round

        with tempfile.TemporaryDirectory() as tmp:
            user_dir = Path(tmp)
            last_message = user_dir / "last-message.txt"
            last_message.write_text("LIVE_TASK_CONTINUITY_OK live-role round-04\nDone.\n", encoding="utf-8")

            failures = _validate_round(
                round_script=LiveRoundScript(4, "Checkpoint", "Preserve progress.", ("checkpoint",)),
                user_directory=user_dir,
                returncode=0,
                last_message_path=last_message,
                commands=["agent sync", "agent commit"],
                db_summary={"protocolEventStatuses": {"applied": 1}, "assetPaths": []},
                before_db_summary={"protocolEventStatuses": {"applied": 1}},
                command_records=[
                    {
                        "argv": [
                            "agent",
                            "sync",
                            "--agent",
                            "codex",
                            "--cwd",
                            ".",
                            "--query",
                            "Preserve progress.",
                            "--format",
                            "packet",
                        ],
                        "returncode": 0,
                        "stdoutBytes": 5200,
                    }
                ],
            )

        self.assertIn("sync packet exceeded compact byte budget: 5200 > 3600", failures)

    def test_round_validation_flags_workroot_asset_with_task_owner(self) -> None:
        from tests.e2e.live_task_continuity import LiveRoundScript, _validate_round

        with tempfile.TemporaryDirectory() as tmp:
            user_dir = Path(tmp)
            (user_dir / "results").mkdir()
            (user_dir / "results" / "summary.md").write_text("# Summary\n", encoding="utf-8")
            last_message = user_dir / "last-message.txt"
            last_message.write_text("LIVE_TASK_CONTINUITY_OK live-role round-30\nDone.\n", encoding="utf-8")

            failures = _validate_round(
                round_script=LiveRoundScript(
                    30,
                    "Cross-task summary",
                    "Create results/summary.md as a cross-task summary.",
                    ("asset",),
                    ("results/summary.md",),
                    (("results/summary.md", "workroot"),),
                ),
                user_directory=user_dir,
                returncode=0,
                last_message_path=last_message,
                commands=["agent sync", "agent commit"],
                db_summary={
                    "assetPaths": ["results/summary.md"],
                    "assetOwners": {"results/summary.md": ["Founder operating task"]},
                    "counts": {"protocolEvents": 1},
                    "protocolEventStatuses": {"applied": 1},
                },
            )

        self.assertIn("expected asset results/summary.md to be workroot-owned", "\n".join(failures))

    def test_round_validation_flags_rejected_commit_packet(self) -> None:
        from tests.e2e.live_task_continuity import LiveRoundScript, _validate_round

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            user_dir = root / "workspace"
            user_dir.mkdir()
            last_message = root / "last-message.txt"
            last_message.write_text("LIVE_TASK_CONTINUITY_OK live-role round-08\nDone.\n", encoding="utf-8")
            stdout_path = root / "commit-stdout.txt"
            stdout_path.write_text(
                '## Workroot Private Packet\n\n```json\n{"write":{"accepted":false,"status":"rejected"}}\n```\n',
                encoding="utf-8",
            )
            failures = _validate_round(
                round_script=LiveRoundScript(8, "Decision", "Decide.", ("decision",)),
                user_directory=user_dir,
                returncode=0,
                last_message_path=last_message,
                commands=["agent sync", "agent commit"],
                db_summary={"protocolEventStatuses": {"applied": 1}, "assetPaths": []},
                before_db_summary={"protocolEventStatuses": {"applied": 1}},
                command_records=[
                    {
                        "argv": ["agent", "sync", "--agent", "codex", "--cwd", ".", "--query", "Decide."],
                        "returncode": 0,
                    },
                    {
                        "argv": ["agent", "commit", "--shape", "decision", "--format", "packet"],
                        "returncode": 0,
                        "stdoutPath": str(stdout_path),
                    },
                ],
            )

        self.assertIn("Workroot commit was rejected: decision", failures)

    def test_round_validation_allows_rejected_commit_when_same_shape_recovers(self) -> None:
        from tests.e2e.live_task_continuity import LiveRoundScript, _validate_round

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            user_dir = root / "workspace"
            user_dir.mkdir()
            last_message = root / "last-message.txt"
            last_message.write_text("LIVE_TASK_CONTINUITY_OK live-role round-05\nDone.\n", encoding="utf-8")
            rejected_stdout = root / "rejected.txt"
            rejected_stdout.write_text(
                '## Workroot Private Packet\n\n```json\n{"write":{"accepted":false,"status":"rejected"}}\n```\n',
                encoding="utf-8",
            )
            accepted_stdout = root / "accepted.txt"
            accepted_stdout.write_text(
                '## Workroot Private Packet\n\n```json\n{"write":{"accepted":true,"status":"applied"}}\n```\n',
                encoding="utf-8",
            )
            failures = _validate_round(
                round_script=LiveRoundScript(5, "Asset", "Create asset.", ("asset",)),
                user_directory=user_dir,
                returncode=0,
                last_message_path=last_message,
                commands=["agent sync", "agent commit"],
                db_summary={"protocolEventStatuses": {"applied": 1}, "assetPaths": []},
                before_db_summary={"protocolEventStatuses": {"applied": 1}},
                command_records=[
                    {
                        "argv": ["agent", "sync", "--agent", "codex", "--cwd", ".", "--query", "Create asset."],
                        "returncode": 0,
                    },
                    {
                        "argv": ["agent", "commit", "--shape", "asset", "--format", "packet"],
                        "returncode": 0,
                        "stdoutPath": str(rejected_stdout),
                    },
                    {
                        "argv": ["agent", "commit", "--shape", "asset", "--format", "packet"],
                        "returncode": 0,
                        "stdoutPath": str(accepted_stdout),
                    },
                ],
            )

        self.assertNotIn("Workroot commit was rejected: asset", failures)

    def test_long_cycle_role_flags_task_proliferation(self) -> None:
        from tests.e2e.live_task_continuity import _validate_role_continuity, live_task_continuity_scenarios

        role = live_task_continuity_scenarios(round_count=10, role_slug="live-founder-operator")[0]
        final_db = {
            "counts": {
                "tasks": 40,
                "taskRuns": 40,
                "protocolEvents": 141,
                "handoffsCurrent": 1,
                "taskSummariesCurrent": 1,
            },
            "taskProliferation": {"activeNormalRootTasks": 40, "duplicateTitleCount": 8},
        }
        with tempfile.TemporaryDirectory() as tmp:
            user_dir = Path(tmp)
            (user_dir / "results").mkdir()
            (user_dir / "results" / "founder-operating-plan.md").write_text("# Plan\n", encoding="utf-8")
            failures = _validate_role_continuity(role=role, user_directory=user_dir, final_db=final_db)

        self.assertIn("task proliferation: active normal root tasks 40 exceeds 3", failures)

    def test_novice_role_flags_final_handoff_owner_drift(self) -> None:
        from tests.e2e.live_task_continuity import _validate_role_continuity, live_task_continuity_scenarios

        role = live_task_continuity_scenarios(round_count=20, role_slug="live-novice-chinese-shop-owner")[0]
        final_db = {
            "counts": {
                "tasks": 2,
                "taskRuns": 2,
                "protocolEvents": 20,
                "handoffsCurrent": 1,
                "taskSummariesCurrent": 1,
            },
            "taskProliferation": {"activeNormalRootTasks": 1, "duplicateTitleCount": 0},
            "assetPaths": ["outputs/shop-month-plan.md", "outputs/朋友圈文案.md", "outputs/下周复盘表.md"],
            "assetOwners": {},
            "latestHandoff": {
                "taskId": "task-inbox",
                "taskTitle": "临时判断是否换桌",
                "currentState": "主线经营方向已经完成本轮讨论。",
                "nextAction": "下次先看经营结果。",
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            user_dir = Path(tmp)
            (user_dir / "outputs").mkdir()
            (user_dir / "outputs" / "shop-month-plan.md").write_text("# Plan\n", encoding="utf-8")
            (user_dir / "outputs" / "朋友圈文案.md").write_text("# Copy\n", encoding="utf-8")
            (user_dir / "outputs" / "下周复盘表.md").write_text("# Review\n", encoding="utf-8")
            failures = _validate_role_continuity(role=role, user_directory=user_dir, final_db=final_db)

        self.assertIn("latest handoff owner drifted away from expected owner: 咖啡", failures)


class LiveTaskContinuityE2ETest(unittest.TestCase):
    def test_codex_five_roles_task_continuity(self) -> None:
        from tests.e2e.live_task_continuity import ROLE_ENV, ROUNDS_ENV, run_live_task_continuity, resolve_round_count

        require_e2e_runner_active(self, "live-task-continuity")
        run_root = os.environ.get("AI_WORKROOT_E2E_RUN_ROOT")
        sandbox_base = os.environ.get("AI_WORKROOT_E2E_SANDBOX_BASE")
        if not run_root or not sandbox_base:
            self.skipTest("live-task-continuity E2E must run through tests.e2e.runner")
        if os.environ.get("AI_WORKROOT_E2E_ALLOW_REMOTE_LLM") != "1":
            self.skipTest("remote LLM opt-in is required")

        result = run_live_task_continuity(run_root=Path(run_root), sandbox_base=Path(sandbox_base))

        self.assertEqual(result.returncode, 0, result.failure_report())
        report = json.loads(result.summary_path.read_text(encoding="utf-8"))
        expected_role = os.environ.get(ROLE_ENV)
        self.assertEqual(len(report["roleResults"]), 1 if expected_role else 5)
        if expected_role:
            self.assertEqual(report["roleResults"][0]["roleSlug"], expected_role)
        expected_rounds = resolve_round_count(os.environ.get(ROUNDS_ENV), single_role=bool(expected_role))
        self.assertTrue(all(role["roundCount"] >= expected_rounds for role in report["roleResults"]))


if __name__ == "__main__":
    unittest.main()
