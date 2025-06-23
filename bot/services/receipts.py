"""
Receipt handling service
Manages receipt file uploads to Google Drive and temporary file cleanup
"""

import os
import tempfile
import threading
import time
from typing import Optional
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.service_account import Credentials
from telebot import TeleBot

from config import GSPREAD_CREDENTIALS

# Global variables
_drive_service = None
_receipts_folder_id: Optional[str] = None

def _get_drive_service():
    """Get Google Drive service instance"""
    global _drive_service
    if _drive_service is None:
        # Указываем необходимые scopes для Google Drive
        scopes = [
            'https://www.googleapis.com/auth/drive',
            'https://www.googleapis.com/auth/drive.file'
        ]
        credentials = Credentials.from_service_account_file(
            GSPREAD_CREDENTIALS,
            scopes=scopes
        )
        _drive_service = build('drive', 'v3', credentials=credentials)
    return _drive_service

def _get_receipts_folder_id() -> str:
    """Get or create Receipts folder in Google Drive"""
    global _receipts_folder_id
    if _receipts_folder_id is None:
        service = _get_drive_service()
        
        # Search for existing folder
        results = service.files().list(
            q="name='Receipts' and mimeType='application/vnd.google-apps.folder'",
            fields="files(id, name)"
        ).execute()
        
        items = results.get('files', [])
        if items:
            _receipts_folder_id = items[0]['id']
        else:
            # Create folder
            folder_metadata = {
                'name': 'Receipts',
                'mimeType': 'application/vnd.google-apps.folder'
            }
            folder = service.files().create(body=folder_metadata,
                                          fields='id').execute()
            _receipts_folder_id = folder.get('id')
    
    return _receipts_folder_id

def save_receipt(bot: TeleBot, file_id: str) -> str:
    """
    Save receipt file to Google Drive and return share URL
    
    Args:
        bot: TeleBot instance
        file_id: Telegram file ID
        
    Returns:
        Share URL of the uploaded file
    """
    # Download file from Telegram
    file_info = bot.get_file(file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    
    # Save to temporary file
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(downloaded_file)
        temp_file_path = temp_file.name
    
    try:
        # Upload to Google Drive
        service = _get_drive_service()
        folder_id = _get_receipts_folder_id()
        
        # Determine file extension
        original_name = file_info.file_path.split('/')[-1]
        file_extension = os.path.splitext(original_name)[1]
        if not file_extension:
            file_extension = '.jpg'  # Default extension
        
        file_name = f"receipt_{int(time.time())}{file_extension}"
        
        file_metadata = {
            'name': file_name,
            'parents': [folder_id]
        }
        
        media = MediaFileUpload(temp_file_path)
        file = service.files().create(body=file_metadata,
                                    media_body=media,
                                    fields='id').execute()
        
        file_id = file.get('id')
        
        # Make file publicly accessible
        permission = {
            'type': 'anyone',
            'role': 'reader'
        }
        service.permissions().create(fileId=file_id, body=permission).execute()
        
        # Get share URL
        share_url = f"https://drive.google.com/file/d/{file_id}/view"
        
        return share_url
        
    finally:
        # Clean up temporary file
        os.unlink(temp_file_path)

def delete_tmp_files():
    """Clean up temporary files (cron-like function)"""
    temp_dir = tempfile.gettempdir()
    current_time = time.time()
    
    for filename in os.listdir(temp_dir):
        if filename.startswith('tmp'):
            file_path = os.path.join(temp_dir, filename)
            try:
                # Delete files older than 1 hour
                if os.path.getctime(file_path) < current_time - 3600:
                    os.unlink(file_path)
            except (OSError, FileNotFoundError):
                pass

# Start cleanup thread
def _cleanup_worker():
    """Background worker for cleaning up temporary files"""
    while True:
        time.sleep(3600)  # Run every hour
        delete_tmp_files()

# Start cleanup thread
cleanup_thread = threading.Thread(target=_cleanup_worker, daemon=True)
cleanup_thread.start() 