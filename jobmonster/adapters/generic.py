from __future__ import annotations

from pathlib import Path

from jobmonster.adapters.base import ApplyAdapter
from jobmonster.detectors import detect_platform
from jobmonster.models import ApplyMode, ApplyPlan, CandidateProfile, Documents, JobLead, Question


class GenericFormAdapter(ApplyAdapter):
    name = "generic"
    default_mode = ApplyMode.ASSISTED

    def can_handle(self, job: JobLead, page_text: str = "") -> bool:
        return detect_platform(job.apply_url, page_text) == "generic"

    def build_plan(self, job: JobLead, candidate: CandidateProfile, docs: Documents) -> ApplyPlan:
        files = {"resume": docs.resume}
        if docs.cover_letter:
            files["cover_letter"] = docs.cover_letter
        return ApplyPlan(
            adapter=self.name,
            mode=ApplyMode.ASSISTED,
            job=job,
            endpoint=job.apply_url,
            fields={
                "name": candidate.full_name,
                "email": candidate.email,
                "phone": candidate.phone,
                "location": candidate.location,
                "linkedin": candidate.linkedin,
                "website": candidate.website,
            },
            files={k: Path(v) for k, v in files.items()},
            questions=(Question("review", "Unknown form; review all filled values before submitting.", required=True),),
            warnings=("Unknown application portal; this must run in approval-gated assisted mode.",),
        )

