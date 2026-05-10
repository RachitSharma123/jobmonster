from pathlib import Path
import unittest

from jobmonster.adapters.base import AdapterRegistry
from jobmonster.adapters.registry import default_registry
from jobmonster.models import ApplyMode, ApplyPlan, CandidateProfile, Documents, JobLead


class DummyAdapter:
    name = "dummy"

    def can_handle(self, job, page_text=""):
        return "dummy" in job.apply_url

    def build_plan(self, job, candidate, docs):
        return ApplyPlan(
            adapter=self.name,
            mode=ApplyMode.PREPARE,
            job=job,
            endpoint=None,
            fields={},
            files={},
        )


class RegistryTests(unittest.TestCase):
    def test_registry_resolves_first_matching_adapter(self):
        registry = AdapterRegistry([DummyAdapter()])
        job = JobLead(title="Role", company="Acme", apply_url="https://dummy.example/job")
        candidate = CandidateProfile(first_name="A", last_name="B", email="a@b.test", phone="1")
        docs = Documents(resume=Path(__file__))

        adapter = registry.resolve(job)
        plan = adapter.build_plan(job, candidate, docs)

        self.assertEqual(adapter.name, "dummy")
        self.assertEqual(plan.adapter, "dummy")

    def test_default_registry_excludes_discovery_and_unknown_forms(self):
        names = default_registry().names()

        self.assertNotIn("adzuna", names)
        self.assertNotIn("linkedin", names)
        self.assertNotIn("generic", names)

    def test_generic_forms_are_explicit_opt_in(self):
        names = default_registry(allow_generic=True).names()

        self.assertIn("generic", names)


if __name__ == "__main__":
    unittest.main()
