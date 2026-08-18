#!/usr/bin/env python3
"""
Validates that a branch's commits respect the scope declared in its
.project/review-plan.json admission commit.

Usage: python scripts/check_review_plan.py [base-branch]
(default base branch: main)

Exits non-zero and prints why if:
- the branch's first commit isn't a review-plan-only commit
- review-plan.json is missing or malformed
- the branch's cumulative diff exceeds max_changed_files / max_changed_lines
- any changed file falls outside allowed_path_patterns

Wire this in as a required CI check on protected branches.
"""
import json
import subprocess
import sys
from fnmatch import fnmatch

PLAN_PATH = ".project/review-plan.json"


def sh(*args: str) -> str:
    return subprocess.run(
        args, capture_output=True, text=True, check=True
    ).stdout


def main() -> int:
    base = sys.argv[1] if len(sys.argv) > 1 else "main"
    commits = sh("git", "log", f"{base}..HEAD", "--format=%H").split()
    if not commits:
        print("No commits ahead of base branch — nothing to check.")
        return 0

    first_commit = commits[-1]  # oldest first
    plan_files = sh(
        "git", "show", "--name-only", "--format=", first_commit
    ).split()

    if plan_files != [PLAN_PATH]:
        print(
            f"FAIL: first commit on this branch must change only "
            f"{PLAN_PATH}, found: {plan_files}"
        )
        return 1

    try:
        plan = json.loads(sh("git", "show", f"{first_commit}:{PLAN_PATH}"))
    except json.JSONDecodeError as exc:
        print(f"FAIL: {PLAN_PATH} is not valid JSON: {exc}")
        return 1

    try:
        patterns = plan["allowed_path_patterns"]
        max_files = plan["max_changed_files"]
        max_lines = plan["max_changed_lines"]
    except KeyError as exc:
        print(f"FAIL: {PLAN_PATH} is missing required key: {exc}")
        return 1

    diff_stat = sh("git", "diff", "--numstat", f"{first_commit}..HEAD")
    changed_files = []
    total_lines = 0
    for line in diff_stat.splitlines():
        added, removed, path = line.split("\t")
        added = int(added) if added != "-" else 0
        removed = int(removed) if removed != "-" else 0
        changed_files.append(path)
        total_lines += added + removed

    if len(changed_files) > max_files:
        print(f"FAIL: {len(changed_files)} files changed, max is {max_files}")
        return 1

    if total_lines > max_lines:
        print(f"FAIL: {total_lines} lines changed, max is {max_lines}")
        return 1

    for path in changed_files:
        if not any(fnmatch(path, pat) for pat in patterns):
            print(f"FAIL: {path} is outside allowed_path_patterns")
            return 1

    print(
        f"OK: {len(changed_files)} files, {total_lines} lines, "
        f"all within declared scope."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
