# GitHub 接口参考

维护者：Xuyiming。脚本封装固定操作，不接受任意 GraphQL、shell 或任意 URL 作为执行入口。

- [gh api](https://cli.github.com/manual/gh_api)：使用 `--input -` 从 stdin 传 JSON；GraphQL variables 单独编码。
- [Pull request GraphQL 对象](https://docs.github.com/en/graphql/reference/pulls)：读取 reviewThreads、comments 和 pageInfo，两层都必须分页。
- [评审评论回复接口](https://docs.github.com/en/rest/pulls/comments#create-a-reply-for-a-review-comment)：`POST /repos/{owner}/{repo}/pulls/{pull_number}/comments/{comment_id}/replies`；comment_id 必须是根评审评论的 REST databaseId。
- [GraphQL mutations](https://docs.github.com/en/graphql/reference/mutations#resolvereviewthread)：`resolveReviewThread` 使用线程的 GraphQL ID，不是评论 databaseId。

PR 的顶层评论、reviews 和 inline review threads 是不同对象；不能仅检查前两者就声称未解决线程为空。回查时比较返回的线程 ID、正文和状态，避免因请求结果不明产生重复回复。
