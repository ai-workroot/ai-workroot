"""Reusable personas for Clean Workroot end-to-end tests."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Persona:
    slug: str
    name: str
    workroot_id: str
    native_agent_entry: bool
    user_files: dict[str, str]
    protected_phrase: str = ""
    protection: str = "none"


PERSONAS: tuple[Persona, ...] = (
    Persona(
        slug="persona-software-engineer",
        name="E2E Software Engineer",
        workroot_id="wr_e2e_software_engineer",
        native_agent_entry=False,
        user_files={
            "README.md": "# Service Refactor\n\nClean Mode context and migration notes.\n",
            "sample-env.txt": "SAMPLE_VALUE=example\n",
        },
    ),
    Persona(
        slug="persona-founder-operator",
        name="E2E Founder Operator",
        workroot_id="wr_e2e_founder_operator",
        native_agent_entry=True,
        user_files={
            "pricing-notes.md": "# Pricing Notes\n\nEnterprise plan risk and customer feedback.\n",
            "customer-feedback.csv": "account,signal\nalpha,needs onboarding\n",
        },
    ),
    Persona(
        slug="persona-researcher",
        name="E2E Researcher",
        workroot_id="wr_e2e_researcher",
        native_agent_entry=False,
        user_files={
            "citations.bib": "@article{clean2026,title={Clean Workroot Retrieval}}\n",
            "literature-notes.md": "# Literature Notes\n\nExplainable retrieval beats hidden magic.\n",
        },
    ),
    Persona(
        slug="persona-writer-creator",
        name="E2E Writer Creator",
        workroot_id="wr_e2e_writer_creator",
        native_agent_entry=True,
        user_files={
            "draft-outline.md": "# Draft Outline\n\nChapter arcs and revision plan.\n",
            "deleted-draft.md": "Old deleted draft placeholder; protected content must not leak.\n",
        },
        protected_phrase="WRITER_PROTECTED_DELETED_DRAFT",
        protection="deleted",
    ),
    Persona(
        slug="persona-nontechnical-learner",
        name="E2E Learner",
        workroot_id="wr_e2e_learner",
        native_agent_entry=False,
        user_files={
            "study-plan.md": "# Study Plan\n\nSmall daily lessons and review checkpoints.\n",
            "questions.md": "# Questions\n\nWhat should I do next?\n",
        },
    ),
)
