#!/usr/bin/env python3
import os
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, Resource
from pydantic import Field, BaseModel
from atlassian import Jira
from dotenv import load_dotenv

load_dotenv()


class JiraConfig(BaseModel):
    """Configuration for Jira connection"""
    url: str = Field(description="Jira instance URL")
    username: str = Field(description="Jira username/email")
    api_token: str = Field(description="Jira API token")
    cloud: bool = Field(default=True, description="Whether this is a cloud instance")


class JiraIssue(BaseModel):
    """Jira issue model"""
    key: str
    summary: str
    description: Optional[str] = None
    status: str
    assignee: Optional[str] = None
    reporter: str
    created: str
    updated: str
    priority: Optional[str] = None
    issue_type: str
    project: str


class JiraMCPServer:
    def __init__(self):
        self.server = Server("jira-mcp")
        self.jira_client: Optional[Jira] = None
        self._setup_handlers()
        
    def _setup_handlers(self):
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            return [
                Tool(
                    name="jira_search_issues",
                    description="Search for Jira issues using JQL",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "jql": {
                                "type": "string",
                                "description": "JQL query string"
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum number of results to return",
                                "default": 50
                            }
                        },
                        "required": ["jql"]
                    }
                ),
                Tool(
                    name="jira_get_issue",
                    description="Get details of a specific Jira issue",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "issue_key": {
                                "type": "string",
                                "description": "Issue key (e.g., PROJ-123)"
                            }
                        },
                        "required": ["issue_key"]
                    }
                ),
                Tool(
                    name="jira_create_issue",
                    description="Create a new Jira issue",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project_key": {
                                "type": "string",
                                "description": "Project key"
                            },
                            "summary": {
                                "type": "string",
                                "description": "Issue summary"
                            },
                            "description": {
                                "type": "string",
                                "description": "Issue description"
                            },
                            "issue_type": {
                                "type": "string",
                                "description": "Issue type (e.g., Bug, Task, Story)",
                                "default": "Task"
                            },
                            "priority": {
                                "type": "string",
                                "description": "Priority (e.g., High, Medium, Low)",
                                "default": "Medium"
                            },
                            "assignee": {
                                "type": "string",
                                "description": "Assignee username"
                            }
                        },
                        "required": ["project_key", "summary"]
                    }
                ),
                Tool(
                    name="jira_update_issue",
                    description="Update an existing Jira issue",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "issue_key": {
                                "type": "string",
                                "description": "Issue key (e.g., PROJ-123)"
                            },
                            "fields": {
                                "type": "object",
                                "description": "Fields to update",
                                "properties": {
                                    "summary": {"type": "string"},
                                    "description": {"type": "string"},
                                    "priority": {"type": "string"},
                                    "assignee": {"type": "string"}
                                }
                            }
                        },
                        "required": ["issue_key", "fields"]
                    }
                ),
                Tool(
                    name="jira_add_comment",
                    description="Add a comment to a Jira issue",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "issue_key": {
                                "type": "string",
                                "description": "Issue key (e.g., PROJ-123)"
                            },
                            "comment": {
                                "type": "string",
                                "description": "Comment text"
                            }
                        },
                        "required": ["issue_key", "comment"]
                    }
                ),
                Tool(
                    name="jira_transition_issue",
                    description="Transition a Jira issue to a different status",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "issue_key": {
                                "type": "string",
                                "description": "Issue key (e.g., PROJ-123)"
                            },
                            "status": {
                                "type": "string",
                                "description": "Target status (e.g., In Progress, Done)"
                            }
                        },
                        "required": ["issue_key", "status"]
                    }
                ),
                Tool(
                    name="jira_get_projects",
                    description="Get list of Jira projects",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> List[TextContent]:
            if not self.jira_client:
                self._connect_to_jira()
            
            try:
                if name == "jira_search_issues":
                    return await self._search_issues(arguments)
                elif name == "jira_get_issue":
                    return await self._get_issue(arguments)
                elif name == "jira_create_issue":
                    return await self._create_issue(arguments)
                elif name == "jira_update_issue":
                    return await self._update_issue(arguments)
                elif name == "jira_add_comment":
                    return await self._add_comment(arguments)
                elif name == "jira_transition_issue":
                    return await self._transition_issue(arguments)
                elif name == "jira_get_projects":
                    return await self._get_projects()
                else:
                    return [TextContent(type="text", text=f"Unknown tool: {name}")]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {str(e)}")]
    
    def _connect_to_jira(self):
        """Initialize Jira client connection"""
        config = JiraConfig(
            url=os.getenv("JIRA_URL", ""),
            username=os.getenv("JIRA_USERNAME", ""),
            api_token=os.getenv("JIRA_API_TOKEN", ""),
            cloud=os.getenv("JIRA_CLOUD", "true").lower() == "true"
        )
        
        if not all([config.url, config.username, config.api_token]):
            raise ValueError("JIRA_URL, JIRA_USERNAME, and JIRA_API_TOKEN must be set")
        
        self.jira_client = Jira(
            url=config.url,
            username=config.username,
            password=config.api_token,
            cloud=config.cloud
        )
    
    async def _search_issues(self, arguments: dict) -> List[TextContent]:
        """Search for Jira issues"""
        jql = arguments["jql"]
        max_results = arguments.get("max_results", 50)
        
        results = self.jira_client.jql(jql, limit=max_results)
        issues = results.get("issues", [])
        
        formatted_issues = []
        for issue in issues:
            fields = issue.get("fields", {})
            formatted_issues.append({
                "key": issue["key"],
                "summary": fields.get("summary", ""),
                "status": fields.get("status", {}).get("name", ""),
                "assignee": fields.get("assignee", {}).get("displayName", "Unassigned") if fields.get("assignee") else "Unassigned",
                "priority": fields.get("priority", {}).get("name", "") if fields.get("priority") else "",
                "created": fields.get("created", ""),
                "updated": fields.get("updated", "")
            })
        
        return [TextContent(
            type="text",
            text=json.dumps(formatted_issues, indent=2)
        )]
    
    async def _get_issue(self, arguments: dict) -> List[TextContent]:
        """Get details of a specific issue"""
        issue_key = arguments["issue_key"]
        
        issue = self.jira_client.issue(issue_key)
        fields = issue.get("fields", {})
        
        issue_details = JiraIssue(
            key=issue["key"],
            summary=fields.get("summary", ""),
            description=fields.get("description", ""),
            status=fields.get("status", {}).get("name", ""),
            assignee=fields.get("assignee", {}).get("displayName", "") if fields.get("assignee") else None,
            reporter=fields.get("reporter", {}).get("displayName", ""),
            created=fields.get("created", ""),
            updated=fields.get("updated", ""),
            priority=fields.get("priority", {}).get("name", "") if fields.get("priority") else None,
            issue_type=fields.get("issuetype", {}).get("name", ""),
            project=fields.get("project", {}).get("key", "")
        )
        
        return [TextContent(
            type="text",
            text=issue_details.model_dump_json(indent=2)
        )]
    
    async def _create_issue(self, arguments: dict) -> List[TextContent]:
        """Create a new Jira issue"""
        fields = {
            "project": {"key": arguments["project_key"]},
            "summary": arguments["summary"],
            "issuetype": {"name": arguments.get("issue_type", "Task")}
        }
        
        if "description" in arguments:
            fields["description"] = arguments["description"]
        
        if "priority" in arguments:
            fields["priority"] = {"name": arguments["priority"]}
        
        if "assignee" in arguments:
            fields["assignee"] = {"name": arguments["assignee"]}
        
        result = self.jira_client.create_issue(fields=fields)
        
        return [TextContent(
            type="text",
            text=f"Created issue: {result['key']}\nURL: {result['self']}"
        )]
    
    async def _update_issue(self, arguments: dict) -> List[TextContent]:
        """Update an existing issue"""
        issue_key = arguments["issue_key"]
        fields = arguments["fields"]
        
        update_fields = {}
        if "summary" in fields:
            update_fields["summary"] = fields["summary"]
        if "description" in fields:
            update_fields["description"] = fields["description"]
        if "priority" in fields:
            update_fields["priority"] = {"name": fields["priority"]}
        if "assignee" in fields:
            update_fields["assignee"] = {"name": fields["assignee"]}
        
        self.jira_client.update_issue_field(issue_key, update_fields)
        
        return [TextContent(
            type="text",
            text=f"Updated issue: {issue_key}"
        )]
    
    async def _add_comment(self, arguments: dict) -> List[TextContent]:
        """Add a comment to an issue"""
        issue_key = arguments["issue_key"]
        comment = arguments["comment"]
        
        self.jira_client.issue_add_comment(issue_key, comment)
        
        return [TextContent(
            type="text",
            text=f"Added comment to issue: {issue_key}"
        )]
    
    async def _transition_issue(self, arguments: dict) -> List[TextContent]:
        """Transition an issue to a different status"""
        issue_key = arguments["issue_key"]
        target_status = arguments["status"]
        
        # Get available transitions
        transitions = self.jira_client.get_issue_transitions(issue_key)
        
        # Find the transition that matches the target status
        transition_id = None
        for transition in transitions["transitions"]:
            if transition["to"]["name"].lower() == target_status.lower():
                transition_id = transition["id"]
                break
        
        if not transition_id:
            available_statuses = [t["to"]["name"] for t in transitions["transitions"]]
            return [TextContent(
                type="text",
                text=f"Cannot transition to '{target_status}'. Available statuses: {', '.join(available_statuses)}"
            )]
        
        self.jira_client.set_issue_status(issue_key, transition_id)
        
        return [TextContent(
            type="text",
            text=f"Transitioned issue {issue_key} to status: {target_status}"
        )]
    
    async def _get_projects(self) -> List[TextContent]:
        """Get list of projects"""
        projects = self.jira_client.projects()
        
        project_list = []
        for project in projects:
            project_list.append({
                "key": project["key"],
                "name": project["name"],
                "id": project["id"]
            })
        
        return [TextContent(
            type="text",
            text=json.dumps(project_list, indent=2)
        )]
    
    async def run(self):
        """Run the MCP server"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream=read_stream,
                write_stream=write_stream,
                init_options={}
            )


def main():
    server = JiraMCPServer()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()