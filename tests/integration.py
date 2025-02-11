import os
import asyncio
import pytest
import time
import dotenv
from googleapiclient.errors import HttpError
import pytest_asyncio

dotenv.load_dotenv()

from mcp_server.google_docs_service import GoogleDocsService

# Use pytest_asyncio.fixture to ensure async fixtures are properly awaited.
@pytest_asyncio.fixture(scope="session")
def creds_file_path():
    path = os.environ.get("GOOGLE_CREDS_FILE")
    if not path:
        pytest.skip("GOOGLE_CREDS_FILE environment variable not set")
    return path

@pytest_asyncio.fixture(scope="session")
def token_file_path():
    path = os.environ.get("GOOGLE_TOKEN_FILE")
    if not path:
        pytest.skip("GOOGLE_TOKEN_FILE environment variable not set")
    return path

@pytest_asyncio.fixture(scope="session")
def docs_service(creds_file_path, token_file_path):
    # Instantiate the service with real credentials.
    service = GoogleDocsService(creds_file_path, token_file_path)
    return service

# Helper fixture to create a temporary document and clean it up.
@pytest_asyncio.fixture
async def temp_document(docs_service):
    unique_title = f"Integration Test Doc {int(time.time())}"
    doc = await docs_service.create_document(unique_title)
    document_id = doc.get("documentId")
    if not document_id:
        pytest.fail("Failed to create document.")
    yield document_id
    # Cleanup: delete the document.
    try:
        await asyncio.to_thread(
            lambda: docs_service.drive_service.files().delete(fileId=document_id).execute()
        )
    except HttpError as e:
        print(f"Warning: Failed to delete document {document_id}: {e}")

@pytest.mark.asyncio
async def test_create_document(docs_service):
    title = f"Integration Create Doc Test {int(time.time())}"
    doc = await docs_service.create_document(title)
    document_id = doc.get("documentId")
    assert document_id, "Document ID should be returned on creation."
    read_doc = await docs_service.read_document(document_id)
    assert "body" in read_doc, "Document should contain a body."
    await asyncio.to_thread(
        lambda: docs_service.drive_service.files().delete(fileId=document_id).execute()
    )

@pytest.mark.asyncio
async def test_edit_document(temp_document, docs_service):
    document_id = temp_document
    requests_payload = [
        {
            "insertText": {
                "location": {"index": 1},
                "text": "Hello Integration Test\n"
            }
        }
    ]
    result = await docs_service.edit_document(document_id, requests_payload)
    # Instead of asserting that "replies" is absent, check for expected keys.
    assert "documentId" in result, "Response should contain 'documentId'"
    assert "writeControl" in result, "Response should contain 'writeControl'"
    text = await docs_service.read_document_text(document_id)
    assert "Hello Integration Test" in text, "The inserted text should appear in the document."

@pytest.mark.asyncio
async def test_read_document_text(temp_document, docs_service):
    document_id = temp_document
    text = await docs_service.read_document_text(document_id)
    assert isinstance(text, str), "Document text should be a string"

@pytest.mark.asyncio
async def test_read_comments(temp_document, docs_service):
    document_id = temp_document
    comments = await docs_service.read_comments(document_id)
    assert isinstance(comments, list), "Comments should be returned as a list"

@pytest.mark.asyncio
async def test_reply_comment(temp_document, docs_service):
    document_id = temp_document
    def create_comment():
        body = {"content": "Integration test comment"}
        return docs_service.drive_service.comments().create(
            fileId=document_id,
            body=body,
            fields="id,content"
        ).execute()
    comment = await asyncio.to_thread(create_comment)
    comment_id = comment.get("id")
    assert comment_id, "A comment should have been created."
    reply_text = "Integration test reply"
    reply_result = await docs_service.reply_comment(document_id, comment_id, reply_text)
    assert reply_text in reply_result.get("content", ""), "The reply should be posted."
    def delete_comment():
        return docs_service.drive_service.comments().delete(
            fileId=document_id,
            commentId=comment_id
        ).execute()
    await asyncio.to_thread(delete_comment)
