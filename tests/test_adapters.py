from pathlib import Path
import unittest

from jobmonster.adapters.registry import default_registry
from jobmonster.models import ApplyMode, CandidateProfile, Documents, JobLead


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.candidate = CandidateProfile(
            first_name="Rachit",
            last_name="Sharma",
            email="rachit@example.com",
            phone="+61400000000",
            location="Melbourne, VIC",
            linkedin="https://linkedin.example/rachit",
            website="https://rachit.example",
            salary_expectation="100000",
        )
        self.docs = Documents(resume=Path("/tmp/resume.pdf"), cover_letter=Path("/tmp/cover.pdf"))

    def test_greenhouse_plan_parses_api_endpoint(self):
        job = JobLead("Engineer", "Acme", "https://boards.greenhouse.io/acme/jobs/123456?gh_src=abc")
        adapter = default_registry().resolve(job)
        plan = adapter.build_plan(job, self.candidate, self.docs)

        self.assertEqual(plan.adapter, "greenhouse")
        self.assertEqual(plan.mode, ApplyMode.PREPARE)
        self.assertEqual(plan.endpoint, "https://boards-api.greenhouse.io/v1/boards/acme/jobs/123456")
        self.assertEqual(plan.fields["mapped_url_token"], "abc")
        self.assertIn("resume", plan.files)

    def test_lever_plan_parses_endpoint(self):
        job = JobLead("Engineer", "Acme", "https://jobs.lever.co/acme/posting-abc")
        adapter = default_registry().resolve(job)
        plan = adapter.build_plan(job, self.candidate, self.docs)

        self.assertEqual(plan.adapter, "lever")
        self.assertEqual(plan.endpoint, "https://api.lever.co/v0/postings/acme/posting-abc")
        self.assertEqual(plan.fields["name"], "Rachit Sharma")
        self.assertIn("cover_letter", plan.files)

    def test_workday_routes_to_assisted_mode(self):
        job = JobLead("Engineer", "Acme", "https://acme.wd3.myworkdayjobs.com/Careers/job/Melbourne/123")
        adapter = default_registry().resolve(job)
        plan = adapter.build_plan(job, self.candidate, self.docs)

        self.assertEqual(plan.adapter, "workday")
        self.assertEqual(plan.mode, ApplyMode.ASSISTED)
        self.assertIn("resume", plan.files)
        self.assertTrue(plan.warnings)


if __name__ == "__main__":
    unittest.main()
