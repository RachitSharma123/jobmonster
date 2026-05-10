import unittest

from jobmonster.detectors import (
    detect_platform,
    is_discovery_platform,
    is_external_portal,
    is_trusted_application_url,
)


class DetectionTests(unittest.TestCase):
    def test_detects_common_external_ats_urls(self):
        self.assertEqual(detect_platform("https://boards.greenhouse.io/acme/jobs/123"), "greenhouse")
        self.assertEqual(detect_platform("https://jobs.lever.co/acme/abc-123"), "lever")
        self.assertEqual(detect_platform("https://acme.wd3.myworkdayjobs.com/Careers/job/x"), "workday")
        self.assertEqual(detect_platform("https://jobs.smartrecruiters.com/Acme/123-role"), "smartrecruiters")
        self.assertEqual(detect_platform("https://acme.livehire.com/job/acme/123"), "livehire")

    def test_job_boards_are_not_treated_as_final_external_portals(self):
        self.assertEqual(detect_platform("https://www.seek.com.au/job/123"), "seek")
        self.assertEqual(detect_platform("https://au.indeed.com/viewjob?jk=abc"), "indeed")
        self.assertEqual(detect_platform("https://au.jora.com/job/abc"), "jora")
        self.assertEqual(detect_platform("https://www.adzuna.com.au/details/123"), "adzuna")
        self.assertEqual(detect_platform("https://www.careerone.com.au/job/abc"), "careerone")
        self.assertFalse(is_external_portal("https://au.indeed.com/viewjob?jk=abc"))
        self.assertTrue(is_external_portal("https://jobs.lever.co/acme/abc-123"))

    def test_trusted_application_gate(self):
        self.assertTrue(is_trusted_application_url("https://jobs.lever.co/acme/abc-123"))
        self.assertTrue(is_trusted_application_url("https://boards.greenhouse.io/acme/jobs/123"))
        self.assertFalse(is_trusted_application_url("https://www.adzuna.com.au/details/123"))
        self.assertFalse(is_trusted_application_url("https://company.example/careers/123"))
        self.assertTrue(is_discovery_platform("https://www.seek.com.au/job/123"))
        self.assertTrue(is_discovery_platform("https://www.linkedin.com/jobs/view/123"))


if __name__ == "__main__":
    unittest.main()
