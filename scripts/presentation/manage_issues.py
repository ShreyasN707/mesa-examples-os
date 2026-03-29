#!/usr/bin/env python3
# Manage a GitHub issue tracking CI health failures.

import argparse
import json
import os
import sys
from pathlib import Path

import requests

ISSUE_TITLE = "CI Health: Example Failures Detected"
ISSUE_LABEL = "ci-health"
GH_API = "https://api.github.com"


def load_registries(registry_dir: Path) -> list:
    """Load all JSON records from the registry."""
    records = []
    for f in sorted(registry_dir.glob("*.json")):
        try:
            records.append(json.loads(f.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            continue
    return records


def should_flag(r: dict) -> bool:
    """Check if an example failure warrants an issue."""
    status = str(r.get("meta", {}).get("status", "")).lower()
    health = r.get("ci", {}).get("health", "")
    if status == "showcase" and health in ("warning", "broken"):
        return True
    return bool(status == "standard" and health == "broken")


def all_clear(records: list) -> bool:
    """True if all standard/showcase examples are passing."""
    for r in records:
        status = str(r.get("meta", {}).get("status", "")).lower()
        health = r.get("ci", {}).get("health", "")
        if status in ("standard", "showcase") and health in ("warning", "broken"):
            return False
    return True


def build_body(flagged: list) -> str:
    """Generate Markdown body for the health issue."""
    lines = [
        "The following examples need attention:\n",
        "| Example | Status | Health | Warning |",
        "| --- | --- | --- | --- |",
    ]
    for r in sorted(flagged, key=lambda x: x.get("location", "")):
        ex_id = r.get("location", "Unknown")
        status = str(r.get("meta", {}).get("status", "")).lower()
        lines.append(
            f"| `{ex_id}` | {status} | **{r.get('ci', {}).get('health', '')}** | {r.get('ci', {}).get('warning') or '—'} |"
        )
    lines.append("\n_Last updated automatically by scheduled CI._")
    return "\n".join(lines)


def _headers(token: str) -> dict:
    return {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}


def ensure_label(repo: str, token: str):
    """Create the health label if missing."""
    url = f"{GH_API}/repos/{repo}/labels/{ISSUE_LABEL}"
    if requests.get(url, headers=_headers(token), timeout=15).status_code == 404:
        requests.post(
            f"{GH_API}/repos/{repo}/labels",
            headers=_headers(token),
            json={
                "name": ISSUE_LABEL,
                "color": "d93f0b",
                "description": "CI health tracking",
            },
            timeout=15,
        )


def find_existing_issue(repo: str, token: str):
    """Find an open health issue."""
    params = {"state": "open", "labels": ISSUE_LABEL}
    resp = requests.get(
        f"{GH_API}/repos/{repo}/issues",
        headers=_headers(token),
        params=params,
        timeout=15,
    )
    return next((i for i in resp.json() if i.get("title") == ISSUE_TITLE), None)


def create_issue(repo: str, token: str, body: str):
    requests.post(
        f"{GH_API}/repos/{repo}/issues",
        headers=_headers(token),
        json={"title": ISSUE_TITLE, "body": body, "labels": [ISSUE_LABEL]},
        timeout=15,
    )


def update_issue(repo: str, token: str, issue_num: int, body: str):
    requests.patch(
        f"{GH_API}/repos/{repo}/issues/{issue_num}",
        headers=_headers(token),
        json={"body": body},
        timeout=15,
    )


def close_issue(repo: str, token: str, issue_num: int):
    requests.patch(
        f"{GH_API}/repos/{repo}/issues/{issue_num}",
        headers=_headers(token),
        json={"state": "closed"},
        timeout=15,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry-dir", default="registry")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--token", default=os.environ.get("GITHUB_TOKEN"))
    args = parser.parse_args()

    if not args.token:
        sys.exit("Error: GITHUB_TOKEN not set.")

    records = load_registries(Path(args.registry_dir))
    if not records:
        return

    existing = find_existing_issue(args.repo, args.token)
    if all_clear(records):
        if existing:
            close_issue(args.repo, args.token, existing["number"])
        return

    import contextlib

    with contextlib.suppress(Exception):
        ensure_label(args.repo, args.token)

    body = build_body([r for r in records if should_flag(r)])
    if existing:
        update_issue(args.repo, args.token, existing["number"], body)
    else:
        create_issue(args.repo, args.token, body)


if __name__ == "__main__":
    main()
