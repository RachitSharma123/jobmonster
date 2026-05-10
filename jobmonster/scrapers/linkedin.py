from __future__ import annotations

import re
import time
import urllib.parse
import urllib.request
from html import unescape
from typing import Any

LI_QUERIES = [
    "AI Engineer",
    "Machine Learning Engineer",
    "LLM Engineer",
    "MLOps Engineer",
    "Python Developer AI",
    "Automation Engineer AI",
    "AI Developer",
    "Software Engineer Machine Learning",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-AU,en;q=0.9",
}

BASE = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"


def scrape_linkedin(
    queries: list[str] | None = None,
    pages_per_query: int = 2,
    headless: bool = True,
) -> list[dict[str, Any]]:
    queries = queries or LI_QUERIES
    seen: set[str] = set()
    jobs: list[dict[str, Any]] = []

    for query in queries:
        for page in range(pages_per_query):
            batch = _fetch_page(query, start=page * 10)
            for job in batch:
                jid = job["job_id"]
                if jid in seen:
                    continue
                seen.add(jid)
                jobs.append(job)
            time.sleep(1.5)

    return jobs


def _fetch_page(query: str, start: int) -> list[dict]:
    params = urllib.parse.urlencode({
        "keywords": query,
        "location": "Australia",
        "start": start,
        "count": 10,
        "f_TPR": "r2592000",  # last 30 days
    })
    url = f"{BASE}?{params}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            html = r.read().decode("utf-8", errors="ignore")
        return _parse_jobs(html)
    except Exception as e:
        print(f"[linkedin] error query={query!r} start={start}: {e}")
        return []


def _parse_jobs(html: str) -> list[dict]:
    jobs = []
    blocks = re.split(r"<li>", html)[1:]
    for block in blocks:
        job_id_m = re.search(r'urn:li:jobPosting:(\d+)', block)
        if not job_id_m:
            continue
        job_id = job_id_m.group(1)

        href_m = re.search(r'href="(https://[a-z]+\.linkedin\.com/jobs/view/[^"]+)"', block)
        apply_url = href_m.group(1).split("?")[0] if href_m else f"https://www.linkedin.com/jobs/view/{job_id}"

        title_m = re.search(r'class="sr-only">\s*(.*?)\s*</span>', block, re.DOTALL)
        title = unescape(title_m.group(1).strip()) if title_m else ""

        company_m = re.search(r'class="[^"]*base-search-card__subtitle[^"]*"[^>]*>\s*<a[^>]*>([^<]+)<', block)
        if not company_m:
            company_m = re.search(r'class="[^"]*hidden-nested-link[^"]*"[^>]*>([^<]+)<', block)
        company = unescape(company_m.group(1).strip()) if company_m else ""

        location_m = re.search(r'class="[^"]*job-search-card__location[^"]*"[^>]*>([^<]+)<', block)
        location = unescape(location_m.group(1).strip()) if location_m else "Australia"

        if not title:
            continue

        jobs.append({
            "job_id": job_id,
            "title": title,
            "company": company,
            "location": location,
            "salary": "",
            "source": "linkedin",
            "apply_url": apply_url,
            "description": "",
            "remote": "remote" in block.lower(),
        })

    return jobs


async def resolve_apply_urls(jobs: list[dict], headless: bool = True) -> list[dict]:
    """Disabled: LinkedIn apply resolution requires login/session-gated browser flows."""
    print("[linkedin] resolver disabled; LinkedIn remains discovery-only")
    return [
        {
            **job,
            "application_ready": False,
            "skip_reason": "LinkedIn is discovery-only; use a direct employer ATS URL",
        }
        for job in jobs
    ]
