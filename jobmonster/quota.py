from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

QUOTA_FILE = Path(__file__).parent.parent / "data" / "api_quota.json"

LIMITS = {
    "jsearch": 200,
    "adzuna": 50000,
}


def _load() -> dict:
    if QUOTA_FILE.exists():
        try:
            return json.loads(QUOTA_FILE.read_text())
        except Exception:
            pass
    return {}


def _save(data: dict) -> None:
    QUOTA_FILE.parent.mkdir(parents=True, exist_ok=True)
    QUOTA_FILE.write_text(json.dumps(data, indent=2))


def _month_key() -> str:
    return datetime.now().strftime("%Y-%m")


def record(api: str, count: int = 1) -> dict:
    """Record `count` API calls. Returns current usage dict."""
    data = _load()
    month = _month_key()
    data.setdefault(month, {})
    data[month].setdefault(api, 0)
    data[month][api] += count
    _save(data)
    used = data[month][api]
    limit = LIMITS.get(api)
    if limit:
        pct = used / limit * 100
        if pct >= 80:
            print(f"[quota] WARNING {api}: {used}/{limit} ({pct:.0f}%) this month")
    return data[month]


def usage(api: str) -> int:
    data = _load()
    return data.get(_month_key(), {}).get(api, 0)


def remaining(api: str) -> int:
    limit = LIMITS.get(api)
    if limit is None:
        return 999999
    return max(0, limit - usage(api))


def check_quota(api: str, needed: int = 1) -> bool:
    """Return False (and print warning) if quota would be exceeded."""
    rem = remaining(api)
    if rem < needed:
        print(f"[quota] BLOCKED {api}: only {rem} requests left this month (limit {LIMITS.get(api)})")
        return False
    return True


def print_status() -> None:
    data = _load()
    month = _month_key()
    month_data = data.get(month, {})
    print(f"\n[quota] API usage for {month}:")
    for api, limit in LIMITS.items():
        used = month_data.get(api, 0)
        print(f"  {api:15s} {used:>6}/{limit:<6} ({used/limit*100:.0f}%)")
    for api, used in month_data.items():
        if api not in LIMITS:
            print(f"  {api:15s} {used:>6} (no limit)")
    print()
