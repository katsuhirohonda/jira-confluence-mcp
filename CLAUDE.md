# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains Python-based MCP (Model Context Protocol) servers for interacting with Jira and Confluence APIs. The project uses `uv` for package management and requires Python 3.10+.

## Key Commands

### Setup and Dependencies
```bash
# Install dependencies
uv sync

# Run Jira MCP server
uv run python src/jira_server.py

# Run Confluence MCP server
uv run python src/confluence_server.py
```

### Environment Configuration
Before running the servers, copy `.env.example` to `.env` and configure:
- `JIRA_URL` / `CONFLUENCE_URL`: Atlassian instance URL
- `JIRA_USERNAME` / `CONFLUENCE_USERNAME`: Email address
- `JIRA_API_TOKEN` / `CONFLUENCE_API_TOKEN`: API token
- `JIRA_CLOUD` / `CONFLUENCE_CLOUD`: `true` for cloud, `false` for server

## Architecture

### MCP Server Structure
Both servers follow the same pattern:

1. **Configuration Classes** (`JiraConfig`, `ConfluenceConfig`): Handle environment variables and connection settings
2. **Model Classes** (`JiraIssue`, `ConfluencePage`): Define data structures
3. **Server Classes** (`JiraMCPServer`, `ConfluenceMCPServer`): 
   - Initialize MCP server with tool handlers
   - Manage client connections to Atlassian APIs
   - Implement tool methods that wrap API calls

### Tool Implementation Pattern
Each tool method follows this structure:
1. Check/initialize client connection
2. Extract arguments
3. Make API call using `atlassian-python-api`
4. Format response as `TextContent`
5. Handle errors gracefully

### Available Tools

**Jira Tools:**
- `jira_search_issues`: Search with JQL
- `jira_get_issue`: Get issue details
- `jira_create_issue`: Create new issue
- `jira_update_issue`: Update existing issue
- `jira_add_comment`: Add comment to issue
- `jira_transition_issue`: Change issue status
- `jira_get_projects`: List projects

**Confluence Tools:**
- `confluence_search_content`: Search with CQL
- `confluence_get_page`: Get page details
- `confluence_create_page`: Create new page
- `confluence_update_page`: Update existing page
- `confluence_delete_page`: Delete page
- `confluence_get_spaces`: List spaces
- `confluence_get_page_children`: Get child pages
- `confluence_add_attachment`: Add file attachment

## Development Notes

- The servers use `stdio_server` for communication with MCP clients
- All API responses are returned as JSON-formatted text
- Error handling returns error messages as `TextContent`
- The `atlassian-python-api` library handles authentication and API calls
- Both servers can be configured for cloud or server/data center instances