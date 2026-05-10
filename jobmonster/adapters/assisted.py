from __future__ import annotations

from pathlib import Path

from jobmonster.adapters.base import ApplyAdapter
from jobmonster.detectors import detect_platform
from jobmonster.models import ApplyMode, ApplyPlan, CandidateProfile, Documents, JobLead, Question


class AssistedPortalAdapter(ApplyAdapter):
    """Browser-assisted adapter for portals that need account/session-specific steps."""

    def __init__(self, name: str, hosts: tuple[str, ...], warnings: tuple[str, ...]):
        self.name = name
        self.hosts = hosts
        self._warnings = warnings
        self.default_mode = ApplyMode.ASSISTED

    def can_handle(self, job: JobLead, page_text: str = "") -> bool:
        return detect_platform(job.apply_url, page_text) == self.name

    def build_plan(self, job: JobLead, candidate: CandidateProfile, docs: Documents) -> ApplyPlan:
        fields = {
            "first_name": candidate.first_name,
            "last_name": candidate.last_name,
            "name": candidate.full_name,
            "email": candidate.email,
            "phone": candidate.phone,
            "location": candidate.location,
            "linkedin": candidate.linkedin,
            "website": candidate.website,
            "work_authorization": "Yes" if candidate.work_authorized else "No",
            "sponsorship": "Yes" if candidate.needs_sponsorship else "No",
            "notice_period": candidate.notice_period,
            "salary_expectation": candidate.salary_expectation,
            **candidate.custom_answers,
        }
        files = {"resume": docs.resume}
        if docs.cover_letter:
            files["cover_letter"] = docs.cover_letter

        return ApplyPlan(
            adapter=self.name,
            mode=ApplyMode.ASSISTED,
            job=job,
            endpoint=job.apply_url,
            fields={k: v for k, v in fields.items() if v},
            files={k: Path(v) for k, v in files.items()},
            questions=(
                Question("account", "This portal may require an employer-specific account.", required=False),
                Question("custom_screening", "Review custom screening questions before submitting.", required=True),
            ),
            warnings=self._warnings,
        )


def assisted_adapters() -> list[AssistedPortalAdapter]:
    return [
        AssistedPortalAdapter(
            "workday",
            ("myworkdayjobs.com", "workdayjobs.com"),
            (
                "Workday is tenant-specific and usually requires a candidate account.",
                "Prepare fields and files, fill with browser automation, then pause for review.",
            ),
        ),
        AssistedPortalAdapter(
            "smartrecruiters",
            ("smartrecruiters.com",),
            (
                "SmartRecruiters forms vary by employer and may include knockout questions.",
                "Use assisted fill and approval before final submit.",
            ),
        ),
        AssistedPortalAdapter(
            "livehire",
            ("livehire.com", "humanforce.com"),
            (
                "LiveHire/Humanforce often requires consent and account steps.",
                "Use assisted fill and approval before final submit.",
            ),
        ),
        AssistedPortalAdapter(
            "ashby",
            ("ashbyhq.com",),
            (
                "Ashby forms are structured but question sets vary by job.",
                "Use assisted fill and approval before final submit.",
            ),
        ),
        AssistedPortalAdapter(
            "breezy",
            ("breezy.hr",),
            (
                "Breezy forms are usually simple, but attachments and custom questions vary.",
                "Use assisted fill and approval before final submit.",
            ),
        ),
        AssistedPortalAdapter(
            "jobadder",
            ("jobadder.com",),
            (
                "JobAdder forms often redirect through recruiter-specific flows.",
                "Use assisted fill and approval before final submit.",
            ),
        ),
        AssistedPortalAdapter(
            "pageup",
            ("pageuppeople.com",),
            (
                "PageUp commonly has multi-step profile and screening pages.",
                "Use assisted fill and approval before final submit.",
            ),
        ),
    ]

