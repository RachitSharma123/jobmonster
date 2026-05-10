from __future__ import annotations

import re
import ssl
import time
import urllib.parse
import urllib.request
from html import unescape
from typing import Any

TRUSTED_DOMAINS = [
    "boards.greenhouse.io",
    "job-boards.greenhouse.io",
    "jobs.lever.co",
    "myworkdayjobs.com",
    "smartrecruiters.com",
    "ashbyhq.com",
    "breezy.hr",
    "livehire.com",
    "jobadder.com",
    "pageuppeople.com",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-AU,en;q=0.9",
}

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


_JOB_SIGNALS = ["apply", "position", "opening", "job", "career", "role", "engineer", "developer"]


def _probe(url: str) -> bool:
    """GET request — returns True if page has job-related content."""
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10, context=_SSL_CTX) as r:
            if r.status >= 400:
                return False
            html = r.read(8192).decode("utf-8", errors="ignore").lower()
            return any(sig in html for sig in _JOB_SIGNALS)
    except Exception:
        return False


def _try_direct_patterns(company: str) -> str | None:
    slug = _slug(company)
    # Greenhouse and Lever have proper 404s for unknown orgs
    strict_candidates = [
        f"https://boards.greenhouse.io/{slug}",
        f"https://job-boards.greenhouse.io/{slug}",
        f"https://jobs.lever.co/{slug}",
        f"https://{slug}.ashbyhq.com",
    ]
    for url in strict_candidates:
        if _probe(url):
            return url
    return None


def _ddg_search(query: str) -> str | None:
    params = urllib.parse.urlencode({"q": query})
    req = urllib.request.Request(
        f"https://html.duckduckgo.com/html/?{params}",
        headers={**HEADERS, "Content-Type": "application/x-www-form-urlencoded"},
        data=params.encode(),
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15, context=_SSL_CTX) as r:
            html = r.read().decode("utf-8", errors="ignore")
        return _extract_ats_url(html)
    except Exception as e:
        print(f"[resolver] ddg error: {e}")
        return None


def _extract_ats_url(html: str) -> str | None:
    href_re = re.compile(r'href="(https?://[^"&]+)"')
    for m in href_re.finditer(html):
        url = unescape(m.group(1))
        for domain in TRUSTED_DOMAINS:
            if domain in url:
                clean = url.split("?")[0].rstrip("/")
                if len(clean) > 30:
                    return clean
    return None


def resolve_ats_url(company: str, title: str) -> str | None:
    """Return a direct trusted ATS URL for company+job, or None."""
    url = _try_direct_patterns(company)
    if url:
        return url

    query = f'"{company}" "{title}" site:boards.greenhouse.io OR site:jobs.lever.co OR site:ashbyhq.com'
    url = _ddg_search(query)
    if url:
        return url

    query2 = f"{company} {title} apply greenhouse lever workday"
    url = _ddg_search(query2)
    return url


def resolve_jobs(jobs: list[dict[str, Any]], delay: float = 1.0) -> list[dict[str, Any]]:
    """Enrich discovery-source jobs with a direct ATS URL where possible."""
    from jobmonster.detectors import is_trusted_application_url, is_discovery_platform

    enriched = []
    for job in jobs:
        apply_url = job.get("apply_url", "")
        if is_trusted_application_url(apply_url):
            enriched.append(job)
            continue

        company = job.get("company", "")
        title = job.get("title", "")

        if not company or not title:
            enriched.append(job)
            continue

        print(f"[resolver] {company} — {title}")
        ats_url = resolve_ats_url(company, title)
        if ats_url:
            print(f"[resolver]   -> {ats_url}")
            job = {**job, "apply_url": ats_url, "resolved_from": apply_url}
        else:
            print(f"[resolver]   -> not found")

        enriched.append(job)
        time.sleep(delay)

    return enriched
