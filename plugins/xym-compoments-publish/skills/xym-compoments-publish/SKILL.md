---
name: xym-compoments-publish
description: Inspect and publish local CocoaPods components with Wukong, then offer to sync released versions into Vone/Poppo/DoraLive Podfiles on develop. Use for component releases, release settings, or post-release project version sync. Explicit publishing needs no second confirmation; project sync and pushing require separate approval.
---

# Xym Compoments Publish

Publish the CocoaPods component in the current local Git repository through Wukong. An explicit request to publish authorizes execution with the defaults below and any user-provided overrides. Inspect the repository, show a concise settings summary, and invoke Wukong directly without asking for a second confirmation. A request only to inspect parameters, prepare a command, or edit this skill does not authorize a component release. If the user explicitly asks to preview or confirm first, respect that request.

## Resolve release settings

Use the repository explicitly named by the user; otherwise use the current working directory. Run `scripts/release_context.py --project-path <path>` from this skill directory to collect the component and the three release settings without changing the repository.

Resolve the defaults as follows:

- **Release note**: read all non-merge commits reachable from `HEAD` but not from the latest reachable Wukong release commit. A Wukong release commit has a subject such as `[Update] (163.b2)` and its Podspec version at that commit must match the version in the subject. If no such commit exists, fall back to the most recent reachable Git tag. This is a Git reachability range (`release-ref..HEAD`), not a wall-clock or first-parent range. Summarize the actual changes into **1–4 key points expressed as one Chinese sentence, at most 25 characters total**, optionally separated by `，`. The limit includes punctuation, spaces, Latin letters, and digits (Python `len(note)`); use no line breaks, numbering, bullets, emoji, commit hashes, or conventional-commit prefixes. The 1–4 limit applies to summarized points, not the number of source commits: consider the entire increment, merge duplicate themes, and prioritize substantive changes. Preserve meaning; never invent improvements or simply concatenate/truncate subjects. If subjects are unclear, inspect the relevant commit diffs before summarizing; if still unclear, ask for a release note. Example: `优化进房流程，修复消息重复，完善异常处理`.

`release_context.py` returns raw evidence in `increment_commits`, leaves `defaults.note` null, and sets `defaults.note_requires_summary` when commits exist. Generate the default note yourself from that evidence before constructing the command; null is not a usable note. Check the final generated sentence is nonempty, single-line, contains 1–4 substantive points, and `len(note) <= 25`; rewrite overlong summaries rather than cutting them off. An explicit user-provided release note remains an override and is not silently shortened.
- **Obfuscation**: default to disabled for `BTRouter`, `BTAssets`, and `BTIMService`; accept `BTAssests` as an alias for the assets component. Default to enabled for every other component. Component matching is case-insensitive.
- **Environment**: default to the test environment, represented by Wukong's `--beta` flag. Production is represented by omitting `--beta`.

If no reachable release node or no incremental commit is found, do not invent a release note. Ask the user to provide the last release ref or an explicit release note. If the repository is dirty, detached, lacks exactly one root-level `.podspec`, or Wukong is unavailable, report the condition and do not publish until it is addressed.

## Release summary

Before publishing, display these effective settings as a progress update, followed by any blocking repository warnings. This summary does not pause execution:

```text
是否需要混淆：是/否（说明默认规则或用户覆盖）
发布信息：<release note>
发布环境：测试环境（--beta）/正式环境
```

Also show the component name, podspec version, branch, current commit, last release node, incremental commit count, and a safely quoted command preview. Keep user-provided overrides separate from generated defaults and use the overrides as the effective release settings. Do not ask whether to proceed when the user has already requested publishing.

## Publish

Immediately before publishing, rerun `release_context.py` and use its current results. Require no blocking warnings and verify that the repository and component still match the requested target. If release metadata changed, regenerate the release note and command using the refreshed context while preserving user overrides, show the updated summary, and proceed without a confirmation round. If the requested target or required settings cannot be determined, report the specific missing information instead of guessing.

Build the Wukong invocation from fixed arguments rather than accepting arbitrary shell text:

```text
wukong pod publish --note <release-note> [--beta] [--mixup]
```

- Add `--beta` only for the test environment.
- Add `--mixup` only when obfuscation is enabled.
- Pass the release note as one quoted argument.
- Execute from the repository root.

On a publish request, execute the command as soon as the checks pass. Do not stop at printing the command or displaying the settings. Stream or summarize progress without exposing credentials. After completion, report the component, version, environment, Git commit, and the authoritative success or failure line.

Wukong can create tags, upload artifacts, or update Specs before a later stage fails. If the result is interrupted or ambiguous, inspect the resulting Git tags and Specs state and report what completed and what remains uncertain. Do not automatically repeat an ambiguous publish; a retry requires a new user request.

## Offer project version sync after success

After a verified successful release, read [references/project-sync.md](references/project-sync.md). Collect every exact version actually published by this invocation; never derive a new version from the old podspec or invent a platform suffix. A suffix containing `VO` maps to Vone; a `PLA` suffix maps to Poppo; a `DRL` suffix maps to DoraLive. Match PLA/DRL as dot- or hyphen-delimited markers, case-insensitively, and preserve the exact published version including any Swift suffix. A single identified platform version is offered only to that platform. Unmarked or ambiguous versions require the user to choose the target project(s) and exact version mapping. If the DoraLive repository path is not explicitly known, ask for it before sync; do not guess or clone a repository.

Ask whether to sync before changing any app repository. A component release request alone does not approve project sync. After approval, use `scripts/sync_projects.py` to fast-forward the selected clean `develop` branches, update only the component's Podfile version, and commit locally with the release note. Then ask separately whether to push those specific commits. Do not run `pod install`, change lockfiles, or automatically push. If the user declines sync, the component release is still complete.

A request only to sync an already released version enters the same reference workflow without running Wukong again. Editing or upgrading this skill never authorizes a release or an app repository change.

The app repository's complete commit message must be the component's actual release note itself (the note passed to Wukong), not a generic version-update title with the note relegated to the body. For a generated note, reuse the same short summary verbatim rather than expanding the original Git subjects or summarizing again. Preserve explicit user overrides and historical release notes, including multiline notes, and verify the resulting message before offering to push.
