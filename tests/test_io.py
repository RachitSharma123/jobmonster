from pathlib import Path
import json
import tempfile
import unittest

from jobmonster.io import load_candidate, load_jobs, make_documents


class IoTests(unittest.TestCase):
    def test_loads_candidate_and_jobs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidate_path = root / "candidate.json"
            jobs_path = root / "jobs.json"
            resume_path = root / "resume.pdf"
            resume_path.write_text("fake")
            candidate_path.write_text(json.dumps({
                "first_name": "Rachit",
                "last_name": "Sharma",
                "email": "rachit@example.com",
                "phone": "123",
                "custom_answers": {"notice": "2 weeks"},
            }))
            jobs_path.write_text(json.dumps([
                {"title": "Engineer", "company": "Acme", "url": "https://jobs.lever.co/acme/abc"}
            ]))

            candidate = load_candidate(candidate_path)
            jobs = load_jobs(jobs_path)
            docs = make_documents(resume_path)

            self.assertEqual(candidate.full_name, "Rachit Sharma")
            self.assertEqual(jobs[0].apply_url, "https://jobs.lever.co/acme/abc")
            self.assertEqual(docs.resume, resume_path)


if __name__ == "__main__":
    unittest.main()
