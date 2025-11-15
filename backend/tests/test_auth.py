import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Scope for Google Slides API — full access
SCOPES = ['https://www.googleapis.com/auth/presentations']

def slides_authenticate():
    """Handles OAuth flow and returns authorized Google Slides API service."""
    creds = None
    token_path = 'token.json'
    credentials_path = 'credentials/credentials.json'

    # Load existing token if available
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    # If no valid credentials, run OAuth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(credentials_path):
                raise FileNotFoundError(f"❌ Missing OAuth client file at: {credentials_path}")
            
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save token for next run
        with open(token_path, 'w') as token:
            token.write(creds.to_json())

    # Build Google Slides API service
    service = build('slides', 'v1', credentials=creds)
    return service

def get_presentation(service, presentation_id):
    """Fetches presentation metadata."""
    try:
        presentation = service.presentations().get(presentationId=presentation_id).execute()
        print(f"✅ Title: {presentation.get('title')}")
        return presentation
    except Exception as e:
        print(f"❌ Error fetching presentation: {e}")
        print("\n👉 Possible causes:")
        print("  - Wrong presentation ID")
        print("  - The authenticated user has no access to the presentation")
        print("  - OAuth token cached for another account (delete token.json and re-run)")
        return None

def main():
    service = slides_authenticate()

    # 🔑 Replace this with your Google Slides presentation ID
    presentation_id = '1k7g7x8qjB4jImEXecYhY7mOLP5L4e4PH4zr5-btK4Q4'

    get_presentation(service, presentation_id)

if __name__ == '__main__':
    main()
