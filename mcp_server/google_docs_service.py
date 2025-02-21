import os
import asyncio
import logging
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GoogleDocsService:
    def __init__(self, creds_file_path: str, token_path: str, scopes: list[str] = None):
        # Default scopes include both Docs and Drive.
        if scopes is None:
            scopes = [
                'https://www.googleapis.com/auth/documents',
                'https://www.googleapis.com/auth/drive'
            ]
        self.creds = self._get_credentials(creds_file_path, token_path, scopes)
        # Initialize the Docs API client.
        self.docs_service = build('docs', 'v1', credentials=self.creds)
        # Initialize the Drive API client (for sharing, comments, etc).
        self.drive_service = build('drive', 'v3', credentials=self.creds)
        logger.info("Google Docs and Drive services initialized.")

    def _get_credentials(self, creds_file_path: str, token_path: str, scopes: list[str]) -> Credentials:
        creds = None
        if os.path.exists(token_path):
            logger.info('Loading token from file.')
            creds = Credentials.from_authorized_user_file(token_path, scopes)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info('Refreshing token.')
                creds.refresh(Request())
            else:
                logger.info('Fetching new token.')
                flow = InstalledAppFlow.from_client_secrets_file(creds_file_path, scopes)
                creds = flow.run_local_server(port=0)
            with open(token_path, 'w') as token_file:
                token_file.write(creds.to_json())
                logger.info(f'Token saved to {token_path}')
        return creds

    async def create_document(self, title: str = "New Document", org: str = None, role: str = "writer") -> dict:
        """
        Creates a new Google Doc with the given title.
        If 'org' is provided (e.g., "example.com"), the document will be shared with everyone in that domain,
        using the specified role (default is "writer").
        """
        def _create():
            body = {'title': title}
            return self.docs_service.documents().create(body=body).execute()
        doc = await asyncio.to_thread(_create)
        document_id = doc.get('documentId')
        logger.info(f"Created document with ID: {document_id}")

        if org and document_id:
            await self.share_document_with_org(document_id, org, role)
        return doc

    async def share_document_with_org(self, document_id: str, domain: str, role: str = "writer") -> dict:
        """
        Shares the document with everyone in the specified domain.

        Args:
            document_id (str): The ID of the document to share.
            domain (str): Your organization's domain (e.g., "example.com").
            role (str): The access level to grant ("writer" for editing, "reader" for viewing).

        Returns:
            dict: The response from the Drive API.
        """
        def _share():
            permission_body = {
                'type': 'domain',
                'role': role,
                'domain': domain
            }
            return self.drive_service.permissions().create(
                fileId=document_id,
                body=permission_body,
                fields='id'
            ).execute()
        result = await asyncio.to_thread(_share)
        logger.info(f"Shared document {document_id} with organization domain: {domain}")
        return result

    async def edit_document(self, document_id: str, requests: list) -> dict:
        """Edits a document using a batchUpdate request."""
        def _update():
            body = {'requests': requests}
            return self.docs_service.documents().batchUpdate(documentId=document_id, body=body).execute()
        result = await asyncio.to_thread(_update)
        logger.info(f"Updated document {document_id}: {result}")
        return result

    async def read_document(self, document_id: str) -> dict:
        """Retrieves the entire Google Doc as a JSON structure."""
        def _get_doc():
            return self.docs_service.documents().get(documentId=document_id).execute()
        doc = await asyncio.to_thread(_get_doc)
        logger.info(f"Read document {document_id}")
        return doc

    def extract_text(self, doc: dict) -> str:
        """
        Extracts and concatenates the plain text from the document's body content.
        This version strips trailing newline characters from each paragraph so that
        the resulting text matches the inserted content more precisely.
        """
        content = doc.get('body', {}).get('content', [])
        paragraphs = []
        for element in content:
            if 'paragraph' in element:
                para = ''
                for elem in element['paragraph'].get('elements', []):
                    if 'textRun' in elem:
                        para += elem['textRun'].get('content', '')
                # Remove any trailing newlines from the paragraph.
                paragraphs.append(para.rstrip("\n"))
        # Join paragraphs with a single newline and strip any trailing newline at the end.
        return "\n".join(paragraphs).rstrip("\n")

    async def read_document_text(self, document_id: str) -> str:
        """Convenience method to get the document text."""
        doc = await self.read_document(document_id)
        return self.extract_text(doc)

    async def rewrite_document(self, document_id: str, final_text: str) -> dict:
        """
        Rewrites the entire content of the document with the provided final text.
        It deletes the existing content (if any) and then inserts the final text at the start.
        """
        # First, read the document to determine its current length.
        doc = await self.read_document(document_id)
        body_content = doc.get("body", {}).get("content", [])
        # Get the end index from the last element, defaulting to 1 if not found.
        end_index = body_content[-1].get("endIndex", 1) if body_content else 1

        requests = []
        # Only delete content if there's something to remove.
        if end_index > 1 and (end_index - 1) > 1:
            requests.append({
                "deleteContentRange": {
                    "range": {"startIndex": 1, "endIndex": end_index - 1}
                }
            })
        # Insert the final text at index 1.
        requests.append({
            "insertText": {"location": {"index": 1}, "text": final_text}
        })
        result = await self.edit_document(document_id, requests)
        return result

    async def read_comments(self, document_id: str) -> list:
        """Reads comments on the document using the Drive API."""
        def _list_comments():
            return self.drive_service.comments().list(
                fileId=document_id,
                fields="comments(id,content,author,createdTime,modifiedTime,resolved,replies(content,author,id,createdTime,modifiedTime))"
            ).execute()
        response = await asyncio.to_thread(_list_comments)
        comments = response.get('comments', [])
        logger.info(f"Retrieved {len(comments)} comments for document {document_id}")
        return comments

    async def reply_comment(self, document_id: str, comment_id: str, reply_content: str) -> dict:
        """Replies to a specific comment on a document using the Drive API."""
        def _reply():
            body = {'content': reply_content}
            return self.drive_service.replies().create(
                fileId=document_id,
                commentId=comment_id,
                body=body,
                fields="id,content,author,createdTime,modifiedTime"
            ).execute()
        reply = await asyncio.to_thread(_reply)
        logger.info(f"Posted reply to comment {comment_id} in document {document_id}")
        return reply

    async def create_comment(self, document_id: str, content: str) -> dict:
        """Creates a comment on the document."""
        def _create_comment():
            body = {"content": content}
            return self.drive_service.comments().create(
                fileId=document_id,
                body=body,
                fields="id,content,author,createdTime,modifiedTime"
            ).execute()
        comment = await asyncio.to_thread(_create_comment)
        logger.info(f"Created comment with ID: {comment.get('id')}")
        return comment

    async def delete_reply(self, document_id: str, comment_id: str, reply_id: str) -> dict:
        """Deletes a reply to a comment in a document using the Drive API."""
        def _delete_reply():
            return self.drive_service.replies().delete(
                fileId=document_id,
                commentId=comment_id,
                replyId=reply_id
            ).execute()
        result = await asyncio.to_thread(_delete_reply)
        logger.info(f"Deleted reply {reply_id} for comment {comment_id} in document {document_id}")
        return result
