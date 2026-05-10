from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from jobmonster.adapters.registry import default_registry
from jobmonster.browser_assist import fill_plan_in_browser
from jobmonster.detectors import detect_platform, is_trusted_application_url
from jobmonster.io import load_candidate, load_jobs, make_documents, plan_to_dict


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="JOBMONSTER planner and assisted filler")
    parser.add_argument("--jobs", required=True, type=Path, help="JSON list of jobs with apply_url/url")
    parser.add_argument("--candidate", required=True, type=Path, help="Candidate JSON profile")
    parser.add_argument("--resume", type=Path,
                        default=None,
                        help="Resume PDF path")
    parser.add_argument("--cover-letter", type=Path,
                        default=None,
                        help="Cover letter PDF path")
    parser.add_argument("--plan-out", type=Path, default=None, help="Write plans to JSON")
    parser.add_argument("--browser-assist", action="store_true", help="Open each URL and fill common fields/files without submitting")
    parser.add_argument("--auto-submit", action="store_true", help="Fill and auto-submit trusted ATS forms")
    parser.add_argument("--allow-generic", action="store_true", help="Allow unknown direct application forms in assisted mode")
    parser.add_argument("--headless", action="store_true", default=False, help="Run browser headless")
    parser.add_argument("--no-headless", dest="headless", action="store_false")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of jobs processed")
    parser.add_argument("--delay-seconds", type=float, default=8.0, help="Delay between browser-assisted applications")
    parser.add_argument("--results-out", type=Path, default=None, help="Write submission results to JSON")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    candidate = load_candidate(args.candidate)
    docs = make_documents(args.resume, args.cover_letter)
    jobs = load_jobs(args.jobs)
    if args.limit:
        jobs = jobs[: args.limit]

    registry = default_registry(allow_generic=args.allow_generic)
    plans = []
    skipped = []
    for job in jobs:
        if not job.apply_url:
            skipped.append(_skip_record(job, "missing apply_url"))
            continue
        platform = detect_platform(job.apply_url)
        if not is_trusted_application_url(job.apply_url) and not (
            args.allow_generic and platform == "generic"
        ):
            skipped.append(_skip_record(job, f"{platform} is discovery-only or unsupported"))
            continue
        try:
            adapter = registry.resolve(job)
        except LookupError as exc:
            skipped.append(_skip_record(job, str(exc)))
            continue
        plan = adapter.build_plan(job, candidate, docs)
        plans.append(plan)

    payload = {
        "summary": {
            "input_jobs": len(jobs),
            "planned": len(plans),
            "skipped": len(skipped),
            "auto_submit": bool(args.auto_submit),
        },
        "plans": [plan_to_dict(plan) for plan in plans],
        "skipped": skipped,
    }
    if args.plan_out:
        args.plan_out.parent.mkdir(parents=True, exist_ok=True)
        args.plan_out.write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))

    if args.browser_assist or args.auto_submit:
        results = asyncio.run(
            _run_browser(
                plans,
                headless=args.headless,
                auto_submit=args.auto_submit,
                delay_seconds=args.delay_seconds,
            )
        )
        if args.results_out:
            args.results_out.parent.mkdir(parents=True, exist_ok=True)
            args.results_out.write_text(json.dumps(results, indent=2))
        print(json.dumps({"results": results}, indent=2))


def _skip_record(job, reason: str) -> dict:
    return {
        "title": job.title,
        "company": job.company,
        "apply_url": job.apply_url,
        "source": job.source,
        "platform": detect_platform(job.apply_url) if job.apply_url else "",
        "reason": reason,
    }


async def _run_browser(plans, headless: bool, auto_submit: bool, delay_seconds: float):
    results = []
    for index, plan in enumerate(plans):
        result = await fill_plan_in_browser(plan, headless=headless, auto_submit=auto_submit)
        results.append({
            "job": plan.job.apply_url,
            "title": plan.job.title,
            "company": plan.job.company,
            **result,
        })
        if index < len(plans) - 1 and delay_seconds > 0:
            await asyncio.sleep(delay_seconds)
    return results


if __name__ == "__main__":
    main()
