"""
Drive Uploader Module

Uploads files to Google Drive with optional conversion to Google Docs format.
Uses Application Default Credentials for seamless local and cloud deployment.
"""

import os
from pathlib import Path

from google.auth import default
from google.auth.exceptions import DefaultCredentialsError
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Scopes required for Drive API
DRIVE_SCOPES = ['https://www.googleapis.com/auth/drive.file']

# MIME type mappings for conversion
GOOGLE_DOC_MIME = 'application/vnd.google-apps.document'
PDF_MIME = 'application/pdf'


def _get_drive_service():
    """
    Get an authenticated Google Drive service.

    Uses Application Default Credentials which works for:
    - Local development: via `gcloud auth application-default login`
    - Google Cloud: via attached service account

    Returns:
        Google Drive API service object.

    Raises:
        DefaultCredentialsError: If no credentials are available.
    """
    try:
        credentials, project = default(scopes=DRIVE_SCOPES)
    except DefaultCredentialsError:
        raise DefaultCredentialsError(
            "No credentials found. For local development, run:\n"
            "  gcloud auth application-default login\n\n"
            "For Google Cloud, ensure a service account is attached to your resource."
        )

    return build('drive', 'v3', credentials=credentials)


def upload_to_drive(
    file_path: str,
    folder_id: str | None = None,
    convert_to_doc: bool = True,
    delete_local: bool = False,
    file_name: str | None = None
) -> dict:
    """
    Upload a file to Google Drive, optionally converting to Google Docs format.

    Args:
        file_path: Path to the local file to upload.
        folder_id: Google Drive folder ID to upload to. If None, uploads to root.
        convert_to_doc: If True and file is PDF, convert to Google Doc.
        delete_local: If True, delete the local file after successful upload.
        file_name: Custom name for the file in Drive. If None, uses original filename.

    Returns:
        Dict containing:
            - id: Google Drive file ID
            - name: File name in Drive
            - url: URL to view/edit the file
            - mimeType: MIME type of the uploaded file

    Raises:
        FileNotFoundError: If the local file doesn't exist.
        DefaultCredentialsError: If no credentials are available.

    Example:
        >>> result = upload_to_drive(
        ...     'report.pdf',
        ...     folder_id='1ABC123...',
        ...     convert_to_doc=True,
        ...     delete_local=True
        ... )
        >>> print(result['url'])
        https://docs.google.com/document/d/xyz.../edit
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    service = _get_drive_service()

    # Determine file name
    name = file_name or path.stem

    # Build file metadata
    file_metadata = {'name': name}

    # Add parent folder if specified
    if folder_id:
        file_metadata['parents'] = [folder_id]

    # Determine MIME types
    local_mime = _get_mime_type(path)

    # Convert PDF to Google Doc if requested
    if convert_to_doc and local_mime == PDF_MIME:
        file_metadata['mimeType'] = GOOGLE_DOC_MIME

    # Upload the file
    media = MediaFileUpload(
        str(path),
        mimetype=local_mime,
        resumable=True
    )

    uploaded_file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, name, mimeType, webViewLink'
    ).execute()

    # Delete local file if requested
    if delete_local:
        path.unlink()

    return {
        'id': uploaded_file['id'],
        'name': uploaded_file['name'],
        'url': uploaded_file.get('webViewLink', f"https://drive.google.com/file/d/{uploaded_file['id']}/view"),
        'mimeType': uploaded_file['mimeType']
    }


def _get_mime_type(path: Path) -> str:
    """Get MIME type based on file extension."""
    mime_types = {
        '.pdf': 'application/pdf',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.txt': 'text/plain',
        '.csv': 'text/csv',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.xls': 'application/vnd.ms-excel',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
    }
    return mime_types.get(path.suffix.lower(), 'application/octet-stream')


def list_files_in_folder(folder_id: str, page_size: int = 100) -> list[dict]:
    """
    List files in a Google Drive folder.

    Args:
        folder_id: Google Drive folder ID.
        page_size: Maximum number of files to return.

    Returns:
        List of file dictionaries with id, name, mimeType, and url.
    """
    service = _get_drive_service()

    results = service.files().list(
        q=f"'{folder_id}' in parents and trashed = false",
        pageSize=page_size,
        fields="files(id, name, mimeType, webViewLink)"
    ).execute()

    files = results.get('files', [])

    return [
        {
            'id': f['id'],
            'name': f['name'],
            'mimeType': f['mimeType'],
            'url': f.get('webViewLink', f"https://drive.google.com/file/d/{f['id']}/view")
        }
        for f in files
    ]


def delete_from_drive(file_id: str) -> None:
    """
    Delete a file from Google Drive.

    Args:
        file_id: Google Drive file ID to delete.
    """
    service = _get_drive_service()
    service.files().delete(fileId=file_id).execute()
