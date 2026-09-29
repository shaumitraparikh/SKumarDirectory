#!/usr/bin/env python3
"""Fail-closed monthly cap for pushes that trigger the Pages workflow."""

import json
import os
import sys
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


OWNER = "shaumitraparikh"
REPOSITORY = "SKumarDirectory"
WORKFLOW = "deploy-pages.yml"
DEFAULT_MONTHLY_RUN_LIMIT = 500
GITHUB_API = "https://api.github.com"


def monthly_run_limit(environment=None):
    environment = environment if environment is not None else os.environ
    configured = environment.get("SKUMAR_PAGES_RUN_LIMIT", "")
    try:
        limit = int(configured) if configured else DEFAULT_MONTHLY_RUN_LIMIT
    except ValueError as error:
        raise ValueError("SKUMAR_PAGES_RUN_LIMIT must be a positive integer.") from error
    if limit < 1:
        raise ValueError("SKUMAR_PAGES_RUN_LIMIT must be a positive integer.")
    return limit


def remaining_run_count(used_runs, limit):
    return max(0, limit - used_runs)


def get_monthly_run_count(now=None, opener=urlopen, environment=None):
    environment = environment if environment is not None else os.environ
    now = now or datetime.now(timezone.utc)
    month_start = now.astimezone(timezone.utc).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    query = urlencode({
        "branch": "main",
        "event": "push",
        "created": f"{month_start.date().isoformat()}..{now.date().isoformat()}",
        "per_page": "1",
    })
    url = (
        f"{GITHUB_API}/repos/{OWNER}/{REPOSITORY}/actions/workflows/"
        f"{WORKFLOW}/runs?{query}"
    )
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "SKumarDirectory-local-publish-guard",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = environment.get("GH_TOKEN") or environment.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, headers=headers)
    try:
        with opener(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
        raise RuntimeError(
            "Could not verify this month's GitHub Actions usage; publishing is blocked to avoid exceeding the configured cap."
        ) from error
    if not isinstance(payload, dict) or not isinstance(payload.get("total_count"), int):
        raise RuntimeError("GitHub Actions returned an invalid monthly run count; publishing is blocked.")
    return payload["total_count"]


def main():
    try:
        limit = monthly_run_limit()
        used = get_monthly_run_count()
    except (RuntimeError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    remaining = remaining_run_count(used, limit)
    print(f"GitHub Pages workflow runs this month: {used}/{limit}.")
    if remaining == 0:
        print("Monthly Pages publish cap reached. No push will be made.", file=sys.stderr)
        return 1
    print(f"Monthly Pages runs remaining before cap: {remaining}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
