#!/usr/bin/env python3
"""Xuyiming：通过 gh 查询完整 PR 评审线程，并预览或执行线程回复、解决操作。"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import sys


COMMENT_FIELDS = "id databaseId body url createdAt author { login }"
THREAD_QUERY = """
query($owner: String!, $repo: String!, $number: Int!, $cursor: String) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $number) {
      number title url state headRefOid reviewDecision
      reviewThreads(first: 100, after: $cursor) {
        nodes {
          id isResolved isOutdated path line originalLine
          comments(first: 100) {
            nodes { COMMENT_FIELDS }
            pageInfo { hasNextPage endCursor }
          }
        }
        pageInfo { hasNextPage endCursor }
      }
    }
  }
}
""".replace("COMMENT_FIELDS", COMMENT_FIELDS)
COMMENTS_QUERY = """
query($id: ID!, $cursor: String) {
  node(id: $id) {
    ... on PullRequestReviewThread {
      comments(first: 100, after: $cursor) {
        nodes { COMMENT_FIELDS }
        pageInfo { hasNextPage endCursor }
      }
    }
  }
}
""".replace("COMMENT_FIELDS", COMMENT_FIELDS)
RESOLVE_QUERY = """
mutation($threadId: ID!) {
  resolveReviewThread(input: {threadId: $threadId}) {
    thread { id isResolved }
  }
}
"""


class ReviewError(Exception):
    pass


class GitHub:
    def __init__(self, hostname="github.com", timeout=30):
        self.hostname = hostname
        self.timeout = timeout

    def request(self, endpoint, payload):
        # JSON 经 stdin 发送，评论中的换行、引号和 shell 字符不会被执行。
        result = subprocess.run(
            ["gh", "api", "--hostname", self.hostname, endpoint, "--method", "POST", "--input", "-"],
            input=json.dumps(payload), text=True, capture_output=True,
            timeout=self.timeout, check=False,
        )
        if result.returncode:
            raise ReviewError(result.stderr.strip() or "GitHub 请求失败")
        data = json.loads(result.stdout)
        if not isinstance(data, dict):
            raise ReviewError("GitHub 返回格式异常，无法确认结果。")
        if data.get("errors"):
            raise ReviewError("GitHub GraphQL 返回错误；没有把部分结果当作完整结果。")
        return data

    def graphql(self, query, variables):
        return self.request("graphql", {"query": query, "variables": variables})["data"]


def next_cursor(connection, seen):
    info = connection["pageInfo"]
    if not info["hasNextPage"]:
        return None
    cursor = info.get("endCursor")
    if not cursor or cursor in seen:
        raise ReviewError("分页游标缺失或重复，无法保证结果完整。")
    seen.add(cursor)
    return cursor


def inspect_review(client, repo, number):
    owner, repository = repo.split("/")
    cursor = None
    seen = set()
    threads = []
    metadata = None
    while True:
        result = client.graphql(THREAD_QUERY, {
            "owner": owner, "repo": repository, "number": number, "cursor": cursor,
        })
        pr = (result.get("repository") or {}).get("pullRequest")
        if not pr:
            raise ReviewError("没有找到目标 PR，或当前 gh 身份没有访问权限。")
        if metadata and metadata["headRefOid"] != pr["headRefOid"]:
            raise ReviewError("读取期间 PR 的 HEAD 已变化，请重新检查。")
        metadata = {key: value for key, value in pr.items() if key != "reviewThreads"}
        connection = pr["reviewThreads"]
        for thread in connection["nodes"]:
            thread = dict(thread)
            comment_page = thread["comments"]
            comments = list(comment_page["nodes"])
            comment_cursors = set()
            # 外层线程和每个线程的评论分别分页，不能只截取 first: N。
            comment_cursor = next_cursor(comment_page, comment_cursors)
            while comment_cursor:
                node = client.graphql(COMMENTS_QUERY, {"id": thread["id"], "cursor": comment_cursor}).get("node")
                if not node:
                    raise ReviewError("读取期间评审线程已不可见，请重新检查。")
                comment_page = node["comments"]
                comments.extend(comment_page["nodes"])
                comment_cursor = next_cursor(comment_page, comment_cursors)
            thread["comments"] = comments
            threads.append(thread)
        cursor = next_cursor(connection, seen)
        if cursor is None:
            break
    return {
        "repo": repo, "hostname": client.hostname, "pull_request": metadata,
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "threads": threads, "unresolved_count": sum(not thread["isResolved"] for thread in threads),
    }


def mutation_plan(snapshot, action, thread_id, body=None, expected_head=None):
    head = snapshot["pull_request"]["headRefOid"]
    if expected_head and expected_head != head:
        raise ReviewError("PR HEAD 与已检查的提交不一致；本次不会发送写请求。")
    matches = [thread for thread in snapshot["threads"] if thread["id"] == thread_id]
    if len(matches) != 1:
        raise ReviewError("线程不属于当前仓库/PR，或无法唯一定位。")
    thread = matches[0]
    base = {"action": action, "thread_id": thread_id, "expected_head": head, "repo": snapshot["repo"]}
    if action == "resolve":
        if thread["isResolved"]:
            return dict(base, status="already_resolved")
        return dict(base, endpoint="graphql", payload={"query": RESOLVE_QUERY, "variables": {"threadId": thread_id}})
    if not body or not body.strip():
        raise ReviewError("回复内容不能为空。")
    if not thread["comments"] or not thread["comments"][0].get("databaseId"):
        raise ReviewError("缺少根评论 databaseId，无法在线程内回复。")
    comment_id = thread["comments"][0]["databaseId"]
    number = snapshot["pull_request"]["number"]
    endpoint = f"repos/{snapshot['repo']}/pulls/{number}/comments/{comment_id}/replies"
    return dict(base, endpoint=endpoint, payload={"body": body})


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("inspect", "reply", "resolve"))
    parser.add_argument("--repo", required=True, help="owner/repo")
    parser.add_argument("--pr", required=True, type=int)
    parser.add_argument("--hostname", default="github.com", help="可指定 GitHub Enterprise 主机")
    parser.add_argument("--thread-id")
    parser.add_argument("--body-file", type=Path)
    parser.add_argument("--expected-head", help="实际写入时必须给出已核实的 PR HEAD SHA")
    parser.add_argument("--execute", action="store_true", help="实际发送写请求；默认仅预览")
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args(argv)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*", args.repo):
        parser.error("--repo 必须是 owner/repo")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.-]*", args.hostname):
        parser.error("--hostname 必须是主机名，不能包含 URL 路径")
    if args.pr < 1 or args.timeout < 1:
        parser.error("PR 编号和 timeout 必须为正整数")
    if args.action == "inspect" and (args.execute or args.thread_id or args.body_file or args.expected_head):
        parser.error("inspect 不接受写入参数")
    if args.action != "inspect" and not args.thread_id:
        parser.error("reply/resolve 需要 --thread-id")
    if args.action == "reply" and not args.body_file:
        parser.error("reply 需要 --body-file")
    if args.action != "reply" and args.body_file:
        parser.error("--body-file 仅用于 reply")
    if args.execute and not args.expected_head:
        parser.error("--execute 需要 --expected-head，防止按过期代码关闭评审线程")
    return args


def main(argv=None):
    args = parse_args(argv)
    try:
        body = args.body_file.read_text(encoding="utf-8") if args.body_file else None
        client = GitHub(args.hostname, args.timeout)
        snapshot = inspect_review(client, args.repo, args.pr)
        if args.action == "inspect":
            output = snapshot
        else:
            plan = mutation_plan(snapshot, args.action, args.thread_id, body, args.expected_head)
            if args.execute and "endpoint" in plan:
                result = client.request(plan["endpoint"], plan["payload"])
                if args.action == "resolve":
                    resolved = result["data"]["resolveReviewThread"]["thread"]
                    if resolved["id"] != args.thread_id or not resolved["isResolved"]:
                        raise ReviewError("写请求已返回，但线程解决状态未获确认；请回查后再决定下一步。")
                elif not result.get("id") or result.get("body") != body:
                    raise ReviewError("回复请求已返回，但评论 ID 或正文不符；请回查线程，不要直接重发。")
                output = {"status": "executed", "action": args.action, "result": result}
            else:
                output = {"status": plan.get("status", "preview"), "plan": plan}
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError, AttributeError, ReviewError, subprocess.TimeoutExpired) as error:
        print(f"GitHub review error: {error}", file=sys.stderr)
        if args.execute:
            print("写入结果可能不完整；请回查远端状态，勿自动重复回复。", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
