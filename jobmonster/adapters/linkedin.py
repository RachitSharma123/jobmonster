from __future__ import annotations

from jobmonster.adapters.base import ApplyAdapter
from jobmonster.detectors import detect_platform
from jobmonster.models import ApplyMode, ApplyPlan, CandidateProfile, Documents, JobLead
from pathlib import Path


class LinkedInAdapter(ApplyAdapter):
    name = "linkedin"
    default_mode = ApplyMode.ASSISTED

    def can_handle(self, job: JobLead, page_text: str = "") -> bool:
        return detect_platform(job.apply_url) == "linkedin"

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
            warnings=("LinkedIn: will click Apply button then fill the form that appears.",),
        )
