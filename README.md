# Jira & Confluence MCP Servers

PythonベースのMCP（Model Context Protocol）サーバーで、JiraとConfluenceのAPIと対話できます。

## セットアップ

### 1. 依存関係のインストール

```bash
uv sync
```

### 2. 環境変数の設定

`.env.example`を`.env`にコピーして、認証情報を設定します：

```bash
cp .env.example .env
```

以下の情報を設定してください：
- `JIRA_URL` / `CONFLUENCE_URL`: AtlassianインスタンスのURL
- `JIRA_USERNAME` / `CONFLUENCE_USERNAME`: メールアドレス
- `JIRA_API_TOKEN` / `CONFLUENCE_API_TOKEN`: APIトークン（[こちら](https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/)から生成）
- `JIRA_CLOUD` / `CONFLUENCE_CLOUD`: クラウド版の場合は`true`、サーバー版の場合は`false`

## 使用方法

### Jira MCPサーバーの起動

```bash
uv run python src/jira_server.py
```

### Confluence MCPサーバーの起動

```bash
uv run python src/confluence_server.py
```

## 利用可能なツール

### Jira MCP

- `jira_search_issues`: JQLを使用してイシューを検索
- `jira_get_issue`: 特定のイシューの詳細を取得
- `jira_create_issue`: 新しいイシューを作成
- `jira_update_issue`: 既存のイシューを更新
- `jira_add_comment`: イシューにコメントを追加
- `jira_transition_issue`: イシューのステータスを変更
- `jira_get_projects`: プロジェクト一覧を取得

### Confluence MCP

- `confluence_search_content`: CQLを使用してコンテンツを検索
- `confluence_get_page`: ページの詳細を取得
- `confluence_create_page`: 新しいページを作成
- `confluence_update_page`: 既存のページを更新
- `confluence_delete_page`: ページを削除
- `confluence_get_spaces`: スペース一覧を取得
- `confluence_get_page_children`: 子ページを取得
- `confluence_add_attachment`: ページに添付ファイルを追加

## Claude Desktopでの設定

Claude Desktopの設定ファイル（`~/Library/Application Support/Claude/claude_desktop_config.json`）に以下を追加：

```json
{
  "mcpServers": {
    "jira": {
      "command": "uv",
      "args": ["run", "python", "/path/to/jira-mcp/src/jira_server.py"],
      "env": {
        "JIRA_URL": "https://your-domain.atlassian.net",
        "JIRA_USERNAME": "your-email@example.com",
        "JIRA_API_TOKEN": "your-api-token",
        "JIRA_CLOUD": "true"
      }
    },
    "confluence": {
      "command": "uv",
      "args": ["run", "python", "/path/to/jira-mcp/src/confluence_server.py"],
      "env": {
        "CONFLUENCE_URL": "https://your-domain.atlassian.net",
        "CONFLUENCE_USERNAME": "your-email@example.com",
        "CONFLUENCE_API_TOKEN": "your-api-token",
        "CONFLUENCE_CLOUD": "true"
      }
    }
  }
}
```

## 使用例

### Jira

```python
# イシューの検索
await jira_search_issues({"jql": "project = PROJ AND status = 'In Progress'", "max_results": 10})

# イシューの作成
await jira_create_issue({
    "project_key": "PROJ",
    "summary": "新しいタスク",
    "description": "タスクの説明",
    "issue_type": "Task",
    "priority": "Medium"
})

# イシューのステータス変更
await jira_transition_issue({"issue_key": "PROJ-123", "status": "Done"})
```

### Confluence

```python
# ページの検索
await confluence_search_content({"cql": "space = DEV AND title ~ 'API'"})

# ページの作成
await confluence_create_page({
    "space_key": "DEV",
    "title": "新しいドキュメント",
    "content": "<p>ページの内容</p>"
})

# ページの更新
await confluence_update_page({
    "page_id": "123456",
    "content": "<p>更新された内容</p>",
    "version_comment": "APIドキュメントを更新"
})
```

## ライセンス

MIT