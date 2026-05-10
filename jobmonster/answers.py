from __future__ import annotations

from jobmonster.models import CandidateProfile


def default_answers(candidate: CandidateProfile) -> dict[str, str]:
    return {
        "first_name": candidate.first_name,
        "last_name": candidate.last_name,
        "name": candidate.full_name,
        "email": candidate.email,
        "phone": candidate.phone,
        "location": candidate.location,
        "linkedin": candidate.linkedin,
        "website": candidate.website,
        "work_authorization": "Yes" if candidate.work_authorized else "No",
        "sponsorship": "Yes" if candidate.needs_sponsorship else "No",
        "notice_period": candidate.notice_period,
        "salary_expectation": candidate.salary_expectation,
        **candidate.custom_answers,
    }


def answer_for_label(label: str, candidate: CandidateProfile) -> str:
    text = label.lower()
    answers = default_answers(candidate)

    if "first" in text or "given" in text:
        return answers["first_name"]
    if "last" in text or "surname" in text or "family" in text:
        return answers["last_name"]
    if "full name" in text or text == "name":
        return answers["name"]
    if "email" in text:
        return answers["email"]
    if "phone" in text or "mobile" in text:
        return answers["phone"]
    if "linkedin" in text:
        return answers["linkedin"]
    if "website" in text or "portfolio" in text:
        return answers["website"]
    if "location" in text or "city" in text or "address" in text:
        return answers["location"]
    if "sponsor" in text:
        return answers["sponsorship"]
    if "authorized" in text or "authorised" in text or "right to work" in text:
        return answers["work_authorization"]
    if "notice" in text or "start" in text:
        return answers["notice_period"]
    if "salary" in text or "compensation" in text or "remuneration" in text:
        return answers["salary_expectation"]
    for key, value in candidate.custom_answers.items():
        if key.lower() in text:
            return value
    return ""

