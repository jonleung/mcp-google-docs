import os
import re
import asyncio
import time
import pytest
import dotenv
from googleapiclient.errors import HttpError
import pytest_asyncio

dotenv.load_dotenv()

from mcp_server.google_docs_service import GoogleDocsService

# Helper function to normalize text by collapsing multiple newlines.
def normalize_text(text: str) -> str:
    return re.sub(r'\n+', '\n', text).strip()

# Async fixtures for credentials and token file paths.
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

# Fixture to create a temporary document and clean it up afterward.
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

# Test: Create a new document.
@pytest.mark.asyncio
async def test_create_document(docs_service):
    title = f"Integration Create Doc Test {int(time.time())}"
    doc = await docs_service.create_document(title)
    document_id = doc.get("documentId")
    assert document_id, "Document ID should be returned on creation."
    read_doc = await docs_service.read_document(document_id)
    assert "body" in read_doc, "Document should contain a body."
    # Clean up.
    await asyncio.to_thread(
        lambda: docs_service.drive_service.files().delete(fileId=document_id).execute()
    )

# Test: Create a document and share with datastax.com
@pytest.mark.asyncio
async def test_create_document_with_org(docs_service):
    title = f"Integration Create Doc with Org Test {int(time.time())}"
    org = "datastax.com"
    # Create the document with org share enabled.
    doc = await docs_service.create_document(title, org, "writer")
    document_id = doc.get("documentId")
    assert document_id, "Document ID should be returned on creation with org sharing."
    # Give the permission a moment to propagate.
    await asyncio.sleep(1)
    # Retrieve the document's permissions.
    permissions = await asyncio.to_thread(
        lambda: docs_service.drive_service.permissions().list(
            fileId=document_id,
            fields="permissions(id, domain, role, type)"
        ).execute()
    )
    # Look for a domain-level permission for datastax.com.
    domain_perms = [
        perm for perm in permissions.get("permissions", [])
        if perm.get("type") == "domain" and perm.get("domain") == org
    ]
    assert domain_perms, f"Document should have domain permission for {org}."
    # Clean up.
    await asyncio.to_thread(
        lambda: docs_service.drive_service.files().delete(fileId=document_id).execute()
    )

# Test: Rewrite the document content.
@pytest.mark.asyncio
async def test_rewrite_document(temp_document, docs_service):
    document_id = temp_document
    final_text = (
        "This is the new final content of the document.\n"
        "It has multiple lines.\n"
        "End of content."
    )
    # Rewrite the document with the final text.
    result = await docs_service.rewrite_document(document_id, final_text)

    # Read back the document text.
    updated_text = await docs_service.read_document_text(document_id)

    # Normalize both expected and actual text to collapse extra newlines.
    normalized_expected = normalize_text(final_text)
    normalized_actual = normalize_text(updated_text)

    assert normalized_expected == normalized_actual, (
        f"Expected: {normalized_expected}, but got: {normalized_actual}"
    )

# Test: Read document text.
@pytest.mark.asyncio
async def test_read_document_text(temp_document, docs_service):
    document_id = temp_document
    text = await docs_service.read_document_text(document_id)
    assert isinstance(text, str), "Document text should be a string"

# Test: Read comments (even if none exist, should return a list).
@pytest.mark.asyncio
async def test_read_comments(temp_document, docs_service):
    document_id = temp_document
    comments = await docs_service.read_comments(document_id)
    assert isinstance(comments, list), "Comments should be returned as a list"

# Test: Reply to a comment.
@pytest.mark.asyncio
async def test_reply_comment(temp_document, docs_service):
    document_id = temp_document
    # Create a comment.
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

    # Post a reply.
    reply_text = "Integration test reply"
    reply_result = await docs_service.reply_comment(document_id, comment_id, reply_text)
    assert reply_text in reply_result.get("content", ""), "The reply should be posted."

    # Clean up: Delete the comment.
    def delete_comment():
        return docs_service.drive_service.comments().delete(
            fileId=document_id,
            commentId=comment_id
        ).execute()
    await asyncio.to_thread(delete_comment)

# Test: Create a comment.
@pytest.mark.asyncio
async def test_create_comment(temp_document, docs_service):
    document_id = temp_document
    content = "Test create comment"
    comment = await docs_service.create_comment(document_id, content)
    assert "id" in comment, "Created comment should have an ID."

    # Clean up: Delete the comment.
    def delete_comment():
        return docs_service.drive_service.comments().delete(
            fileId=document_id,
            commentId=comment.get("id")
        ).execute()
    await asyncio.to_thread(delete_comment)

# Test: Delete a reply.
@pytest.mark.asyncio
async def test_delete_reply(temp_document, docs_service):
    document_id = temp_document

    # Create a comment.
    def create_comment():
        body = {"content": "Test comment for delete reply"}
        return docs_service.drive_service.comments().create(
            fileId=document_id,
            body=body,
            fields="id,content,replies"
        ).execute()
    comment = await asyncio.to_thread(create_comment)
    comment_id = comment.get("id")
    assert comment_id, "A comment should have been created for delete reply test."

    # Create a reply for the comment.
    reply_text = "Test reply to be deleted"
    reply = await docs_service.reply_comment(document_id, comment_id, reply_text)
    reply_id = reply.get("id")
    assert reply_id, "A reply should have been created for delete reply test."

    # Delete the reply using the new delete_reply method.
    await docs_service.delete_reply(document_id, comment_id, reply_id)

    # Verify the reply was deleted.
    comments = await docs_service.read_comments(document_id)
    for c in comments:
        if c.get("id") == comment_id:
            replies = c.get("replies", [])
            assert all(r.get("id") != reply_id for r in replies), "The reply should have been deleted."

    # Clean up: Delete the comment.
    def delete_comment():
        return docs_service.drive_service.comments().delete(
            fileId=document_id,
            commentId=comment_id
        ).execute()
    await asyncio.to_thread(delete_comment)
