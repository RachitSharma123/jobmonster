from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jobmonster.models import ApplyPlan, CandidateProfile, Documents, JobLead


def load_candidate(path: Path) -> CandidateProfile:
    data = json.loads(path.read_text())
    return CandidateProfile(
        first_name=data["first_name"],
        last_name=data["last_name"],
        email=data["email"],
        phone=data["phone"],
        location=data.get("location", ""),
        linkedin=data.get("linkedin", ""),
        website=data.get("website", ""),
        work_authorized=bool(data.get("work_authorized", True)),
        needs_sponsorship=bool(data.get("needs_sponsorship", False)),
        notice_period=data.get("notice_period", "2 weeks"),
        salary_expectation=data.get("salary_expectation", ""),
        custom_answers=data.get("custom_answers", {}),
    )


def load_jobs(path: Path) -> list[JobLead]:
    data = json.loads(path.read_text())
    items = data if isinstance(data, list) else list(data.values())
    return [job_from_mapping(item) for item in items]


def job_from_mapping(data: dict[str, Any]) -> JobLead:
    return JobLead(
        title=data.get("title", ""),
        company=data.get("company", ""),
        apply_url=data.get("apply_url") or data.get("url") or data.get("job_url", ""),
        location=data.get("location", ""),
        salary=data.get("salary", ""),
        source=data.get("source", ""),
        description=data.get("description", data.get("description_snippet", "")),
        metadata={k: v for k, v in data.items() if k not in {
            "title", "company", "apply_url", "url", "job_url", "location", "salary", "source",
            "description", "description_snippet",
        }},
    )


def make_documents(resume: Path, cover_letter: Path | None = None) -> Documents:
    if not resume.exists():
        raise FileNotFoundError(f"Resume not found: {resume}")
    if cover_letter and not cover_letter.exists():
        raise FileNotFoundError(f"Cover letter not found: {cover_letter}")
    return Documents(resume=resume, cover_letter=cover_letter)


def plan_to_dict(plan: ApplyPlan) -> dict[str, Any]:
    return {
        "adapter": plan.adapter,
        "mode": plan.mode.value,
        "job": {
            "title": plan.job.title,
            "company": plan.job.company,
            "apply_url": plan.job.apply_url,
            "location": plan.job.location,
            "salary": plan.job.salary,
            "source": plan.job.source,
        },
        "endpoint": plan.endpoint,
        "fields": plan.fields,
        "files": {key: str(path) for key, path in plan.files.items()},
        "questions": [
            {
                "key": question.key,
                "label": question.label,
                "required": question.required,
                "field_type": question.field_type,
                "options": list(question.options),
            }
            for question in plan.questions
        ],
        "warnings": list(plan.warnings),
    }

