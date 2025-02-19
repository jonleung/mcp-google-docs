import os
import argparse
import asyncio
import dotenv

# Import MCP server utilities.
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.types as types
import mcp.server.stdio

# Import our updated GoogleDocsService.
from mcp_server.google_docs_service import GoogleDocsService

dotenv.load_dotenv()

async def run_main(creds_file_path: str, token_path: str):
    # Convert relative paths to absolute paths.
    creds_file_path = os.path.abspath(creds_file_path)
    token_path = os.path.abspath(token_path)

    # Instantiate the service.
    docs_service = GoogleDocsService(creds_file_path, token_path)
    server = Server("googledocs")

    @server.list_tools()
    async def handle_list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name="create-doc",
                description="Creates a new Google Doc with an optional title. Optionally, share with your organization by providing a domain and role.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Title of the new document",
                            "default": "New Document",
                            "example": "My New Document"
                        },
                        "org": {
                            "type": "string",
                            "description": "Organization domain to share the document with (e.g., 'example.com')",
                            "example": "example.com"
                        },
                        "role": {
                            "type": "string",
                            "description": "Permission role to assign (e.g., 'writer' or 'reader')",
                            "default": "writer",
                            "example": "writer"
                        }
                    },
                    "required": []
                }
            ),
            types.Tool(
                name="rewrite-document",
                description="Rewrites the entire content of a Google Doc with the provided final text",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "document_id": {
                            "type": "string",
                            "description": "The ID of the Google Document",
                            "example": "1abcXYZ..."
                        },
                        "final_text": {
                            "type": "string",
                            "description": "The final text to replace the document's content",
                            "example": "This is the new content of the document."
                        }
                    },
                    "required": ["document_id", "final_text"]
                }
            ),
            types.Tool(
                name="read-comments",
                description="Reads comments from a Google Doc",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "document_id": {
                            "type": "string",
                            "description": "ID of the document",
                            "example": "1abcXYZ..."
                        }
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
                        "document_id": {
                            "type": "string",
                            "description": "ID of the document",
                            "example": "1abcXYZ..."
                        },
                        "comment_id": {
                            "type": "string",
                            "description": "ID of the comment",
                            "example": "Cp1..."
                        },
                        "reply": {
                            "type": "string",
                            "description": "Content of the reply",
                            "example": "Thanks for the feedback!"
                        }
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
                        "document_id": {
                            "type": "string",
                            "description": "ID of the document",
                            "example": "1abcXYZ..."
                        }
                    },
                    "required": ["document_id"]
                }
            ),
            types.Tool(
                name="create-comment",
                description="Creates a new anchored comment on a Google Doc.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "document_id": {
                            "type": "string",
                            "description": "ID of the document",
                            "example": "1abcXYZ..."
                        },
                        "content": {
                            "type": "string",
                            "description": "The text content of the comment",
                            "example": "This is an anchored comment."
                        }
                    },
                    "required": ["document_id", "content"]
                }
            ),
            types.Tool(
                name="delete-reply",
                description="Deletes a reply from a comment in a Google Doc",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "document_id": {
                            "type": "string",
                            "description": "The ID of the Google Document",
                            "example": "1abcXYZ..."
                        },
                        "comment_id": {
                            "type": "string",
                            "description": "The ID of the comment containing the reply",
                            "example": "Cp1..."
                        },
                        "reply_id": {
                            "type": "string",
                            "description": "The ID of the reply to delete",
                            "example": "reply123"
                        }
                    },
                    "required": ["document_id", "comment_id", "reply_id"]
                }
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
        if name == "create-doc":
            title = arguments.get("title", "New Document")
            # Retrieve optional parameters for org and role.
            org = arguments.get("org")
            role = arguments.get("role", "writer")
            doc = await docs_service.create_document(title, org, role)
            return [types.TextContent(
                type="text",
                text=f"Document created at URL: https://docs.google.com/document/d/{doc.get('documentId')}/edit"
            )]
        elif name == "rewrite-document":
            document_id = arguments["document_id"]
            final_text = arguments["final_text"]
            result = await docs_service.rewrite_document(document_id, final_text)
            return [types.TextContent(
                type="text",
                text=f"Document {document_id} rewritten with new content. Result: {result}"
            )]
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
        elif name == "create-comment":
            document_id = arguments["document_id"]
            content = arguments["content"]
            comment = await docs_service.create_comment(document_id, content)
            return [types.TextContent(type="text", text=f"Comment created: {comment}")]
        elif name == "delete-reply":
            document_id = arguments["document_id"]
            comment_id = arguments["comment_id"]
            reply_id = arguments["reply_id"]
            await docs_service.delete_reply(document_id, comment_id, reply_id)
            return [types.TextContent(
                type="text",
                text=f"Deleted reply {reply_id} from comment {comment_id} in document {document_id}."
            )]
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
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                ),
            ),
        )

def main():
    """
    Entry point for the MCP server. Parses command-line arguments (or falls back to environment variables)
    for the credentials and token file paths, then calls the async run_main() function.
    """
    parser = argparse.ArgumentParser(description='Google Docs API MCP Server')
    parser.add_argument(
        '--creds-file-path', '--creds_file_path',
        required=False,
        default=os.environ.get("GOOGLE_CREDS_FILE"),
        dest="creds_file_path",
        help='OAuth 2.0 credentials file path (or set GOOGLE_CREDS_FILE env variable)'
    )
    parser.add_argument(
        '--token-path', '--token_path',
        required=False,
        default=os.environ.get("GOOGLE_TOKEN_FILE"),
        dest="token_path",
        help='File path to store/retrieve tokens (or set GOOGLE_TOKEN_FILE env variable)'
    )
    args = parser.parse_args()
    if not args.creds_file_path or not args.token_path:
        parser.error("You must supply --creds-file-path and --token-path, or set GOOGLE_CREDS_FILE and GOOGLE_TOKEN_FILE environment variables.")
    asyncio.run(run_main(args.creds_file_path, args.token_path))

if __name__ == "__main__":
    main()
