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
    def __init__(self, creds_file_path: str, token_path: str,
                 scopes: list[str] = None):
        # Include both Docs and Drive scopes.
        if scopes is None:
            scopes = [
                'https://www.googleapis.com/auth/documents',
                'https://www.googleapis.com/auth/drive'
            ]
        self.creds = self._get_credentials(creds_file_path, token_path, scopes)
        # Initialize the Docs API client.
        self.docs_service = build('docs', 'v1', credentials=self.creds)
        # Initialize the Drive API client (for comments operations).
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

    async def create_document(self, title: str = "New Document") -> dict:
        """Creates a new Google Doc with the given title."""
        def _create():
            body = {'title': title}
            return self.docs_service.documents().create(body=body).execute()
        doc = await asyncio.to_thread(_create)
        logger.info(f"Created document with ID: {doc.get('documentId')}")
        return doc

    async def edit_document(self, document_id: str, requests: list) -> dict:
        """Edits a document using a batchUpdate request."""
        def _update():
            body = {'requests': requests}
            return self.docs_service.documents().batchUpdate(documentId=document_id, body=body).execute()
        result = await asyncio.to_thread(_update)
        logger.info(f"Updated document {document_id}: {result}")
        return result

    async def read_comments(self, document_id: str) -> list:
        """Reads comments on the document using the Drive API."""
        def _list_comments():
            # Request only supported fields (replyCount removed).
            return self.drive_service.comments().list(
                fileId=document_id,
                fields="comments(id,content,author,createdTime,modifiedTime)"
            ).execute()
        response = await asyncio.to_thread(_list_comments)
        comments = response.get('comments', [])
        logger.info(f"Retrieved {len(comments)} comments for document {document_id}")
        return comments

    async def reply_comment(self, document_id: str, comment_id: str, reply_content: str) -> dict:
        """Replies to a specific comment on a document using the Drive API."""
        def _reply():
            body = {'content': reply_content}
            # Provide the required fields parameter.
            return self.drive_service.replies().create(
                fileId=document_id,
                commentId=comment_id,
                body=body,
                fields="id,content,author,createdTime,modifiedTime"
            ).execute()
        reply = await asyncio.to_thread(_reply)
        logger.info(f"Posted reply to comment {comment_id} in document {document_id}")
        return reply

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
        This walks through all the structural elements (typically paragraphs) and collects text.
        """
        content = doc.get('body', {}).get('content', [])
        paragraphs = []
        for element in content:
            if 'paragraph' in element:
                para = ''
                for elem in element['paragraph'].get('elements', []):
                    if 'textRun' in elem:
                        para += elem['textRun'].get('content', '')
                paragraphs.append(para)
        return "\n".join(paragraphs)

    async def read_document_text(self, document_id: str) -> str:
        """Convenience method to get the document text."""
        doc = await self.read_document(document_id)
        return self.extract_text(doc)
