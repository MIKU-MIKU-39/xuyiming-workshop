#!/usr/bin/env python3
"""Build a read-only CocoaPods component release context.

Author: Xuyiming
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


# BTAssests is retained as an alias for the user-provided spelling of BTAssets.
MIXUP_EXEMPT_COMPONENTS = {
    "btrouter",
    "btassets",
    "btassests",
    "btimservice",
}


class ReleaseContextError(RuntimeError):
    """Raised when the local repository cannot produce a release context."""


def run_git(repository: Path, *arguments: str, check: bool = True) -> str:
    """Run a read-only Git query and return trimmed standard output."""
    result = subprocess.run(
        ["git", *arguments],
        cwd=repository,
        text=True,
        capture_output=True,
        check=False,
    )
    if check and result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "Git query failed"
        raise ReleaseContextError(message)
    # Preserve leading spaces because `git status --porcelain` encodes index and
    # worktree state in its first two columns.
    return result.stdout.rstrip("\n") if result.returncode == 0 else ""


def parse_podspec_value(contents: str, key: str) -> str | None:
    """Read a simple literal Podspec assignment such as `s.version = '1.0'`."""
    pattern = rf"\b(?:s|spec)\.{re.escape(key)}\s*=\s*['\"]([^'\"]+)['\"]"
    for line in contents.splitlines():
        if line.lstrip().startswith("#"):
            continue
        match = re.search(pattern, line)
        if match:
            return match.group(1).strip()
    return None


def collect_increment_commits(repository: Path, last_release_ref: str) -> list[dict[str, str]]:
    """Collect non-merge commit subjects after the last release in chronological order."""
    output = run_git(
        repository,
        "log",
        "--reverse",
        "--no-merges",
        "--format=%H%x1f%s",
        f"{last_release_ref}..HEAD",
    )
    commits: list[dict[str, str]] = []
    for line in output.splitlines():
        if "\x1f" not in line:
            continue
        commit_hash, subject = line.split("\x1f", 1)
        commits.append({"sha": commit_hash, "subject": subject.strip()})
    return commits


def find_wukong_release_commit(
    repository: Path, podspec_relative_path: Path
) -> tuple[str, str] | None:
    """Find the newest reachable `[Update] (...)` commit matching its Podspec."""
    output = run_git(repository, "log", "--format=%H%x1f%s", "HEAD")
    release_pattern = re.compile(r"^\[Update\]\s*\(([^)]+)\)$", re.IGNORECASE)
    for line in output.splitlines():
        if "\x1f" not in line:
            continue
        commit_hash, subject = line.split("\x1f", 1)
        match = release_pattern.fullmatch(subject.strip())
        if not match:
            continue

        historical_podspec = run_git(
            repository,
            "show",
            f"{commit_hash}:{podspec_relative_path.as_posix()}",
            check=False,
        )
        historical_version = parse_podspec_value(historical_podspec, "version")
        if historical_version == match.group(1).strip():
            return commit_hash, subject.strip()
    return None


def build_context(project_path: Path) -> dict[str, object]:
    """Resolve repository metadata and default release decisions without side effects."""
    requested_path = project_path.expanduser().resolve()
    if not requested_path.exists():
        raise ReleaseContextError(f"Project path does not exist: {requested_path}")

    repository_text = run_git(requested_path, "rev-parse", "--show-toplevel")
    repository = Path(repository_text).resolve()
    podspecs = sorted(repository.glob("*.podspec"))
    if len(podspecs) != 1:
        raise ReleaseContextError(
            f"Expected exactly one root-level .podspec in {repository}, found {len(podspecs)}"
        )

    podspec = podspecs[0]
    podspec_contents = podspec.read_text(encoding="utf-8")
    component = parse_podspec_value(podspec_contents, "name") or podspec.stem
    version = parse_podspec_value(podspec_contents, "version")
    branch = run_git(repository, "branch", "--show-current")
    head = run_git(repository, "rev-parse", "HEAD")
    dirty_entries = run_git(repository, "status", "--porcelain").splitlines()
    release_commit = find_wukong_release_commit(repository, podspec.relative_to(repository))
    if release_commit:
        last_release_ref, last_release_label = release_commit
        last_release_source = "wukong_update_commit"
    else:
        last_release_ref = run_git(
            repository,
            "describe",
            "--tags",
            "--abbrev=0",
            "HEAD",
            check=False,
        )
        last_release_label = last_release_ref
        last_release_source = "git_tag" if last_release_ref else None

    commits = collect_increment_commits(repository, last_release_ref) if last_release_ref else []
    # 原始提交只作为证据；由技能做语义总结，不能把拼接或截断当成摘要。
    normalized_component = component.casefold()
    mixup = normalized_component not in MIXUP_EXEMPT_COMPONENTS
    warnings: list[str] = []

    if not branch:
        warnings.append("Repository is in detached HEAD state.")
    if dirty_entries:
        warnings.append("Repository has uncommitted changes.")
    if not version:
        warnings.append("Podspec version could not be resolved from a literal assignment.")
    if not last_release_ref:
        warnings.append("No reachable Wukong release commit or Git tag was found; provide the last release ref or release note.")
    elif not commits:
        warnings.append("No incremental non-merge commits were found after the last release node.")

    wukong_path = shutil.which("wukong")
    if not wukong_path:
        warnings.append("The wukong executable is unavailable on PATH.")

    return {
        "project_path": str(repository),
        "component": component,
        "podspec": str(podspec),
        "version": version,
        "branch": branch or None,
        "head": head,
        "dirty": bool(dirty_entries),
        "dirty_entries": dirty_entries,
        "last_release_ref": last_release_ref or None,
        "last_release_label": last_release_label or None,
        "last_release_source": last_release_source,
        "increment_commit_count": len(commits),
        "increment_commits": commits,
        "wukong_path": wukong_path,
        "defaults": {
            "mixup": mixup,
            "mixup_reason": (
                f"{component} is exempt from obfuscation."
                if not mixup
                else f"{component} uses the default obfuscation policy."
            ),
            "note": None,
            "note_requires_summary": bool(commits),
            "environment": "beta",
            "environment_flag": "--beta",
        },
        "ready_for_confirmation": not warnings,
        "warnings": warnings,
    }


def main() -> int:
    """Parse arguments and print the resolved release context as UTF-8 JSON."""
    parser = argparse.ArgumentParser(
        description="Inspect a local CocoaPods component before Wukong publishing."
    )
    parser.add_argument(
        "--project-path",
        default=".",
        help="Path inside the component Git repository. Defaults to the current directory.",
    )
    arguments = parser.parse_args()

    try:
        context = build_context(Path(arguments.project_path))
    except (OSError, ReleaseContextError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False, indent=2))
        return 1

    print(json.dumps(context, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
