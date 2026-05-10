from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from jobmonster.adapters.base import ApplyAdapter
from jobmonster.detectors import detect_platform
from jobmonster.models import ApplyMode, ApplyPlan, CandidateProfile, Documents, JobLead, Question


class LeverAdapter(ApplyAdapter):
    name = "lever"
    default_mode = ApplyMode.PREPARE

    def can_handle(self, job: JobLead, page_text: str = "") -> bool:
        return detect_platform(job.apply_url, page_text) == self.name

    def build_plan(self, job: JobLead, candidate: CandidateProfile, docs: Documents) -> ApplyPlan:
        site, posting_id = self._parse_url(job.apply_url)
        endpoint = (
            f"https://api.lever.co/v0/postings/{site}/{posting_id}"
            if site and posting_id
            else None
        )
        warnings = [
            "Lever apply payloads are posting-specific; validate required custom questions before submission.",
        ]
        fields = {
            "name": candidate.full_name,
            "first_name": candidate.first_name,
            "last_name": candidate.last_name,
            "email": candidate.email,
            "phone": candidate.phone,
            "location": candidate.location,
            "urls[LinkedIn]": candidate.linkedin,
            "linkedin": candidate.linkedin,
            "urls[Portfolio]": candidate.website,
            "website": candidate.website,
            "notice_period": candidate.notice_period,
            "salary_expectation": candidate.salary_expectation,
            "work_authorization": "Yes" if candidate.work_authorized else "No",
            "sponsorship": "Yes" if candidate.needs_sponsorship else "No",
            **candidate.custom_answers,
        }
        files = {"resume": docs.resume}
        if docs.cover_letter:
            files["cover_letter"] = docs.cover_letter

        return ApplyPlan(
            adapter=self.name,
            mode=self.default_mode,
            job=job,
            endpoint=endpoint,
            fields={k: v for k, v in fields.items() if v},
            files={k: Path(v) for k, v in files.items()},
            questions=(
                Question("work_authorization", "Are you authorized to work?", required=True),
                Question("sponsorship", "Do you require visa sponsorship?", required=True),
            ),
            warnings=tuple(warnings),
        )

    @staticmethod
    def _parse_url(url: str) -> tuple[str, str]:
        parsed = urlparse(url)
        parts = [p for p in parsed.path.split("/") if p]
        if parsed.netloc.endswith("lever.co") and len(parts) >= 2:
            return parts[0], parts[1]
        return "", ""
