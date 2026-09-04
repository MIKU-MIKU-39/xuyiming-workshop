---
name: xym-compoments-publish
description: Inspect and publish a local CocoaPods component with Wukong. Use when the user asks to publish/release a component, run `wukong pod publish`, or determine component release notes, obfuscation, and beta/production settings. Always confirm the resolved release settings immediately before publishing.
---

# Xym Compoments Publish

Publish the CocoaPods component in the current local Git repository through Wukong. Treat publishing as an external, potentially partial mutation: inspect first, show the resolved settings, and require explicit user confirmation before invoking Wukong.

## Resolve release settings

Use the repository explicitly named by the user; otherwise use the current working directory. Run `scripts/release_context.py --project-path <path>` from this skill directory to collect the component and the three release settings without changing the repository.

Resolve the defaults as follows:

- **Release note**: use the subjects of all non-merge commits reachable from `HEAD` but not from the latest reachable Wukong release commit, ordered oldest to newest and joined with `；`. A Wukong release commit has a subject such as `[Update] (163.b2)` and its Podspec version at that commit must match the version in the subject. If no such commit exists, fall back to the most recent reachable Git tag. Preserve commit subjects rather than rewriting their meaning. This is a Git reachability range (`release-ref..HEAD`), not a wall-clock or first-parent range.
- **Obfuscation**: default to disabled for `BTRouter`, `BTAssets`, and `BTIMService`; accept `BTAssests` as an alias for the assets component. Default to enabled for every other component. Component matching is case-insensitive.
- **Environment**: default to the test environment, represented by Wukong's `--beta` flag. Production is represented by omitting `--beta`.

If no reachable release node or no incremental commit is found, do not invent a release note. Ask the user to provide the last release ref or an explicit release note. If the repository is dirty, detached, lacks exactly one root-level `.podspec`, or Wukong is unavailable, report the condition and do not publish until it is addressed.

## Confirmation

Before publishing, display exactly these decision fields prominently, followed by any blocking repository warnings:

```text
是否需要混淆：是/否（说明默认规则或用户覆盖）
发布信息：<release note>
发布环境：测试环境（--beta）/正式环境
```

Also show the component name, podspec version, branch, current commit, last release node, incremental commit count, and a safely quoted command preview. Ask the user to confirm or edit the three decision fields. Keep the script-computed values as the confirmation baseline and keep any user-edited values separately as the effective release settings. A request to inspect, prepare, or create this skill is not approval to publish.

## Publish

Immediately before publishing, rerun `release_context.py`. Require the refreshed context to have no blocking warnings, then compare its repository path, component, podspec version, branch, `HEAD`, dirty state, last release node, incremental commits, generated defaults, and Wukong executable with the script-computed baseline saved when the user confirmed. Do not compare a refreshed default with a user override. If the baseline changed, show a refreshed plan and obtain confirmation again; otherwise publish with the separately stored effective settings.

Build the Wukong invocation from fixed arguments rather than accepting arbitrary shell text:

```text
wukong pod publish --note <release-note> [--beta] [--mixup]
```

- Add `--beta` only for the test environment.
- Add `--mixup` only when obfuscation is enabled.
- Pass the release note as one quoted argument.
- Execute from the repository root.

Run the command only after explicit confirmation. Stream or summarize progress without exposing credentials. After completion, report the component, version, environment, Git commit, and the authoritative success or failure line.

Wukong can create tags, upload artifacts, or update Specs before a later stage fails. If the result is interrupted or ambiguous, inspect the resulting Git tags and Specs state and ask the user before retrying. Never retry a publish automatically.
