# File: mcp_server/mcp_server.py

import os
import argparse
import asyncio
import dotenv

# Import MCP server utilities
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.types as types
import mcp.server.stdio

# Import your service implementation
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
            # Tool: create-doc remains unchanged.
            types.Tool(
                name="create-doc",
                description="Creates a new Google Doc with an optional title",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "title": {
                            "type": "string",
                            "description": "Title of the new document",
                            "default": "New Document",
                            "example": "My New Document"
                        }
                    },
                    "required": []
                }
            ),
            # New tool: insert-text
            types.Tool(
                name="insert-text",
                description="Inserts text into a Google Doc at a specified index",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "document_id": {
                            "type": "string",
                            "description": "The ID of the Google Document",
                            "example": "1abcXYZ..."
                        },
                        "index": {
                            "type": "number",
                            "description": "The insertion index (1-based)",
                            "example": 1
                        },
                        "text": {
                            "type": "string",
                            "description": "The text to insert",
                            "example": "Hello World\n"
                        }
                    },
                    "required": ["document_id", "index", "text"]
                }
            ),
            # New tool: replace-text
            types.Tool(
                name="replace-text",
                description="Replaces all occurrences of a search string with a replacement string in a Google Doc",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "document_id": {
                            "type": "string",
                            "description": "The ID of the Google Document",
                            "example": "1abcXYZ..."
                        },
                        "search_text": {
                            "type": "string",
                            "description": "The text to search for",
                            "example": "FOO"
                        },
                        "replace_text": {
                            "type": "string",
                            "description": "The text to replace with",
                            "example": "BAR"
                        },
                        "match_case": {
                            "type": "boolean",
                            "description": "Whether the search should be case sensitive",
                            "default": False,
                            "example": False
                        }
                    },
                    "required": ["document_id", "search_text", "replace_text"]
                }
            ),
            # New tool: delete-content
            types.Tool(
                name="delete-content",
                description="Deletes the content in a specified range in a Google Doc",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "document_id": {
                            "type": "string",
                            "description": "The ID of the Google Document",
                            "example": "1abcXYZ..."
                        },
                        "start_index": {
                            "type": "number",
                            "description": "The starting index of the content range (inclusive)",
                            "example": 10
                        },
                        "end_index": {
                            "type": "number",
                            "description": "The ending index of the content range (exclusive)",
                            "example": 20
                        }
                    },
                    "required": ["document_id", "start_index", "end_index"]
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
                description="Creates a new anchored comment on a Google Doc. "
                            "You must specify the document ID, comment content, "
                            "starting offset, and length. Optionally, provide the total "
                            "number of characters (ml) in the target region.",
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
                        },
                        "start_offset": {
                            "type": "number",
                            "description": "Starting offset in the document text",
                            "example": 10
                        },
                        "length": {
                            "type": "number",
                            "description": "Length of the text range for the anchor",
                            "example": 5
                        },
                        "total_length": {
                            "type": "number",
                            "description": "Total characters in the target region (ml)",
                            "default": 5,
                            "example": 5
                        }
                    },
                    "required": ["document_id", "content", "start_offset", "length"]
                }
            ),
        ]

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
        if name == "create-doc":
            title = arguments.get("title", "New Document")
            doc = await docs_service.create_document(title)
            return [types.TextContent(
                type="text",
                text=f"Document created at URL: https://docs.google.com/document/d/{doc.get('documentId')}/edit"
            )]
        elif name == "insert-text":
            document_id = arguments["document_id"]
            index = arguments["index"]
            text_to_insert = arguments["text"]
            # Build an insertText request.
            request = [{"insertText": {"location": {"index": index}, "text": text_to_insert}}]
            result = await docs_service.edit_document(document_id, request)
            return [types.TextContent(type="text", text=f"Inserted text into document {document_id}.")]
        elif name == "replace-text":
            document_id = arguments["document_id"]
            search_text = arguments["search_text"]
            replace_text = arguments["replace_text"]
            match_case = arguments.get("match_case", False)
            request = [{
                "replaceAllText": {
                    "containsText": {"text": search_text, "matchCase": match_case},
                    "replaceText": replace_text
                }
            }]
            result = await docs_service.edit_document(document_id, request)
            return [types.TextContent(type="text", text=f"Replaced text in document {document_id}: {result}")]
        elif name == "delete-content":
            document_id = arguments["document_id"]
            start_index = arguments["start_index"]
            end_index = arguments["end_index"]
            request = [{
                "deleteContentRange": {
                    "range": {"startIndex": start_index, "endIndex": end_index}
                }
            }]
            result = await docs_service.edit_document(document_id, request)
            return [types.TextContent(type="text", text=f"Deleted content from document {document_id}: {result}")]
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
            start_offset = arguments["start_offset"]
            length = arguments["length"]
            total_length = arguments.get("total_length", length)
            # Retrieve the document to get the current revision id.
            doc = await docs_service.read_document(document_id)
            revision_id = doc.get("revisionId")
            if not revision_id:
                raise ValueError("Document revision ID not found.")
            anchor_value = (
                f"{{'r': '{revision_id}', 'a': [{{'txt': {{'o': {start_offset}, 'l': {length}, 'ml': {total_length}}}}}]}}"
            )
            def _create_comment():
                body = {
                    "content": content,
                    "anchor": anchor_value
                }
                return docs_service.drive_service.comments().create(
                    fileId=document_id,
                    body=body,
                    fields="id,content,author,createdTime,modifiedTime"
                ).execute()
            comment = await asyncio.to_thread(_create_comment)
            return [types.TextContent(type="text", text=f"Comment created: {comment}")]
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
    Entry point for the MCP server. This function parses command-line arguments
    (or falls back to environment variables) for the credentials and token file paths,
    then calls the async run_main() function.
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
