"""Canonical PRD element catalog.

Judgement of quality lives in ``prompts/agents/prd-*.md``. This module is the
fact layer: ids, requiredness, and the heading/body signals the mapper uses to
find elements in any product repo.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple


@dataclass(frozen=True)
class PrdElement:
    id: str
    name: str
    required: str  # must | should | could
    heading_aliases: Tuple[str, ...]
    body_signals: Tuple[str, ...]


ELEMENTS: Tuple[PrdElement, ...] = (
    PrdElement(
        "document_control",
        "Document Control",
        "must",
        ("document control", "status", "version", "owner", "reviewers", "author"),
        ("approval status", "living document", "version:"),
    ),
    PrdElement(
        "executive_summary",
        "Executive Summary",
        "must",
        ("executive summary", "overview", "value proposition", "product summary"),
        ("core value", "value proposition", "this product"),
    ),
    PrdElement(
        "problem",
        "Problem Statement",
        "must",
        ("why", "problem statement", "problem", "pain", "hypothesis"),
        ("who is affected", "why now", "key hypothesis", "pain point"),
    ),
    PrdElement(
        "personas",
        "Users / Personas",
        "must",
        ("persona", "personas", "target users", "jobs to be done", "user goals"),
        ("jobs to be done", "pain point", "primary user"),
    ),
    PrdElement(
        "mvp",
        "MVP / Scope",
        "must",
        ("mvp", "scope", "moscow", "must have", "feature prioritization"),
        ("p0", "must have", "should have", "won't have", "minimum viable"),
    ),
    PrdElement(
        "oos",
        "Out of Scope",
        "must",
        ("out of scope", "oos", "non-goals", "non goals", "won't have"),
        ("out of scope", "we are not", "explicitly excluded"),
    ),
    PrdElement(
        "success",
        "Success Criteria",
        "must",
        ("success criteria", "definition of done", "north star", "kpis"),
        ("north star", "definition of done", "success metric", "measurable"),
    ),
    PrdElement(
        "ux",
        "UX / User Flows",
        "should",
        ("ux", "user experience", "user flow", "user flows", "happy path"),
        ("trigger:", "user action", "failure mode", "reversibility"),
    ),
    PrdElement(
        "api",
        "API",
        "should",
        ("api", "endpoints", "atomic programmable"),
        ("http", "endpoint", "openapi", "authentication"),
    ),
    PrdElement(
        "nfr",
        "Non-Functional Requirements",
        "should",
        ("nfr", "non-functional", "performance", "reliability", "slo"),
        ("p99", "uptime", "latency", "throughput"),
    ),
    PrdElement(
        "edge",
        "Edge Cases / Dependencies",
        "should",
        ("edge", "exceptions", "dependencies", "gotchas", "constraints"),
        ("mitigation", "fallback", "dependency"),
    ),
    PrdElement(
        "architecture",
        "Technical Architecture",
        "should",
        ("architecture", "technical architecture", "system design"),
        ("service", "component", "stack"),
    ),
    PrdElement(
        "testing",
        "Testing & Validation",
        "should",
        ("testing", "validation", "test pyramid", "qa"),
        ("unit test", "acceptance criteria", "hypothesis validation"),
    ),
    PrdElement(
        "security",
        "Security & Privacy",
        "should",
        ("security", "privacy", "threat model"),
        ("encryption", "tls", "pii", "retention"),
    ),
    PrdElement(
        "roadmap",
        "Roadmap",
        "should",
        ("roadmap", "timeline", "milestones"),
        ("alpha", "beta", "ga", "exit criteria"),
    ),
    PrdElement(
        "risks",
        "Risks",
        "should",
        ("risks", "risk register"),
        ("probability", "mitigation", "trigger"),
    ),
    PrdElement(
        "user_stories",
        "User Stories",
        "could",
        ("user stories", "user story", "acceptance criteria"),
        ("as a ", "i want", "so that"),
    ),
    PrdElement(
        "data_models",
        "Data Models",
        "could",
        ("data models", "entities", "schema"),
        ("primary key", "entity", "relationship"),
    ),
    PrdElement(
        "integrations",
        "Integrations",
        "could",
        ("integration", "integrations", "connectors"),
        ("webhook", "oauth", "third-party"),
    ),
    PrdElement(
        "gtm",
        "Go-To-Market",
        "could",
        ("go-to-market", "gtm", "pricing", "positioning"),
        ("pricing", "launch", "channel"),
    ),
    PrdElement(
        "appendix",
        "Appendix",
        "could",
        ("appendix", "glossary", "decision log", "changelog", "references"),
        ("glossary", "decision log"),
    ),
)

ELEMENT_BY_ID = {e.id: e for e in ELEMENTS}
MUST_IDS = tuple(e.id for e in ELEMENTS if e.required == "must")
SHOULD_IDS = tuple(e.id for e in ELEMENTS if e.required == "should")
COULD_IDS = tuple(e.id for e in ELEMENTS if e.required == "could")


def all_ids() -> List[str]:
    return [e.id for e in ELEMENTS]
