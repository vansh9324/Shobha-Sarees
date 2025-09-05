from __future__ import print_function
import os.path
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
import io

SCOPES = ['https://www.googleapis.com/auth/drive.file']

class DriveUploader:
    def __init__(self, credentials_file="credentials.json"):
        self.credentials_file = credentials_file
        self.service = self._authenticate()
        
        # Your specific Shobha Sarees folder ID
        self.main_folder_id = "1doyiFBYxHfdbLmqu2seRZJMbPH2940_z"
        
        print(f"✅ Connected to Shobha Sarees folder: {self.main_folder_id}")
    
    def _authenticate(self):
        """Handle Google Drive authentication"""
        creds = None
        
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
        
        return build('drive', 'v3', credentials=creds)
    
    def get_or_create_folder(self, folder_name, parent_id):
        """Get existing folder or create new one in specific parent"""
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and parents in '{parent_id}'"
        
        results = self.service.files().list(q=query).execute()
        folders = results.get('files', [])
        
        if folders:
            print(f"📁 Found existing folder: {folder_name}")
            return folders[0]['id']
        else:
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_id]
            }
            
            folder = self.service.files().create(body=folder_metadata).execute()
            print(f"📁 Created new folder: {folder_name}")
            return folder.get('id')
    
    def upload_image(self, image_bytes, filename, catalog):
        """
        Upload to specific catalog folder within Shobha Sarees
        
        Structure: Shobha Sarees/{catalog}/{filename}
        """
        try:
            # Create catalog-specific folder within Shobha Sarees
            catalog_folder_id = self.get_or_create_folder(catalog, self.main_folder_id)
            
            # Check for existing files and handle duplicates
            existing_files = self.service.files().list(
                q=f"name='{filename}' and parents in '{catalog_folder_id}'"
            ).execute().get('files', [])
            
            if existing_files:
                # Add timestamp to avoid duplicates
                import datetime
                timestamp = datetime.datetime.now().strftime("%H%M%S")
                name_parts = filename.rsplit('.', 1)
                filename = f"{name_parts[0]}_{timestamp}.{name_parts[1]}"
                print(f"⚠️ File exists, renamed to: {filename}")
            
            # Upload file
            media = MediaIoBaseUpload(image_bytes, mimetype='image/jpeg', resumable=True)
            file_metadata = {
                'name': filename,
                'parents': [catalog_folder_id]
            }
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,webViewLink'
            ).execute()
            
            print(f"✅ Uploaded: {filename} to Shobha Sarees/{catalog}/")
            return file.get('webViewLink')
            
        except Exception as e:
            print(f"❌ Upload error: {str(e)}")
            raise e
