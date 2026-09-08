#!/usr/bin/env python3
"""Xuyiming：只读收集 Git 变更；改编自 BaiTu-iOS/workshop，见插件 LICENSE。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


class ReviewError(Exception):
    """The requested review input cannot be collected reliably."""


def git(root: Path, *args: str, allowed: tuple = (0,)) -> bytes:
    result = subprocess.run(
        ["git", "--no-optional-locks", "-C", str(root), *args],
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if result.returncode not in allowed:
        raise ReviewError(result.stderr.decode(errors="replace").strip())
    return result.stdout


def revision(root: Path, ref: str) -> str:
    return git(root, "rev-parse", "--verify", "--end-of-options", ref + "^{commit}").decode().strip()


def default_base(root: Path) -> str:
    remote = git(root, "symbolic-ref", "-q", "refs/remotes/origin/HEAD", allowed=(0, 1)).decode().strip()
    candidates = [remote] if remote else []
    candidates += ["refs/remotes/origin/main", "refs/remotes/origin/master", "refs/heads/main", "refs/heads/master"]
    for candidate in candidates:
        try:
            revision(root, candidate)
            return candidate
        except ReviewError:
            continue
    raise ReviewError("Cannot resolve default branch; supply --base <ref>.")


def index_digest(root: Path) -> str:
    # Covers staged caller context as well as the changed files. No write-tree.
    return hashlib.sha256(git(root, "ls-files", "--stage", "-z")).hexdigest()


def collect(root: Path, scope: str, base_ref: str | None = None) -> tuple:
    head_raw = git(root, "rev-parse", "--verify", "HEAD", allowed=(0, 128)).decode().strip()
    head = head_raw or None
    historical = scope == "branch" or scope.startswith("commit:")
    if base_ref and not historical:
        raise ReviewError("--base applies only to branch or commit:<ref>.")
    if not historical and git(root, "ls-files", "--unmerged", "-z"):
        raise ReviewError("Unmerged index: resolve conflicts before reviewing this mutable scope.")
    before_index = index_digest(root) if not historical else None
    # hash-object without -w computes the repository's SHA-1/SHA-256 empty tree.
    empty = git(root, "hash-object", "-t", "tree", "--stdin").decode().strip()
    base = head or empty
    target = "worktree"
    if scope == "all":
        diff_args = [base]
    elif scope == "staged":
        diff_args = ["--cached", base]
        target = "index"
    elif scope == "unstaged":
        base = "index"
        diff_args = []
    elif scope == "branch":
        if not head:
            raise ReviewError("branch scope requires HEAD.")
        base_ref = base_ref or default_base(root)
        bases = git(root, "merge-base", "--all", revision(root, base_ref), head).decode().splitlines()
        if len(bases) != 1:
            raise ReviewError("Expected one merge base; choose an explicit commit scope/base.")
        base, target = bases[0], head
        diff_args = [base, target]
    elif scope.startswith("commit:"):
        target = revision(root, scope.removeprefix("commit:"))
        parents = git(root, "rev-list", "--parents", "-n", "1", target).decode().split()[1:]
        if len(parents) > 1 and not base_ref:
            raise ReviewError("Merge commit: supply --base <parent-ref> to select comparison semantics.")
        base = revision(root, base_ref) if base_ref else (parents[0] if parents else empty)
        diff_args = [base, target]
    else:
        raise ReviewError("scope must be all, staged, unstaged, branch or commit:<ref>.")

    options = ["--no-ext-diff", "--no-textconv", "--no-renames", "--no-color", "--ignore-submodules=none"]
    raw = git(root, "diff", *options, "--name-status", "-z", *diff_args, "--").split(b"\0")
    files = [{"status": raw[i].decode(), "path": os.fsdecode(raw[i + 1])} for i in range(0, len(raw) - 1, 2)]
    patch = git(root, "diff", *options, "--full-index", "--src-prefix=a/", "--dst-prefix=b/", *diff_args, "--")
    patch_parts = [patch]
    limitations = []
    if scope in ("all", "unstaged"):
        for name in git(root, "ls-files", "--others", "--exclude-standard", "-z").split(b"\0"):
            if not name:
                continue
            path = os.fsdecode(name)
            file = root / path
            files.append({"status": "?", "path": path})
            if not file.is_symlink() and not file.is_file():
                limitations.append(f"Untracked non-file requires manual inspection: {path}")
                continue
            # Git handles symlink contents and binary detection; exit 1 means differences.
            patch_parts.append(git(root, "diff", "--no-index", *options, "--full-index", "--", "/dev/null", "./" + path, allowed=(0, 1)))
    patch = b"".join(patch_parts)
    if before_index is not None and before_index != index_digest(root):
        raise ReviewError("Index changed during collection; retry after edits finish.")
    if not historical and head != (git(root, "rev-parse", "--verify", "HEAD", allowed=(0, 128)).decode().strip() or None):
        raise ReviewError("HEAD changed during collection; retry after edits finish.")
    if b"Binary files " in patch:
        limitations.append("Binary contents are not represented by text hunks; inspect affected behavior separately.")
    if b"Subproject commit " in patch or b"-dirty" in patch:
        limitations.append("Submodule changes require a separate review inside the submodule.")
    context = {
        "scope": scope, "base_ref": base_ref, "base": base, "target": target,
        "head": head, "index_digest": before_index, "files": files,
        "diff_sha256": hashlib.sha256(patch).hexdigest(), "limitations": limitations,
    }
    return context, patch


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--scope", default="all")
    parser.add_argument("--base")
    parser.add_argument("--out", type=Path, help="New directory for context.json and changes.diff; never overwritten")
    args = parser.parse_args()
    try:
        root = Path(os.fsdecode(git(Path(args.repo), "rev-parse", "--show-toplevel")).removesuffix("\n"))
        context, patch = collect(root, args.scope, args.base)
        metadata = json.dumps(context, ensure_ascii=True, indent=2) + "\n"
        if args.out:
            args.out.mkdir(parents=True, exist_ok=False)
            (args.out / "context.json").write_text(metadata, encoding="utf-8")
            (args.out / "changes.diff").write_bytes(patch)
            print(metadata, end="")
            print(f"Diff saved to {args.out / 'changes.diff'}")
        else:
            sys.stdout.buffer.write(metadata.encode() + b"\n--- REVIEW DIFF ---\n" + patch)
        return 0
    except (ReviewError, OSError) as exc:
        print(f"review input error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
