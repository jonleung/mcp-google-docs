from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.types as types
import mcp.server.stdio
import dotenv

from google_docs_service import GoogleDocsService

dotenv.load_dotenv()

async def main(creds_file_path: str, token_path: str):
    creds_file_path = os.path.abspath(creds_file_path)
    token_path = os.path.abspath(token_path)
    docs_service = GoogleDocsService(creds_file_path, token_path)
    server = Server("googledocs")

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name="create-doc",
                description="Creates a new Google Doc with an optional title",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Title of the new document", "default": "New Document"}
                    },
                    "required": []
                }
            ),
            types.Tool(
                name="edit-doc",
                description="Edits a Google Doc using batchUpdate requests",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "document_id": {"type": "string", "description": "ID of the document"},
                        "requests": {"type": "array", "description": "List of update requests"}
                    },
                    "required": ["document_id", "requests"]
                }
            ),
            types.Tool(
                name="read-comments",
                description="Reads comments from a Google Doc",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "document_id": {"type": "string", "description": "ID of the document"}
                    },
                    "required": ["document_id"]
                }
            ),
            types.Tool(
                name="reply-comment",
                description="Replies to a comment in a Google Doc",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "document_id": {"type": "string", "description": "ID of the document"},
                        "comment_id": {"type": "string", "description": "ID of the comment"},
                        "reply": {"type": "string", "description": "Content of the reply"}
                    },
                    "required": ["document_id", "comment_id", "reply"]
                }
            ),
            types.Tool(
                name="read-doc",
                description="Reads and returns the plain-text content of a Google Doc",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "document_id": {"type": "string", "description": "ID of the document"}
                    },
                    "required": ["document_id"]
                }
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
        if name == "create-doc":
            title = arguments.get("title", "New Document")
            doc = await docs_service.create_document(title)
            return [types.TextContent(type="text", text=f"Document created at url: https://docs.google.com/document/d/{doc.get('documentId')}/edit")]
        elif name == "edit-doc":
            document_id = arguments["document_id"]
            requests_payload = arguments["requests"]
            result = await docs_service.edit_document(document_id, requests_payload)
            return [types.TextContent(type="text", text=f"Document updated: {result}")]
        elif name == "read-comments":
            document_id = arguments["document_id"]
            comments = await docs_service.read_comments(document_id)
            return [types.TextContent(type="text", text=str(comments))]
        elif name == "reply-comment":
            document_id = arguments["document_id"]
            comment_id = arguments["comment_id"]
            reply = arguments["reply"]
            result = await docs_service.reply_comment(document_id, comment_id, reply)
            return [types.TextContent(type="text", text=f"Reply posted: {result}")]
        elif name == "read-doc":
            document_id = arguments["document_id"]
            text = await docs_service.read_document_text(document_id)
            return [types.TextContent(type="text", text=text)]
        else:
            raise ValueError(f"Unknown tool: {name}")

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="googledocs",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(), experimental_capabilities={}
                ),
            ),
        )

if __name__ == "__main__":
    import os
    import argparse
    import asyncio

    print(os.getcwd())
    parser = argparse.ArgumentParser(description='Google Docs API MCP Server')

    # Use environment variables as defaults if available.
    parser.add_argument(
        '--creds-file-path',
        required=False,
        default=os.environ.get("GOOGLE_CREDS_FILE"),
        help='OAuth 2.0 credentials file path (or set GOOGLE_CREDS_FILE env variable)'
    )
    parser.add_argument(
        '--token-path',
        required=False,
        default=os.environ.get("GOOGLE_TOKEN_FILE"),
        help='File path to store/retrieve tokens (or set GOOGLE_TOKEN_FILE env variable)'
    )
    args = parser.parse_args()

    if not args.creds_file_path or not args.token_path:
        parser.error(
            "You must supply --creds-file-path and --token-path, or set GOOGLE_CREDS_FILE and GOOGLE_TOKEN_FILE environment variables."
        )

    asyncio.run(main(args.creds_file_path, args.token_path))
