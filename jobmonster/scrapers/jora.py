from __future__ import annotations

import re
import time
import urllib.parse
import urllib.request
from html import unescape
from typing import Any

JORA_QUERIES = [
    "AI Engineer",
    "Machine Learning Engineer",
    "Python Developer AI",
    "LLM Engineer",
    "MLOps Engineer",
    "Automation Engineer Python",
    "AI Developer",
    "Software Engineer AI",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-AU,en;q=0.9",
}


def scrape_jora(
    queries: list[str] | None = None,
    pages_per_query: int = 2,
    headless: bool = True,
) -> list[dict[str, Any]]:
    queries = queries or JORA_QUERIES
    seen: set[str] = set()
    jobs: list[dict[str, Any]] = []

    for query in queries:
        for page_num in range(1, pages_per_query + 1):
            batch = _fetch_page(query, page_num)
            for job in batch:
                jid = job.get("job_id", "")
                if jid and jid in seen:
                    continue
                seen.add(jid)
                jobs.append(job)
            time.sleep(1.2)

    return jobs


def _fetch_page(query: str, page: int) -> list[dict]:
    params = urllib.parse.urlencode({"q": query, "l": "Australia", "p": page})
    url = f"https://au.jora.com/jobs?{params}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            html = r.read().decode("utf-8", errors="ignore")
        return _parse_jobs(html)
    except Exception as e:
        print(f"[jora] error query={query!r} page={page}: {e}")
        return []


def _parse_jobs(html: str) -> list[dict]:
    jobs = []
    # Each job block: <article ... data-job-id="...">
    blocks = re.split(r'<article\b', html)[1:]
    for block in blocks:
        job_id_m = re.search(r'data-job-id="([^"]+)"', block)
        if not job_id_m:
            continue
        job_id = job_id_m.group(1)

        title_m = re.search(r'<a[^>]+class="[^"]*job-title[^"]*"[^>]*>([^<]+)<', block)
        if not title_m:
            title_m = re.search(r'data-job-title="([^"]+)"', block)
        title = unescape(title_m.group(1).strip()) if title_m else ""

        company_m = re.search(r'class="[^"]*company[^"]*"[^>]*>([^<]+)<', block)
        company = unescape(company_m.group(1).strip()) if company_m else ""

        location_m = re.search(r'class="[^"]*location[^"]*"[^>]*>\s*<[^>]+>([^<]+)<', block)
        if not location_m:
            location_m = re.search(r'class="[^"]*location[^"]*"[^>]*>([^<]+)<', block)
        location = unescape(location_m.group(1).strip()) if location_m else "Australia"

        # prefer fsv=false (non-duplicate) link
        link_m = re.search(r'href="(/job/[^"]+fsv=false[^"]*)"', block)
        if not link_m:
            link_m = re.search(r'href="(/job/[^"]+)"', block)
        apply_url = ("https://au.jora.com" + unescape(link_m.group(1))) if link_m else ""

        if not title or not apply_url:
            continue

        jobs.append({
            "job_id": job_id,
            "title": title,
            "company": company,
            "location": location,
            "salary": "",
            "source": "jora",
            "apply_url": apply_url,
            "description": "",
            "remote": "remote" in block.lower(),
        })

    return jobs
