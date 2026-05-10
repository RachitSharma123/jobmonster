from __future__ import annotations

from urllib.parse import urlparse

TRUSTED_APPLICATION_PLATFORMS = frozenset(
    {
        "greenhouse",
        "lever",
        "workday",
        "smartrecruiters",
        "livehire",
        "ashby",
        "breezy",
        "jobadder",
        "pageup",
    }
)

DISCOVERY_PLATFORMS = frozenset(
    {
        "adzuna",
        "careerone",
        "indeed",
        "jora",
        "linkedin",
        "seek",
    }
)


def normalized_host(url: str) -> str:
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def detect_platform(url: str, page_text: str = "") -> str:
    host = normalized_host(url)
    text = page_text.lower()

    if "greenhouse.io" in host or "job-boards.greenhouse.io" in host:
        return "greenhouse"
    if "lever.co" in host:
        return "lever"
    if "myworkdayjobs.com" in host or "workdayjobs.com" in host or "workday.com" in host:
        return "workday"
    if "smartrecruiters.com" in host:
        return "smartrecruiters"
    if "livehire.com" in host or "humanforce.com" in host:
        return "livehire"
    if "ashbyhq.com" in host:
        return "ashby"
    if "breezy.hr" in host:
        return "breezy"
    if "jobadder.com" in host:
        return "jobadder"
    if "pageuppeople.com" in host or "pageuppeople" in text:
        return "pageup"
    if "seek.com.au" in host or "seek.co.nz" in host:
        return "seek"
    if "indeed.com" in host:
        return "indeed"
    if "careerone.com.au" in host:
        return "careerone"
    if "jora.com" in host:
        return "jora"
    if "adzuna." in host or "adzuna.com" in host:
        return "adzuna"
    if "linkedin.com" in host:
        return "linkedin"
    return "generic"


def is_trusted_application_url(url: str) -> bool:
    return detect_platform(url) in TRUSTED_APPLICATION_PLATFORMS


def is_discovery_platform(url: str) -> bool:
    return detect_platform(url) in DISCOVERY_PLATFORMS


def is_external_portal(url: str) -> bool:
    return is_trusted_application_url(url)
