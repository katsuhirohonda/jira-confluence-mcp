#!/usr/bin/env python3
import os
import asyncio
from typing import List, Dict, Any, Optional
import json

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent, Resource, ServerCapabilities
from pydantic import Field, BaseModel
from atlassian import Confluence
from dotenv import load_dotenv

load_dotenv()


class ConfluenceConfig(BaseModel):
    """Configuration for Confluence connection"""
    url: str = Field(description="Confluence instance URL")
    username: str = Field(description="Confluence username/email")
    api_token: str = Field(description="Confluence API token")
    cloud: bool = Field(default=True, description="Whether this is a cloud instance")


class ConfluencePage(BaseModel):
    """Confluence page model"""
    id: str
    title: str
    space_key: str
    space_name: str
    version: int
    created_by: str
    created_date: str
    last_updated: str
    parent_id: Optional[str] = None
    url: str


class ConfluenceMCPServer:
    def __init__(self):
        self.server = Server("confluence-mcp")
        self.confluence_client: Optional[Confluence] = None
        self._setup_handlers()
        
    def _setup_handlers(self):
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            return [
                Tool(
                    name="confluence_search_content",
                    description="Search for Confluence content using CQL",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "cql": {
                                "type": "string",
                                "description": "CQL query string"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results to return",
                                "default": 25
                            }
                        },
                        "required": ["cql"]
                    }
                ),
                Tool(
                    name="confluence_get_page",
                    description="Get a Confluence page by ID",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "page_id": {
                                "type": "string",
                                "description": "Page ID"
                            },
                            "expand": {
                                "type": "string",
                                "description": "Properties to expand (e.g., body.storage,version)",
                                "default": "body.storage,version"
                            }
                        },
                        "required": ["page_id"]
                    }
                ),
                Tool(
                    name="confluence_create_page",
                    description="Create a new Confluence page",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "space_key": {
                                "type": "string",
                                "description": "Space key where the page will be created"
                            },
                            "title": {
                                "type": "string",
                                "description": "Page title"
                            },
                            "content": {
                                "type": "string",
                                "description": "Page content in storage format (HTML)"
                            },
                            "parent_id": {
                                "type": "string",
                                "description": "Parent page ID (optional)"
                            }
                        },
                        "required": ["space_key", "title", "content"]
                    }
                ),
                Tool(
                    name="confluence_update_page",
                    description="Update an existing Confluence page",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "page_id": {
                                "type": "string",
                                "description": "Page ID"
                            },
                            "title": {
                                "type": "string",
                                "description": "New page title"
                            },
                            "content": {
                                "type": "string",
                                "description": "New page content in storage format (HTML)"
                            },
                            "version_comment": {
                                "type": "string",
                                "description": "Comment for this version"
                            }
                        },
                        "required": ["page_id", "content"]
                    }
                ),
                Tool(
                    name="confluence_delete_page",
                    description="Delete a Confluence page",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "page_id": {
                                "type": "string",
                                "description": "Page ID to delete"
                            }
                        },
                        "required": ["page_id"]
                    }
                ),
                Tool(
                    name="confluence_get_spaces",
                    description="Get list of Confluence spaces",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of spaces to return",
                                "default": 25
                            }
                        }
                    }
                ),
                Tool(
                    name="confluence_get_page_children",
                    description="Get child pages of a specific page",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "page_id": {
                                "type": "string",
                                "description": "Parent page ID"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of children to return",
                                "default": 25
                            }
                        },
                        "required": ["page_id"]
                    }
                ),
                Tool(
                    name="confluence_add_attachment",
                    description="Add an attachment to a Confluence page",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "page_id": {
                                "type": "string",
                                "description": "Page ID"
                            },
                            "file_path": {
                                "type": "string",
                                "description": "Path to the file to attach"
                            },
                            "comment": {
                                "type": "string",
                                "description": "Comment for the attachment"
                            }
                        },
                        "required": ["page_id", "file_path"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> List[TextContent]:
            if not self.confluence_client:
                self._connect_to_confluence()
            
            try:
                if name == "confluence_search_content":
                    return await self._search_content(arguments)
                elif name == "confluence_get_page":
                    return await self._get_page(arguments)
                elif name == "confluence_create_page":
                    return await self._create_page(arguments)
                elif name == "confluence_update_page":
                    return await self._update_page(arguments)
                elif name == "confluence_delete_page":
                    return await self._delete_page(arguments)
                elif name == "confluence_get_spaces":
                    return await self._get_spaces(arguments)
                elif name == "confluence_get_page_children":
                    return await self._get_page_children(arguments)
                elif name == "confluence_add_attachment":
                    return await self._add_attachment(arguments)
                else:
                    return [TextContent(type="text", text=f"Unknown tool: {name}")]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {str(e)}")]
    
    def _connect_to_confluence(self):
        """Initialize Confluence client connection"""
        config = ConfluenceConfig(
            url=os.getenv("CONFLUENCE_URL", ""),
            username=os.getenv("CONFLUENCE_USERNAME", ""),
            api_token=os.getenv("CONFLUENCE_API_TOKEN", ""),
            cloud=os.getenv("CONFLUENCE_CLOUD", "true").lower() == "true"
        )
        
        if not all([config.url, config.username, config.api_token]):
            raise ValueError("CONFLUENCE_URL, CONFLUENCE_USERNAME, and CONFLUENCE_API_TOKEN must be set")
        
        self.confluence_client = Confluence(
            url=config.url,
            username=config.username,
            password=config.api_token,
            cloud=config.cloud
        )
    
    async def _search_content(self, arguments: dict) -> List[TextContent]:
        """Search for Confluence content"""
        cql = arguments["cql"]
        limit = arguments.get("limit", 25)
        
        results = self.confluence_client.cql(cql, limit=limit)
        
        formatted_results = []
        for result in results.get("results", []):
            formatted_results.append({
                "id": result["content"]["id"],
                "title": result["content"]["title"],
                "type": result["content"]["type"],
                "space": result["content"]["space"]["key"],
                "url": f"{self.confluence_client.url}{result['content']['_links']['webui']}"
            })
        
        return [TextContent(
            type="text",
            text=json.dumps(formatted_results, indent=2)
        )]
    
    async def _get_page(self, arguments: dict) -> List[TextContent]:
        """Get a specific page"""
        page_id = arguments["page_id"]
        expand = arguments.get("expand", "body.storage,version")
        
        page = self.confluence_client.get_page_by_id(page_id, expand=expand)
        
        page_info = {
            "id": page["id"],
            "title": page["title"],
            "space": page["space"]["key"],
            "version": page["version"]["number"],
            "created_by": page["version"]["by"]["displayName"],
            "created_date": page["version"]["when"],
            "url": f"{self.confluence_client.url}{page['_links']['webui']}"
        }
        
        if "body" in page and "storage" in page["body"]:
            page_info["content"] = page["body"]["storage"]["value"]
        
        return [TextContent(
            type="text",
            text=json.dumps(page_info, indent=2)
        )]
    
    async def _create_page(self, arguments: dict) -> List[TextContent]:
        """Create a new page"""
        space_key = arguments["space_key"]
        title = arguments["title"]
        content = arguments["content"]
        parent_id = arguments.get("parent_id")
        
        result = self.confluence_client.create_page(
            space=space_key,
            title=title,
            body=content,
            parent_id=parent_id
        )
        
        return [TextContent(
            type="text",
            text=f"Created page: {result['title']}\nID: {result['id']}\nURL: {self.confluence_client.url}{result['_links']['webui']}"
        )]
    
    async def _update_page(self, arguments: dict) -> List[TextContent]:
        """Update an existing page"""
        page_id = arguments["page_id"]
        content = arguments["content"]
        title = arguments.get("title")
        version_comment = arguments.get("version_comment", "Updated via MCP")
        
        # Get current page info
        current_page = self.confluence_client.get_page_by_id(page_id)
        
        result = self.confluence_client.update_page(
            page_id=page_id,
            title=title or current_page["title"],
            body=content,
            version_comment=version_comment
        )
        
        return [TextContent(
            type="text",
            text=f"Updated page: {result['title']}\nVersion: {result['version']['number']}"
        )]
    
    async def _delete_page(self, arguments: dict) -> List[TextContent]:
        """Delete a page"""
        page_id = arguments["page_id"]
        
        self.confluence_client.remove_page(page_id)
        
        return [TextContent(
            type="text",
            text=f"Deleted page with ID: {page_id}"
        )]
    
    async def _get_spaces(self, arguments: dict) -> List[TextContent]:
        """Get list of spaces"""
        limit = arguments.get("limit", 25)
        
        spaces = self.confluence_client.get_all_spaces(limit=limit)
        
        space_list = []
        for space in spaces["results"]:
            space_list.append({
                "key": space["key"],
                "name": space["name"],
                "id": space["id"],
                "type": space["type"]
            })
        
        return [TextContent(
            type="text",
            text=json.dumps(space_list, indent=2)
        )]
    
    async def _get_page_children(self, arguments: dict) -> List[TextContent]:
        """Get child pages"""
        page_id = arguments["page_id"]
        limit = arguments.get("limit", 25)
        
        children = self.confluence_client.get_page_child_by_type(
            page_id, type="page", limit=limit
        )
        
        child_list = []
        for child in children:
            child_list.append({
                "id": child["id"],
                "title": child["title"],
                "url": f"{self.confluence_client.url}{child['_links']['webui']}"
            })
        
        return [TextContent(
            type="text",
            text=json.dumps(child_list, indent=2)
        )]
    
    async def _add_attachment(self, arguments: dict) -> List[TextContent]:
        """Add attachment to a page"""
        page_id = arguments["page_id"]
        file_path = arguments["file_path"]
        comment = arguments.get("comment", "")
        
        if not os.path.exists(file_path):
            return [TextContent(
                type="text",
                text=f"Error: File not found: {file_path}"
            )]
        
        result = self.confluence_client.attach_file(
            file_path,
            page_id=page_id,
            comment=comment
        )
        
        return [TextContent(
            type="text",
            text=f"Attached file: {os.path.basename(file_path)} to page {page_id}"
        )]
    
    async def run(self):
        """Run the MCP server"""
        async with stdio_server() as (read_stream, write_stream):
            init_options = InitializationOptions(
                server_name="confluence-mcp",
                server_version="1.0.0",
                capabilities=ServerCapabilities(
                    tools={}
                )
            )
            await self.server.run(
                read_stream=read_stream,
                write_stream=write_stream,
                initialization_options=init_options
            )


def main():
    server = ConfluenceMCPServer()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()