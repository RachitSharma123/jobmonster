from __future__ import annotations

import json
import time
import urllib.request
from typing import Any

AU_LEVER_COMPANIES = [
    "atlassian", "canva", "xero", "safety-culture", "coverhero",
    "whispir", "employmenthero", "autopilot", "buildkite", "rezdy",
    "iress", "elmo", "brighte", "harmoney", "immutable",
    "flare", "knowit", "data61", "quantium", "pexa",
    "healthengine", "prospa", "simplero", "myobapps",
    "airtasker", "siteminder", "airwallex", "payhero",
    "practice-ignition", "zip", "tyro", "go1", "culture-amp",
    "enboarder", "up", "equiem", "hyper", "atlassianteam",
]

import re as _re

AI_PATTERNS = _re.compile(
    r"\bai\b|\bml\b|\bllm\b|\bnlp\b|\bgpt\b|machine learning|deep learning"
    r"|data science|mlops|artificial intelligence|computer vision|generative ai"
    r"|neural network|automation engineer|agentic|python developer|python engineer",
    _re.IGNORECASE,
)

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
}

BASE = "https://api.lever.co/v0/postings"


def scrape_lever(
    companies: list[str] | None = None,
    delay: float = 0.5,
) -> list[dict[str, Any]]:
    companies = companies or AU_LEVER_COMPANIES
    jobs: list[dict[str, Any]] = []

    for company in companies:
        batch = _fetch_company(company)
        jobs.extend(batch)
        if batch:
            print(f"[lever] {company}: {len(batch)} matching jobs")
        time.sleep(delay)

    return jobs


def _fetch_company(company: str) -> list[dict[str, Any]]:
    url = f"{BASE}/{company}?mode=json"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        if isinstance(data, list):
            return [_normalize(j, company) for j in data if _matches(j)]
        return []
    except urllib.error.HTTPError as e:
        if e.code != 404:
            print(f"[lever] {company}: HTTP {e.code}")
        return []
    except Exception as e:
        print(f"[lever] {company}: {e}")
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
    title = job.get('text', '')
    if _EXCLUDE_TITLES.search(title):
        return False
    return bool(_TITLE_PAT.search(title))


def _normalize(job: dict, company: str) -> dict[str, Any]:
    categories = job.get("categories", {})
    location = categories.get("location", categories.get("allLocations", [""])[0] if categories.get("allLocations") else "")

    return {
        "job_id": f"lever_{job['id']}",
        "title": job.get("text", ""),
        "company": company,
        "location": location,
        "salary": "",
        "source": "lever",
        "apply_url": job.get("hostedUrl", f"https://jobs.lever.co/{company}/{job['id']}"),
        "description": job.get("descriptionPlain", "")[:500],
        "remote": "remote" in (job.get("text", "") + job.get("descriptionPlain", "")).lower(),
        "posted": "",
    }
