from __future__ import annotations

import os
import time
from typing import Any

import urllib.request
import urllib.parse
import json

JSEARCH_KEY = os.getenv("JSEARCH_API_KEY", "ak_hw2mvmtun5kfgo9j8nwx7mtpkdf8waus4u541v2j5po0nsc")
JSEARCH_BASE = os.getenv("JSEARCH_BASE_URL", "https://jsearch.p.rapidapi.com")

QUERIES = [
    "AI Engineer Australia",
    "Machine Learning Engineer Australia",
    "Python Developer AI Australia",
    "Automation Engineer AI Australia",
    "MLOps Engineer Australia",
    "Data Engineer AI Australia",
    "LLM Engineer Australia",
    "AI Developer Melbourne",
    "Software Engineer AI Melbourne",
    "Agentic AI Developer Australia",
]


def scrape_jsearch(
    queries: list[str] | None = None,
    pages_per_query: int = 3,
    country: str = "AU",
    delay: float = 1.2,
) -> list[dict[str, Any]]:
    if not JSEARCH_KEY:
        print("[jsearch] missing JSEARCH_API_KEY; skipping JSearch")
        return []

    from jobmonster.quota import check_quota, record as quota_record

    queries = queries or QUERIES
    seen: set[str] = set()
    jobs: list[dict[str, Any]] = []
    total_requests = len(queries) * pages_per_query

    if not check_quota("jsearch", total_requests):
        return []

    for query in queries:
        for page in range(1, pages_per_query + 1):
            quota_record("jsearch", 1)
            batch = _fetch_page(query, page, country)
            for raw in batch:
                job_id = raw.get("job_id", "")
                if job_id in seen:
                    continue
                seen.add(job_id)
                normalized = _normalize(raw)
                if normalized["apply_url"]:
                    jobs.append(normalized)
            time.sleep(delay)

    return jobs


def _fetch_page(query: str, page: int, country: str) -> list[dict]:
    params = urllib.parse.urlencode({
        "query": query,
        "page": page,
        "num_pages": 1,
        "country": country,
        "date_posted": "month",
    })
    url = f"{JSEARCH_BASE}/search-v2?{params}"
    req = urllib.request.Request(url, headers={
        "x-api-key": JSEARCH_KEY,
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            return data.get("data", [])
    except Exception as e:
        print(f"[jsearch] page {page} query={query!r} error: {e}")
        return []


def _normalize(raw: dict) -> dict[str, Any]:
    apply_url = raw.get("job_apply_link") or ""
    return {
        "job_id": raw.get("job_id", ""),
        "title": raw.get("job_title", ""),
        "company": raw.get("employer_name", ""),
        "location": _location(raw),
        "salary": _salary(raw),
        "source": raw.get("job_publisher", ""),
        "apply_url": apply_url,
        "description": (raw.get("job_description") or "")[:500],
        "employment_type": raw.get("job_employment_type", ""),
        "remote": raw.get("job_is_remote", False),
        "posted": raw.get("job_posted_at_datetime_utc", ""),
    }


def _location(raw: dict) -> str:
    parts = [raw.get("job_city"), raw.get("job_state"), raw.get("job_country")]
    return ", ".join(p for p in parts if p)


def _salary(raw: dict) -> str:
    lo = raw.get("job_min_salary")
    hi = raw.get("job_max_salary")
    period = raw.get("job_salary_period", "")
    if lo and hi:
        return f"{lo}–{hi} {period}".strip()
    if lo:
        return f"{lo}+ {period}".strip()
    return ""
