from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class ApplyMode(str, Enum):
    PREPARE = "prepare"
    ASSISTED = "assisted"
    SUBMIT = "submit"


class ApplyStatus(str, Enum):
    PREPARED = "prepared"
    NEEDS_REVIEW = "needs_review"
    SUBMITTED = "submitted"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass(frozen=True)
class JobLead:
    title: str
    company: str
    apply_url: str
    location: str = ""
    salary: str = ""
    source: str = ""
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CandidateProfile:
    first_name: str
    last_name: str
    email: str
    phone: str
    location: str = ""
    linkedin: str = ""
    website: str = ""
    work_authorized: bool = True
    needs_sponsorship: bool = False
    notice_period: str = "2 weeks"
    salary_expectation: str = ""
    custom_answers: dict[str, str] = field(default_factory=dict)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


@dataclass(frozen=True)
class Documents:
    resume: Path
    cover_letter: Path | None = None


@dataclass(frozen=True)
class Question:
    key: str
    label: str
    required: bool = False
    field_type: str = "text"
    options: tuple[str, ...] = ()


@dataclass(frozen=True)
class ApplyPlan:
    adapter: str
    mode: ApplyMode
    job: JobLead
    endpoint: str | None
    fields: dict[str, Any]
    files: dict[str, Path]
    questions: tuple[Question, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class ApplyResult:
    status: ApplyStatus
    adapter: str
    job: JobLead
    message: str
    evidence: dict[str, Any] = field(default_factory=dict)

