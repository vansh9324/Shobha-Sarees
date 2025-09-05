from __future__ import print_function
import os.path
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
import io
import logging

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/drive.file']

class DriveUploader:
    def __init__(self, credentials_file="credentials.json"):
        self.credentials_file = credentials_file
        try:
            self.service = self._authenticate()
            self.main_folder_id = "1doyiFBYxHfdbLmqu2seRZJMbPH2940_z"
            logger.info(f"✅ Connected to Shobha Sarees folder: {self.main_folder_id}")
        except Exception as e:
            logger.error(f"Failed to initialize DriveUploader: {str(e)}")
            raise e

    def _authenticate(self):
        """Handle Google Drive authentication with error handling"""
        try:
            creds = None
            if os.path.exists('token.pickle'):
                with open('token.pickle', 'rb') as token:
                    creds = pickle.load(token)
                    logger.info("Loaded existing credentials from token.pickle")

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    logger.info("Refreshing expired credentials")
                    creds.refresh(Request())
                else:
                    logger.info("Running OAuth flow for new credentials")
                    if not os.path.exists(self.credentials_file):
                        raise FileNotFoundError(f"Credentials file not found: {self.credentials_file}")
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, SCOPES
                    )
                    # Use console flow instead of local server for cloud deployment
                    creds = flow.run_console()
                    
                with open('token.pickle', 'wb') as token:
                    pickle.dump(creds, token)
                    logger.info("Saved new credentials to token.pickle")

            service = build('drive', 'v3', credentials=creds)
            logger.info("Successfully built Drive service")
            return service
            
        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            raise e

    def get_or_create_folder(self, folder_name, parent_id):
        """Get existing folder or create new one in specific parent"""
        try:
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and parents in '{parent_id}'"
            results = self.service.files().list(q=query).execute()
            folders = results.get('files', [])
            if folders:
                logger.info(f"📁 Found existing folder: {folder_name}")
                return folders[0]['id']
            else:
                folder_metadata = {
                    'name': folder_name,
                    'mimeType': 'application/vnd.google-apps.folder',
                    'parents': [parent_id]
                }
                folder = self.service.files().create(body=folder_metadata).execute()
                logger.info(f"📁 Created new folder: {folder_name}")
                return folder.get('id')
        except Exception as e:
            logger.error(f"Error in get_or_create_folder: {str(e)}")
            raise e

    def upload_image(self, image_bytes, filename, catalog):
        """Upload with comprehensive error handling"""
        try:
            logger.info(f"Starting upload: {filename} to catalog {catalog}")
            
            # Create catalog-specific folder
            catalog_folder_id = self.get_or_create_folder(catalog, self.main_folder_id)
            logger.info(f"Using catalog folder ID: {catalog_folder_id}")

            # Check for existing files
            existing_files = self.service.files().list(
                q=f"name='{filename}' and parents in '{catalog_folder_id}'"
            ).execute().get('files', [])

            if existing_files:
                import datetime
                timestamp = datetime.datetime.now().strftime("%H%M%S")
                name_parts = filename.rsplit('.', 1)
                filename = f"{name_parts[0]}_{timestamp}.{name_parts[1]}"
                logger.info(f"File exists, renamed to: {filename}")

            # Upload file
            logger.info(f"Uploading {len(image_bytes.getvalue())} bytes")
            media = MediaIoBaseUpload(image_bytes, mimetype='image/jpeg', resumable=True)
            file_metadata = {
                'name': filename,
                'parents': [catalog_folder_id]
            }

            file_result = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,webViewLink'
            ).execute()

            url = file_result.get('webViewLink')
            logger.info(f"✅ Upload successful: {filename} -> {url}")
            return url

        except Exception as e:
            logger.error(f"❌ Upload error for {filename}: {str(e)}")
            raise e
