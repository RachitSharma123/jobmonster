from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from jobmonster.adapters.base import ApplyAdapter
from jobmonster.detectors import detect_platform
from jobmonster.models import ApplyMode, ApplyPlan, CandidateProfile, Documents, JobLead, Question


class GreenhouseAdapter(ApplyAdapter):
    name = "greenhouse"
    default_mode = ApplyMode.PREPARE

    def can_handle(self, job: JobLead, page_text: str = "") -> bool:
        return detect_platform(job.apply_url, page_text) == self.name

    def build_plan(self, job: JobLead, candidate: CandidateProfile, docs: Documents) -> ApplyPlan:
        board_token, job_id = self._parse_url(job.apply_url)
        endpoint = None
        warnings: list[str] = []
        if board_token and job_id:
            endpoint = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs/{job_id}"
            warnings.append("Direct Greenhouse API submission requires the employer's Job Board API key.")
        else:
            warnings.append("Could not parse Greenhouse board token or job id; use browser-assisted fill.")

        query = parse_qs(urlparse(job.apply_url).query)
        fields = {
            "first_name": candidate.first_name,
            "last_name": candidate.last_name,
            "email": candidate.email,
            "phone": candidate.phone,
            "location": candidate.location,
            "notice_period": candidate.notice_period,
            "salary_expectation": candidate.salary_expectation,
            "work_authorization": "Yes" if candidate.work_authorized else "No",
            "sponsorship": "Yes" if candidate.needs_sponsorship else "No",
        }
        if candidate.linkedin:
            fields["urls[LinkedIn]"] = candidate.linkedin
            fields["linkedin"] = candidate.linkedin
        if candidate.website:
            fields["urls[Portfolio]"] = candidate.website
            fields["website"] = candidate.website
        if "gh_src" in query:
            fields["mapped_url_token"] = query["gh_src"][0]
        fields.update(candidate.custom_answers)

        files = {"resume": docs.resume}
        if docs.cover_letter:
            files["cover_letter"] = docs.cover_letter

        return ApplyPlan(
            adapter=self.name,
            mode=self.default_mode,
            job=job,
            endpoint=endpoint,
            fields=fields,
            files={k: Path(v) for k, v in files.items()},
            questions=(
                Question("work_authorization", "Are you legally authorized to work?", required=True),
                Question("sponsorship", "Will you now or in the future require sponsorship?", required=True),
            ),
            warnings=tuple(warnings),
        )

    @staticmethod
    def _parse_url(url: str) -> tuple[str, str]:
        parsed = urlparse(url)
        parts = [p for p in parsed.path.split("/") if p]
        if "greenhouse.io" in parsed.netloc:
            # Path: /company/jobs/id or /company/jobs/id?...
            if len(parts) >= 3 and parts[1] == "jobs":
                return parts[0], re.sub(r"\D.*$", "", parts[2])
            # Query params: ?for=company&job_id=id
            qs = parse_qs(parsed.query)
            for_val = qs.get("for", [""])[0]
            job_id_val = qs.get("job_id", [""])[0]
            if for_val and job_id_val:
                return for_val, job_id_val
        return "", ""

