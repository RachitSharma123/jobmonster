"""JOBMONSTER full pipeline: scrape → chase → apply."""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from jobmonster.detectors import detect_platform, is_trusted_application_url
from jobmonster.scrapers.adzuna import scrape_adzuna
from jobmonster.scrapers.jsearch import scrape_jsearch
from jobmonster.scrapers.linkedin import scrape_linkedin
from jobmonster.io import load_candidate, make_documents, job_from_mapping
from jobmonster.adapters.registry import default_registry
from jobmonster.browser_assist import fill_plan_in_browser
from jobmonster.quota import print_status

DATA_DIR = Path(__file__).parent.parent / "data"
RESULTS_DIR = DATA_DIR / "results"


def main() -> None:
    parser = argparse.ArgumentParser(description="JOBMONSTER — full pipeline")
    parser.add_argument("--candidate", type=Path,
                        default=Path(__file__).parent.parent / "examples" / "candidate.example.json")
    parser.add_argument("--resume", type=Path, default=None,
                        help="Resume PDF (required for browser-assist / auto-submit)")
    parser.add_argument("--cover-letter", type=Path, default=None,
                        help="Cover letter PDF (optional)")
    parser.add_argument("--pages", type=int, default=2, help="Pages per scraper query")
    parser.add_argument("--limit", type=int, default=10, help="Max applications to submit")
    parser.add_argument("--source", choices=["adzuna", "jsearch", "linkedin", "greenhouse", "lever", "ats", "all"],
                        default="ats", help="ats = greenhouse+lever (direct ATS URLs)")
    parser.add_argument("--chase", action="store_true", help="Browser-chase discovery URLs to find employer ATS")
    parser.add_argument("--no-chase", dest="chase", action="store_false")
    parser.add_argument("--headless", action="store_true", default=True)
    parser.add_argument("--no-headless", dest="headless", action="store_false")
    parser.add_argument("--delay", type=float, default=6.0, help="Seconds between applications")
    parser.add_argument("--dry-run", action="store_true", help="Plan only, no browser submission")
    parser.add_argument("--out", type=Path, default=DATA_DIR / "jobs.json")
    parser.set_defaults(chase=True)
    args = parser.parse_args()

    candidate = load_candidate(args.candidate)
    docs = make_documents(args.resume, args.cover_letter)

    # === SCRAPE ===
    jobs_raw: list[dict] = []
    if args.source in {"adzuna", "all"}:
        print("[JOBMONSTER] scraping Adzuna ...")
        jobs_raw.extend(scrape_adzuna(pages_per_query=args.pages))
    if args.source in {"jsearch", "all"}:
        print("[JOBMONSTER] scraping JSearch ...")
        jobs_raw.extend(scrape_jsearch(pages_per_query=args.pages))
    if args.source in {"linkedin", "all"}:
        print("[JOBMONSTER] scraping LinkedIn ...")
        jobs_raw.extend(scrape_linkedin(pages_per_query=args.pages))
    if args.source in {"greenhouse", "ats", "all"}:
        print("[JOBMONSTER] scraping Greenhouse ...")
        from jobmonster.scrapers.greenhouse import scrape_greenhouse
        jobs_raw.extend(scrape_greenhouse())
    if args.source in {"lever", "ats", "all"}:
        print("[JOBMONSTER] scraping Lever ...")
        from jobmonster.scrapers.lever import scrape_lever
        jobs_raw.extend(scrape_lever())

    jobs_raw = _dedupe(jobs_raw)
    print(f"[JOBMONSTER] {len(jobs_raw)} unique jobs scraped")

    # === CHASE ===
    if args.chase:
        print("[JOBMONSTER] chasing URLs via browser ...")
        from jobmonster.chaser import chase_jobs_sync
        jobs_raw = chase_jobs_sync(jobs_raw, headless=args.headless)

    # === FILTER TO TRUSTED ATS ===
    for job in jobs_raw:
        job["platform"] = detect_platform(job.get("apply_url", ""))
        job["application_ready"] = is_trusted_application_url(job.get("apply_url", ""))

    ready_jobs = [j for j in jobs_raw if j["application_ready"]]
    print(f"[JOBMONSTER] {len(ready_jobs)} application-ready jobs")

    # Save all scraped jobs
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(jobs_raw, indent=2))

    if not ready_jobs:
        print("[JOBMONSTER] No trusted ATS URLs found. Try --chase or check sources.")
        print_status()
        return

    # === APPLY ===
    targets = ready_jobs[: args.limit]
    print(f"[JOBMONSTER] submitting {len(targets)} applications ...")

    registry = default_registry(allow_generic=False)
    results = asyncio.run(_apply_all(targets, candidate, docs, registry, args))

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    import datetime
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    results_path = RESULTS_DIR / f"results_{ts}.json"
    results_path.write_text(json.dumps(results, indent=2))

    submitted = sum(1 for r in results if r.get("submitted"))
    success = sum(1 for r in results if r.get("success"))
    print(f"\n[JOBMONSTER] submitted={submitted} success_signals={success}/{len(targets)}")
    print(f"[JOBMONSTER] results → {results_path}")

    print_status()


async def _apply_all(jobs_raw, candidate, docs, registry, args) -> list[dict]:
    from jobmonster.io import job_from_mapping
    results = []
    for i, job_dict in enumerate(jobs_raw):
        job = job_from_mapping(job_dict)
        try:
            adapter = registry.resolve(job)
        except LookupError:
            results.append({"job": job.apply_url, "title": job.title, "company": job.company,
                            "skipped": True, "reason": "no adapter"})
            continue

        plan = adapter.build_plan(job, candidate, docs)
        if args.dry_run:
            results.append({"job": job.apply_url, "title": job.title, "company": job.company,
                            "skipped": True, "reason": "dry-run"})
            continue

        result = await fill_plan_in_browser(plan, headless=args.headless, auto_submit=True)
        results.append({
            "job": job.apply_url,
            "title": job.title,
            "company": job.company,
            **result,
        })
        print(f"[{i+1}/{len(jobs_raw)}] {job.company} — {job.title[:40]} submitted={result.get('submitted')} success={result.get('success')}")

        if i < len(jobs_raw) - 1:
            await asyncio.sleep(args.delay)

    return results


def _dedupe(jobs: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out = []
    for job in jobs:
        url_key = job.get("job_id") or job.get("apply_url")
        title_key = f"{job.get('company', '').lower()}::{job.get('title', '').lower()}"
        if not url_key or url_key in seen or title_key in seen:
            continue
        seen.add(url_key)
        seen.add(title_key)
        out.append(job)
    return out


if __name__ == "__main__":
    main()
