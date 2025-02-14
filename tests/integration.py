import os
import asyncio
import pytest
import time
import dotenv
from googleapiclient.errors import HttpError
import pytest_asyncio

dotenv.load_dotenv()

from mcp_server.google_docs_service import GoogleDocsService

# Async fixtures via pytest_asyncio.
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
async def test_insert_text(temp_document, docs_service):
    document_id = temp_document
    # Use the insert-text tool logic.
    insert_request = [{"insertText": {"location": {"index": 1}, "text": "Hello Insert Test\n"}}]
    result = await docs_service.edit_document(document_id, insert_request)
    # Check that the response contains expected keys.
    assert "documentId" in result, "Response should contain 'documentId'"
    text = await docs_service.read_document_text(document_id)
    assert "Hello Insert Test" in text, "Inserted text should appear in the document."

@pytest.mark.asyncio
async def test_replace_text(temp_document, docs_service):
    document_id = temp_document
    # First, insert text that we can replace.
    await docs_service.edit_document(document_id, [{"insertText": {"location": {"index": 1}, "text": "FOO FOO\n"}}])
    # Use the replace-text tool logic.
    replace_request = [{
        "replaceAllText": {
            "containsText": {"text": "FOO", "matchCase": True},
            "replaceText": "BAR"
        }
    }]
    result = await docs_service.edit_document(document_id, replace_request)
    assert "documentId" in result, "Response should contain 'documentId'"
    text = await docs_service.read_document_text(document_id)
    assert "BAR BAR" in text, "Text should be replaced with BAR."

@pytest.mark.asyncio
async def test_delete_content(temp_document, docs_service):
    document_id = temp_document
    # Insert some text to delete.
    await docs_service.edit_document(document_id, [{"insertText": {"location": {"index": 1}, "text": "DELETE_ME\n"}}])
    # Read the text to determine the deletion range.
    text_before = await docs_service.read_document_text(document_id)
    # For simplicity, assume the inserted text appears at a known location.
    # Here we delete from index 1 to index (1 + len("DELETE_ME\n"))
    start_index = 1
    end_index = start_index + len("DELETE_ME\n")
    delete_request = [{
        "deleteContentRange": {
            "range": {"startIndex": start_index, "endIndex": end_index}
        }
    }]
    result = await docs_service.edit_document(document_id, delete_request)
    assert "documentId" in result, "Response should contain 'documentId'"
    text_after = await docs_service.read_document_text(document_id)
    assert "DELETE_ME" not in text_after, "The deleted text should no longer be present."

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
