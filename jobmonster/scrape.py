from __future__ import annotations

import argparse
import json
from pathlib import Path

from jobmonster.detectors import detect_platform, is_trusted_application_url
from jobmonster.scrapers.adzuna import scrape_adzuna
from jobmonster.scrapers.jsearch import scrape_jsearch

DATA_DIR = Path(__file__).parent.parent / "data"
DEFAULT_OUT = DATA_DIR / "jobs.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="JOBMONSTER scraper — API-only job discovery")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--pages", type=int, default=2, help="Pages per query")
    parser.add_argument("--limit", type=int, default=0, help="Cap total jobs")
    parser.add_argument("--where", type=str, default="Australia")
    parser.add_argument("--source", choices=["adzuna", "jsearch", "greenhouse", "lever", "ats", "all"], default="ats",
                        help="ats = greenhouse+lever (direct ATS URLs, no resolve needed)")
    parser.add_argument("--trusted-only", action="store_true", help="Save only jobs whose apply_url is a trusted ATS")
    parser.add_argument("--resolve", action="store_true", help="Search for direct ATS URLs for discovery-source jobs")
    parser.add_argument("--chase", action="store_true", help="Use Playwright browser to follow Adzuna/discovery URLs to employer ATS")
    args = parser.parse_args()

    jobs: list[dict] = []
    if args.source in {"adzuna", "all"}:
        print("[JOBMONSTER] scraping Adzuna AU ...")
        jobs.extend(scrape_adzuna(pages_per_query=args.pages, where=args.where))
    if args.source in {"jsearch", "all"}:
        print("[JOBMONSTER] scraping JSearch ...")
        jobs.extend(scrape_jsearch(pages_per_query=args.pages))
    if args.source in {"greenhouse", "ats", "all"}:
        print("[JOBMONSTER] scraping Greenhouse ...")
        from jobmonster.scrapers.greenhouse import scrape_greenhouse
        jobs.extend(scrape_greenhouse())
    if args.source in {"lever", "ats", "all"}:
        print("[JOBMONSTER] scraping Lever ...")
        from jobmonster.scrapers.lever import scrape_lever
        jobs.extend(scrape_lever())

    jobs = _dedupe(jobs)

    if args.resolve:
        print("[JOBMONSTER] resolving discovery jobs → direct ATS URLs ...")
        from jobmonster.resolver import resolve_jobs
        jobs = resolve_jobs(jobs)

    if args.chase:
        print("[JOBMONSTER] chasing Adzuna/discovery URLs via browser ...")
        from jobmonster.chaser import chase_jobs_sync
        jobs = chase_jobs_sync(jobs)

    for job in jobs:
        platform = detect_platform(job.get("apply_url", ""))
        job["platform"] = platform
        job["application_ready"] = is_trusted_application_url(job.get("apply_url", ""))

    if args.trusted_only:
        jobs = [job for job in jobs if job["application_ready"]]

    if args.limit:
        jobs = jobs[: args.limit]

    print(f"[JOBMONSTER] {len(jobs)} unique jobs")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(jobs, indent=2))
    print(f"[JOBMONSTER] saved → {args.out}")

    platform_counts: dict[str, int] = {}
    for job in jobs:
        p = detect_platform(job.get("apply_url", ""))
        platform_counts[p] = platform_counts.get(p, 0) + 1

    print("\n[JOBMONSTER] platform breakdown:")
    for plat, count in sorted(platform_counts.items(), key=lambda x: -x[1]):
        print(f"  {plat:20s} {count}")

    ready = sum(1 for job in jobs if job.get("application_ready"))
    print(f"\n[JOBMONSTER] application-ready: {ready}/{len(jobs)}")

    from jobmonster.quota import print_status
    print_status()


def _dedupe(jobs: list[dict]) -> list[dict]:
    seen: set[str] = set()
    deduped: list[dict] = []
    for job in jobs:
        url_key = job.get("job_id") or job.get("apply_url")
        # Also dedupe by company+title to avoid same role in multiple offices
        title_key = f"{job.get('company', '').lower()}::{job.get('title', '').lower()}"
        if not url_key or url_key in seen or title_key in seen:
            continue
        seen.add(url_key)
        seen.add(title_key)
        deduped.append(job)
    return deduped


if __name__ == "__main__":
    main()
