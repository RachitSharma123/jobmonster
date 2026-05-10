from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from jobmonster.detectors import detect_platform, is_trusted_application_url
from jobmonster.models import ApplyPlan

TEXT_SELECTORS = (
    "input:not([type=hidden]):not([type=submit]):not([type=button]):not([type=file])"
    ":not([type=checkbox]):not([type=radio]), textarea"
)

SUBMIT_SELECTORS = [
    "button[type=submit]",
    "input[type=submit]",
    "button:has-text('Submit Application')",
    "button:has-text('Submit')",
    "button:has-text('Apply Now')",
    "button:has-text('Apply')",
    "button:has-text('Send Application')",
    "button:has-text('Complete Application')",
    "[data-testid*=submit]",
    "[data-qa*=submit]",
]

NEXT_SELECTORS = [
    "button:has-text('Next')",
    "button:has-text('Continue')",
    "button:has-text('Next Step')",
    "[data-testid*=next]",
    "[data-qa*=next]",
]

SUCCESS_SIGNALS = [
    "application submitted",
    "application received",
    "thank you for applying",
    "successfully applied",
    "we received your application",
    "your application has been",
    "application complete",
    "thanks for applying",
    "your application was submitted",
    "we'll be in touch",
    "we will be in touch",
    "application has been submitted",
    "you've applied",
    "you have applied",
    "application is complete",
]


async def fill_plan_in_browser(
    plan: ApplyPlan,
    headless: bool = False,
    auto_submit: bool = False,
    screenshot_dir: Path | None = None,
) -> dict[str, Any]:
    platform = detect_platform(plan.job.apply_url)
    if not is_trusted_application_url(plan.job.apply_url):
        return {
            "filled_fields": [],
            "uploaded_files": [],
            "checked_boxes": [],
            "steps_completed": 0,
            "submitted": False,
            "success": False,
            "skipped": True,
            "skip_reason": f"{platform} is a discovery source, not a trusted application portal",
            "screenshot": "",
        }

    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise RuntimeError("playwright required. pip install playwright && playwright install chromium") from exc

    screenshot_dir = screenshot_dir or Path("/tmp/JOBMONSTER")
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{_safe_name(plan.job.company)}_{_safe_name(plan.job.title)}"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="en-AU",
            timezone_id="Australia/Melbourne",
        )
        page = await context.new_page()
        await page.goto(plan.job.apply_url, wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(2)

        # Some ATS pages (Lever) require clicking an "Apply" button to reveal the form
        await _reveal_form(page)

        all_filled: list[str] = []
        all_uploaded: list[str] = []
        all_checked: list[str] = []
        submitted = False
        success = False
        step = 0
        max_steps = 10

        while step < max_steps:
            step += 1
            filled = await _fill_common_fields(page, plan.fields)
            all_filled.extend(filled)
            await _fill_selects(page, plan.fields)
            react_filled = await _fill_react_selects(page, plan.fields)
            all_filled.extend(react_filled)
            await _fill_radios(page, plan.fields)
            checked = await _fill_checkboxes(page, plan.fields)
            all_checked.extend(checked)
            uploaded = await _upload_files(page, plan.files)
            all_uploaded.extend(uploaded)
            await asyncio.sleep(1)

            screenshot_path = screenshot_dir / f"{safe_name}_step{step}.png"
            await page.screenshot(path=str(screenshot_path), full_page=True)

            if auto_submit:
                advanced = await _click_next(page)
                if advanced:
                    await asyncio.sleep(2)
                    continue

                clicked = await _click_submit(page)
                if clicked:
                    submitted = True
                    await asyncio.sleep(3)
                    success = await _detect_success(page)
                    await page.screenshot(path=str(screenshot_dir / f"{safe_name}_result.png"), full_page=True)
                break
            else:
                break

        await browser.close()
        return {
            "filled_fields": all_filled,
            "uploaded_files": all_uploaded,
            "checked_boxes": all_checked,
            "steps_completed": step,
            "submitted": submitted,
            "success": success,
            "skipped": False,
            "skip_reason": "",
            "screenshot": str(screenshot_dir / f"{safe_name}_step{step}.png"),
        }


async def _fill_common_fields(page, fields: dict[str, Any]) -> list[str]:
    filled: list[str] = []
    elements = await page.query_selector_all(TEXT_SELECTORS)
    for element in elements:
        try:
            if not await element.is_visible():
                continue
            current = await element.input_value()
            if current.strip():
                continue
            hint = await _get_field_hint(element)
            value = _value_for_hint(hint, fields)
            if not value:
                continue
            await element.fill(str(value))
            filled.append(hint[:80].strip())
        except Exception:
            continue
    return filled


async def _fill_selects(page, fields: dict[str, Any]) -> None:
    elements = await page.query_selector_all("select")
    for element in elements:
        try:
            if not await element.is_visible():
                continue
            # Skip already-selected non-empty dropdowns
            current_val = await element.evaluate("el => el.value")
            if current_val and current_val not in ("", "0", "-1"):
                continue
            hint = await _get_field_hint(element)
            options_raw = await element.evaluate(
                "el => Array.from(el.options).map(o => ({v: o.value, t: o.text.trim()}))"
            )
            # Filter out placeholder options
            real_options = [o for o in options_raw if o["v"] and o["t"] and o["t"] not in ("Select...", "-- Select --", "Please select", "")]
            if not real_options:
                continue

            value = _value_for_hint(hint, fields) or _default_select_value(hint)
            target = str(value).lower() if value else ""

            matched = None
            if target:
                matched = next((o for o in real_options if target in o["t"].lower() or o["t"].lower() in target), None)

            # Yes/no logic for work auth / sponsorship
            if not matched:
                option_texts = [o["t"].lower() for o in real_options]
                if _is_yes_field(hint, fields) and any("yes" in t for t in option_texts):
                    matched = next(o for o in real_options if "yes" in o["t"].lower())
                elif _is_no_field(hint, fields) and any("no" in t for t in option_texts):
                    matched = next(o for o in real_options if "no" in o["t"].lower())

            # Fallback: pick first real option for required dropdowns to avoid validation error
            if not matched and real_options:
                # Prefer "Yes" if available for yes/no fields, else first option
                option_texts = [o["t"].lower() for o in real_options]
                if any("yes" in t for t in option_texts) and _is_yes_field(hint, fields):
                    matched = next(o for o in real_options if "yes" in o["t"].lower())
                elif any("australia" in t for t in option_texts):
                    matched = next(o for o in real_options if "australia" in o["t"].lower())
                else:
                    matched = real_options[0]

            if matched:
                await element.select_option(value=matched["v"])
        except Exception:
            continue


async def _fill_react_selects(page, fields: dict[str, Any]) -> list[str]:
    """Fill React Select dropdowns (class='select__control ...')."""
    filled = []

    controls = await page.query_selector_all("div.select__control")
    if not controls:
        controls = await page.query_selector_all("[class*='__control']")

    for control in controls:
        try:
            if not await control.is_visible():
                continue
            current_text = await control.evaluate("el => el.innerText.trim()")
            if current_text and current_text not in ("Select...", ""):
                continue

            hint = await control.evaluate("""el => {
                let p = el;
                for (let i = 0; i < 10; i++) {
                    p = p.parentElement;
                    if (!p) break;
                    const labels = p.querySelectorAll('label');
                    if (labels.length > 0) return labels[0].innerText.toLowerCase();
                }
                return '';
            }""")

            value = _react_select_value(hint, fields)
            if not value:
                continue

            # Click to open dropdown
            await control.click()
            await asyncio.sleep(0.7)

            # Read all available options from the open menu
            opts = await page.query_selector_all("div.select__option")
            if not opts:
                opts = await page.query_selector_all("[class*='__option']")

            if not opts:
                await page.keyboard.press("Escape")
                continue

            # Find best matching option
            opt_texts = []
            for o in opts:
                try:
                    t = await o.inner_text()
                    opt_texts.append((t.strip(), o))
                except Exception:
                    continue

            target = value.lower()
            best = None

            # Exact / startswith match
            for text, el in opt_texts:
                if text.lower().startswith(target) or target in text.lower():
                    best = (text, el)
                    break

            # For yes/no: pick first "Yes" option
            if not best and target in ("yes", "no"):
                for text, el in opt_texts:
                    if text.lower().startswith(target):
                        best = (text, el)
                        break

            # Fallback: first option
            if not best and opt_texts:
                best = opt_texts[0]

            if best:
                await best[1].click()
                filled.append(f"{hint[:50]} → {best[0][:40]}")
                await asyncio.sleep(0.4)
            else:
                await page.keyboard.press("Escape")
                await asyncio.sleep(0.2)

        except Exception:
            try:
                await page.keyboard.press("Escape")
            except Exception:
                pass
            continue

    return filled


def _react_select_value(hint: str, fields: dict[str, Any]) -> str:
    """Map a field hint to a value for React Select dropdowns."""
    if "country" in hint:
        return "Australia"
    if "authoris" in hint or "authoriz" in hint or "legally" in hint or "right to work" in hint:
        return "Yes"
    if "sponsor" in hint:
        return "No"
    if "location" in hint or "located" in hint or "city" in hint:
        loc = fields.get("location", "Melbourne")
        return loc.split(",")[0].strip()
    if "notice" in hint or "notice period" in hint:
        return fields.get("notice_period", "Immediately")
    if "gender" in hint or "pronouns" in hint or "identify" in hint:
        return "Prefer not to say"
    if "salary" in hint or "compensation" in hint:
        return fields.get("salary_expectation", "")
    if "aboriginal" in hint or "torres" in hint:
        return "No"
    if "access" in hint and "requirement" in hint:
        return "No"
    return ""


async def _fill_radios(page, fields: dict[str, Any]) -> None:
    groups: dict[str, list] = {}
    radios = await page.query_selector_all("input[type=radio]")
    for radio in radios:
        try:
            name = await radio.evaluate("el => el.name")
            groups.setdefault(name, []).append(radio)
        except Exception:
            continue

    for name, group in groups.items():
        try:
            hint = name.lower()
            value = _value_for_hint(hint, fields)
            for radio in group:
                label_text = await radio.evaluate(
                    """el => {
                        const label = document.querySelector('label[for="' + el.id + '"]');
                        return (label ? label.innerText : el.value || '').toLowerCase();
                    }"""
                )
                should_check = False
                if value and value.lower() in label_text:
                    should_check = True
                elif not value and _is_yes_field(hint, fields) and "yes" in label_text:
                    should_check = True
                elif not value and _is_no_field(hint, fields) and "no" in label_text:
                    should_check = True
                if should_check and await radio.is_visible():
                    await radio.check()
                    break
        except Exception:
            continue


async def _fill_checkboxes(page, fields: dict[str, Any]) -> list[str]:
    checked_boxes: list[str] = []
    checkboxes = await page.query_selector_all("input[type=checkbox]")
    for cb in checkboxes:
        try:
            if not await cb.is_visible():
                continue
            checked = await cb.is_checked()
            if checked:
                continue
            hint = await _get_field_hint(cb)
            if any(t in hint for t in ("agree", "accept", "terms", "privacy", "consent", "acknowledge")):
                await cb.check()
                checked_boxes.append(hint[:80].strip())
                continue
            if "work" in hint and ("authoris" in hint or "authoriz" in hint or "right" in hint):
                if fields.get("work_authorization", "Yes") == "Yes":
                    await cb.check()
                    checked_boxes.append(hint[:80].strip())
            else:
                value = _value_for_hint(hint, fields)
                if str(value).lower() in {"true", "yes", "on", "checked"}:
                    await cb.check()
                    checked_boxes.append(hint[:80].strip())
        except Exception:
            continue
    return checked_boxes


async def _upload_files(page, files: dict[str, Path]) -> list[str]:
    uploaded: list[str] = []
    inputs = await page.query_selector_all("input[type=file]")
    for element in inputs:
        try:
            hint = await _get_field_hint(element)
            target = None
            if "cover" in hint and "cover_letter" in files:
                target = files["cover_letter"]
            elif "resume" in files:
                target = files["resume"]
            if target:
                await element.set_input_files(str(target))
                uploaded.append(str(target))
        except Exception:
            continue
    return uploaded


async def _click_next(page) -> bool:
    for selector in NEXT_SELECTORS:
        try:
            btn = page.locator(selector).first
            if await btn.is_visible(timeout=1000) and await btn.is_enabled(timeout=1000):
                await btn.click()
                return True
        except Exception:
            continue
    return False


async def _click_submit(page) -> bool:
    for selector in SUBMIT_SELECTORS:
        try:
            btn = page.locator(selector).first
            if await btn.is_visible(timeout=1000) and await btn.is_enabled(timeout=1000):
                await btn.click()
                return True
        except Exception:
            continue
    return False


async def _reveal_form(page) -> None:
    """Click 'Apply' button if no form fields are immediately visible (e.g. Lever)."""
    try:
        visible_inputs = await page.query_selector_all(TEXT_SELECTORS)
        has_visible = any(
            [await el.is_visible() for el in visible_inputs[:5]]
        ) if visible_inputs else False
        if not has_visible:
            for text in ("Apply for this job", "Apply Now", "Apply"):
                try:
                    btn = page.get_by_text(text, exact=False).first
                    if await btn.is_visible(timeout=2000):
                        await btn.click()
                        await asyncio.sleep(2)
                        return
                except Exception:
                    continue
    except Exception:
        pass


async def _detect_success(page) -> bool:
    try:
        content = (await page.content()).lower()
        return any(signal in content for signal in SUCCESS_SIGNALS)
    except Exception:
        return False


async def _get_field_hint(element) -> str:
    return await element.evaluate(
        """el => {
            let text = '';
            if (el.id) {
                const label = document.querySelector('label[for="' + el.id + '"]');
                if (label) text += ' ' + label.innerText;
            }
            const parent = el.closest('label, [class*=field], [class*=Field], [class*=question], [class*=Question]');
            if (parent) text += ' ' + parent.innerText;
            text += ' ' + (el.name || '') + ' ' + (el.id || '') + ' ' + (el.placeholder || '') + ' ' + (el.ariaLabel || '');
            return text.toLowerCase();
        }"""
    )


def _value_for_hint(hint: str, fields: dict[str, Any]) -> Any:
    checks = [
        (("first", "given"), "first_name"),
        (("last", "surname", "family"), "last_name"),
        (("full name", "your name"), "name"),
        (("email",), "email"),
        (("phone", "mobile", "tel"), "phone"),
        (("linkedin",), "linkedin"),
        (("website", "portfolio"), "website"),
        (("city", "location", "address"), "location"),
        (("salary", "compensation", "remuneration"), "salary_expectation"),
        (("notice", "start date", "available"), "notice_period"),
        (("sponsor",), "sponsorship"),
        (("authoris", "authoriz", "right to work", "work permit"), "work_authorization"),
    ]
    for needles, key in checks:
        if any(needle in hint for needle in needles):
            return fields.get(key, "")
    for key, value in fields.items():
        if key.lower() in hint:
            return value
    return ""


def _default_select_value(hint: str) -> str:
    if "country" in hint:
        return "Australia"
    if "currency" in hint:
        return "AUD"
    return ""


def _is_yes_field(hint: str, fields: dict[str, Any]) -> bool:
    if "authoris" in hint or "authoriz" in hint or "right to work" in hint:
        return fields.get("work_authorization", "Yes") == "Yes"
    return False


def _is_no_field(hint: str, fields: dict[str, Any]) -> bool:
    if "sponsor" in hint:
        return fields.get("sponsorship", "No") == "No"
    return False


def _safe_name(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_")
    return cleaned[:40] or "job"
