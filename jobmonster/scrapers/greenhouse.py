from __future__ import annotations

import json
import time
import urllib.request
import urllib.parse
from typing import Any

AU_GREENHOUSE_COMPANIES = [
    "atlassian", "canva", "safetyculture", "xero", "envato", "afterpay",
    "go1", "cultureamp", "airtasker", "tyrohealth", "nearmap", "compumedics",
    "employmenthero", "buildkite", "autopilothq", "whispir", "simpro",
    "brighte", "harmoney", "prospa", "zip-co", "airwallex", "practice-ignition",
    "squarespace", "netlify", "bugsnag", "coverhero", "immutable",
    "elmo-software", "flare-hr", "knowit", "siteminder", "pexa-group",
    "lendi-group", "coupa", "myob", "iress", "fintech-au",
    "quantium", "deloitte-au", "pwcau", "thoughtworks",
    "healthengine", "rezdy", "monash", "rmit", "anz-banking-group",
    "cochlear", "bluescope", "csiro", "data61",
]

import re as _re

AI_KEYWORDS = [
    r"\bai\b", r"\bml\b", r"\bllm\b", r"\bnlp\b", r"\bgpt\b",
    r"machine learning", r"deep learning", r"data science", r"mlops",
    r"artificial intelligence", r"computer vision", r"generative ai",
    r"neural network", r"automation engineer", r"agentic",
    r"python developer", r"python engineer",
]

def _keyword_re() -> _re.Pattern:
    return _re.compile("|".join(AI_KEYWORDS), _re.IGNORECASE)

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
}

BASE = "https://boards-api.greenhouse.io/v1/boards"


_PAT = _keyword_re()


def scrape_greenhouse(
    companies: list[str] | None = None,
    delay: float = 0.5,
) -> list[dict[str, Any]]:
    companies = companies or AU_GREENHOUSE_COMPANIES
    jobs: list[dict[str, Any]] = []

    for company in companies:
        batch = _fetch_company(company)
        jobs.extend(batch)
        if batch:
            print(f"[greenhouse] {company}: {len(batch)} matching jobs")
        time.sleep(delay)

    return jobs


def _fetch_company(company: str) -> list[dict[str, Any]]:
    url = f"{BASE}/{company}/jobs?content=true"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        all_jobs = data.get("jobs", [])
        return [_normalize(j, company) for j in all_jobs if _matches(j)]
    except urllib.error.HTTPError as e:
        if e.code != 404:
            print(f"[greenhouse] {company}: HTTP {e.code}")
        return []
    except Exception as e:
        print(f"[greenhouse] {company}: {e}")
        return []


_TITLE_PAT = _re.compile(
    r"\bai\b|\bml\b|\bllm\b|\bnlp\b|\bgpt\b|machine learning|deep learning"
    r"|data science|mlops|artificial intelligence|computer vision|generative ai"
    r"|neural network|automation engineer|agentic|python developer|python engineer"
    r"|data engineer|analytics engineer|software engineer|platform engineer|backend engineer",
    _re.IGNORECASE,
)

_EXCLUDE_TITLES = _re.compile(
    r"marketing|sales|finance|financial|accounting|legal|hr |human resources"
    r"|recruiter|talent|compliance|operations manager|product manager|product marketing"
    r"|customer success|support specialist|office manager|executive|director of",
    _re.IGNORECASE,
)


def _matches(job: dict) -> bool:
    title = job.get('title', '')
    if _EXCLUDE_TITLES.search(title):
        return False
    return bool(_TITLE_PAT.search(title))


def _normalize(job: dict, company: str) -> dict[str, Any]:
    location = ""
    offices = job.get("offices") or job.get("location", {})
    if isinstance(offices, list) and offices:
        location = offices[0].get("name", "")
    elif isinstance(offices, dict):
        location = offices.get("name", "")

    return {
        "job_id": f"greenhouse_{job['id']}",
        "title": job.get("title", ""),
        "company": company,
        "location": location,
        "salary": "",
        "source": "greenhouse",
        "apply_url": job.get("absolute_url", f"https://job-boards.greenhouse.io/{company}/jobs/{job['id']}"),
        "description": _strip_html(job.get("content", ""))[:500],
        "remote": "remote" in (job.get("title", "") + job.get("content", "")).lower(),
        "posted": job.get("updated_at", ""),
    }


def _strip_html(html: str) -> str:
    import re
    return re.sub(r"<[^>]+>", " ", html).strip()
