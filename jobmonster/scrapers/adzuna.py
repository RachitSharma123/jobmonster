from __future__ import annotations

import time
import urllib.parse
import urllib.request
import json
import os
from typing import Any

APP_ID = os.getenv("ADZUNA_APP_ID", "")
APP_KEY = os.getenv("ADZUNA_APP_KEY", "")
BASE = "https://api.adzuna.com/v1/api/jobs/au/search"

QUERIES = [
    "AI Engineer",
    "Machine Learning Engineer",
    "Python Developer AI",
    "LLM Engineer",
    "MLOps Engineer",
    "Automation Engineer Python",
    "AI Developer",
    "Data Engineer AI",
    "Software Engineer Machine Learning",
    "Agentic AI Developer",
]


def scrape_adzuna(
    queries: list[str] | None = None,
    pages_per_query: int = 2,
    results_per_page: int = 20,
    where: str = "Australia",
) -> list[dict[str, Any]]:
    if not APP_ID or not APP_KEY:
        print("[adzuna] missing ADZUNA_APP_ID or ADZUNA_APP_KEY; skipping Adzuna")
        return []

    from jobmonster.quota import record as quota_record

    queries = queries or QUERIES
    seen: set[str] = set()
    jobs: list[dict[str, Any]] = []

    for query in queries:
        for page in range(1, pages_per_query + 1):
            quota_record("adzuna", 1)
            batch = _fetch_page(query, page, results_per_page, where)
            for job in batch:
                jid = job["job_id"]
                if jid in seen:
                    continue
                seen.add(jid)
                jobs.append(job)
            time.sleep(0.8)

    return jobs


def _fetch_page(query: str, page: int, per_page: int, where: str) -> list[dict]:
    params = urllib.parse.urlencode({
        "app_id": APP_ID,
        "app_key": APP_KEY,
        "what": query,
        "where": where,
        "results_per_page": per_page,
        "category": "it-jobs",
        "sort_by": "date",
    })
    url = f"{BASE}/{page}?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
        return [_normalize(j) for j in data.get("results", [])]
    except Exception as e:
        print(f"[adzuna] error query={query!r} page={page}: {e}")
        return []


def _normalize(raw: dict) -> dict[str, Any]:
    loc = raw.get("location", {})
    area = loc.get("area", [])
    location = loc.get("display_name", ", ".join(area[1:]) if area else "Australia")

    salary = ""
    lo = raw.get("salary_min")
    hi = raw.get("salary_max")
    if lo and hi:
        salary = f"${int(lo):,}–${int(hi):,}"
    elif lo:
        salary = f"${int(lo):,}+"

    return {
        "job_id": f"adzuna_{raw['id']}",
        "title": raw.get("title", ""),
        "company": (raw.get("company") or {}).get("display_name", ""),
        "location": location,
        "salary": salary,
        "source": "adzuna",
        "apply_url": raw.get("redirect_url", ""),
        "description": raw.get("description", "")[:400],
        "remote": "remote" in raw.get("description", "").lower(),
        "posted": raw.get("created", ""),
        "contract_time": raw.get("contract_time", ""),
    }
