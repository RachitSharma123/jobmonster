from __future__ import annotations

import asyncio
from typing import Any

from jobmonster.detectors import detect_platform, is_trusted_application_url

_APPLY_LINK_TEXT = ["apply for this job", "no thanks, take me to the job"]


async def chase_url(url: str, headless: bool = True, timeout_ms: int = 25000) -> str:
    """Follow a discovery URL to find the employer ATS URL."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return url

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="en-AU",
        )
        page = await context.new_page()

        try:
            await page.goto(url, wait_until="networkidle", timeout=timeout_ms)
            await asyncio.sleep(2)

            # Extract the actual apply href from the page (avoid popup/click issues)
            apply_href = await page.evaluate("""() => {
                const links = Array.from(document.querySelectorAll('a'));
                for (const link of links) {
                    const text = link.innerText.trim().toLowerCase();
                    if (text.includes('apply for this job') || text.includes('take me to the job')) {
                        return link.href;
                    }
                }
                return null;
            }""")

            if not apply_href or "adzuna" not in apply_href:
                # Already on a useful page or different site
                current = page.url
                if is_trusted_application_url(current):
                    return current
                return url

            # Navigate to the apply link and follow redirects
            popup_future = asyncio.ensure_future(context.wait_for_event("page", timeout=8000))
            nav_future = asyncio.ensure_future(page.goto(apply_href, wait_until="domcontentloaded", timeout=timeout_ms))

            try:
                done, pending = await asyncio.wait(
                    [popup_future, nav_future],
                    return_when=asyncio.FIRST_COMPLETED,
                    timeout=12,
                )
                for t in pending:
                    t.cancel()

                if popup_future in done and not popup_future.cancelled():
                    try:
                        popup = popup_future.result()
                        await popup.wait_for_load_state("domcontentloaded", timeout=10000)
                        await asyncio.sleep(2)
                        final = popup.url
                    except Exception:
                        final = page.url
                else:
                    await asyncio.sleep(2)
                    final = page.url
            except Exception:
                await asyncio.sleep(2)
                final = page.url

            return final

        except Exception as e:
            return url
        finally:
            await browser.close()


async def chase_jobs(
    jobs: list[dict[str, Any]],
    headless: bool = True,
    delay: float = 2.0,
) -> list[dict[str, Any]]:
    enriched = []
    for job in jobs:
        apply_url = job.get("apply_url", "")
        if not apply_url or is_trusted_application_url(apply_url):
            enriched.append(job)
            continue

        company = job.get("company", "?")
        title = (job.get("title") or "?")[:40]
        print(f"[chaser] {company} — {title}")

        real_url = await chase_url(apply_url, headless=headless)
        platform = detect_platform(real_url)

        if real_url != apply_url:
            if is_trusted_application_url(real_url):
                print(f"[chaser]   TRUSTED -> {real_url}")
                job = {**job, "apply_url": real_url, "chased_from": apply_url}
            else:
                print(f"[chaser]   landed on {platform} -> {real_url[:70]}")
        else:
            print(f"[chaser]   no redirect")

        enriched.append(job)
        await asyncio.sleep(delay)

    return enriched


def chase_jobs_sync(
    jobs: list[dict[str, Any]],
    headless: bool = True,
    delay: float = 2.0,
) -> list[dict[str, Any]]:
    return asyncio.run(chase_jobs(jobs, headless=headless, delay=delay))
