from __future__ import annotations

from typing import Any

SEEK_QUERIES = [
    "AI Engineer",
    "Machine Learning Engineer",
    "Python Developer AI",
    "LLM Engineer",
    "MLOps Engineer",
    "Automation Engineer Python",
    "AI Developer",
    "Data Engineer AI",
    "Agentic AI",
    "Software Engineer AI",
]


async def scrape_seek(
    queries: list[str] | None = None,
    pages_per_query: int = 3,
    headless: bool = True,
) -> list[dict[str, Any]]:
    print("[seek] scraper disabled; use official/API sources or direct employer ATS URLs")
    return []
