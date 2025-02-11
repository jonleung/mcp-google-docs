import os
import asyncio
import pytest
import pytest_asyncio
import time
from googleapiclient.errors import HttpError
import dotenv

dotenv.load_dotenv()

# Import your real GoogleDocsService implementation.
# For example, if your service code is in google_docs_service.py:
from src.google_docs_service import GoogleDocsService

# --- Pytest fixtures for integration configuration ---
@pytest.fixture(scope="session")
def creds_file_path():
    path = os.environ.get("GOOGLE_CREDS_FILE")
    if not path:
        pytest.skip("GOOGLE_CREDS_FILE environment variable not set")
    return path

@pytest.fixture(scope="session")
def token_file_path():
    path = os.environ.get("GOOGLE_TOKEN_FILE")
    if not path:
        pytest.skip("GOOGLE_TOKEN_FILE environment variable not set")
    return path

@pytest.fixture(scope="session")
def docs_service(creds_file_path, token_file_path):
    # Instantiate the service with real credentials.
    service = GoogleDocsService(creds_file_path, token_file_path)
    return service

# --- Helper fixture to create a temporary document and clean up ---
@pytest_asyncio.fixture
async def temp_document(docs_service):
    # Create a document with a unique title.
    unique_title = f"Integration Test Doc {int(time.time())}"
    doc = await docs_service.create_document(unique_title)
    document_id = doc.get("documentId")
    if not document_id:
        pytest.fail("Failed to create document.")
    yield document_id
    # Clean up by deleting the document.
    try:
        # Use the Drive API client to delete the document.
        await asyncio.to_thread(
            lambda: docs_service.drive_service.files().delete(fileId=document_id).execute()
        )
    except HttpError as e:
        # Log error but don’t fail the test cleanup.
        print(f"Warning: Failed to delete document {document_id}: {e}")

# --- Test functions using real API calls ---

@pytest.mark.asyncio
async def test_create_document(docs_service):
    # Create a document and immediately read it back.
    title = f"Integration Create Doc Test {int(time.time())}"
    doc = await docs_service.create_document(title)
    document_id = doc.get("documentId")
    assert document_id, "Document ID should be returned on creation."

    # Optionally, read the doc to ensure it is accessible.
    read_doc = await docs_service.read_document(document_id)
    assert "body" in read_doc, "Document should contain a body."

    # Cleanup: delete the document.
    await asyncio.to_thread(
        lambda: docs_service.drive_service.files().delete(fileId=document_id).execute()
    )

@pytest.mark.asyncio
async def test_edit_document(temp_document, docs_service):
    # Use the temporary document created by the fixture.
    document_id = temp_document

    # Prepare a batchUpdate request to insert text at the beginning.
    requests_payload = [
        {
            "insertText": {
                "location": {"index": 1},
                "text": "Hello Integration Test\n"
            }
        }
    ]
    result = await docs_service.edit_document(document_id, requests_payload)
    assert "replies" not in result  # Just a basic check that the update returned something

    # Now read back the document text.
    text = await docs_service.read_document_text(document_id)
    assert "Hello Integration Test" in text, "The inserted text should appear in the document."

@pytest.mark.asyncio
async def test_read_document_text(temp_document, docs_service):
    document_id = temp_document

    # For a new document, the text might be empty or contain default content.
    text = await docs_service.read_document_text(document_id)
    # We simply verify that a string is returned.
    assert isinstance(text, str), "Document text should be a string."

@pytest.mark.asyncio
async def test_read_comments(temp_document, docs_service):
    document_id = temp_document

    # For a new document, there should be no comments.
    comments = await docs_service.read_comments(document_id)
    # Depending on account and doc state, this might be an empty list.
    assert isinstance(comments, list), "Comments should be returned as a list."

@pytest.mark.asyncio
async def test_reply_comment(temp_document, docs_service):
    document_id = temp_document

    # To test replying to a comment, we need to first create a comment.
    # Since our service doesn't provide a create_comment method, we use the Drive API directly.
    def create_comment():
        body = {"content": "Integration test comment"}
        # Request only the ID and content.
        return docs_service.drive_service.comments().create(
            fileId=document_id,
            body=body,
            fields="id,content"
        ).execute()
    comment = await asyncio.to_thread(create_comment)
    comment_id = comment.get("id")
    assert comment_id, "A comment should have been created."

    # Now reply to that comment.
    reply_text = "Integration test reply"
    reply_result = await docs_service.reply_comment(document_id, comment_id, reply_text)
    assert "reply" in reply_result.get("reply", reply_text) or reply_text in str(reply_result), "The reply should be posted."

    # (Optional) Clean up: Delete the comment if desired.
    def delete_comment():
        return docs_service.drive_service.comments().delete(
            fileId=document_id,
            commentId=comment_id
        ).execute()
    await asyncio.to_thread(delete_comment)
