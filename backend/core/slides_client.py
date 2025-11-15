"""
Google Slides API Client for PPT Automation
Handles all interactions with Google Slides API
"""
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials as UserCredentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.http import MediaFileUpload
import os
import re
from config import AUTH_MODE, GOOGLE_CREDENTIALS_FILE, GOOGLE_OAUTH_CLIENT_FILE, GOOGLE_TOKEN_FILE, GOOGLE_SCOPES, LOG_LEVEL, LOG_FILE
import copy
from utils.logger import get_logger


class SlidesClient:
    def __init__(self):
        """Initialize the Google Slides API client"""
        self.logger = get_logger(__name__, LOG_LEVEL, LOG_FILE)
        self.service = None
        self.drive_service = None
        self._authenticate()
    
    def _extract_file_id(self, template_presentation_id_or_url):
        """Extract Google file ID from a plain ID or a full Slides URL."""
        if not template_presentation_id_or_url:
            return None
        value = str(template_presentation_id_or_url).strip()
        # If it looks like a full URL, try to extract the /d/<ID>/ segment
        if value.startswith('http://') or value.startswith('https://'):
            # Typical format: https://docs.google.com/presentation/d/<ID>/edit
            parts = value.split('/d/')
            if len(parts) > 1:
                tail = parts[1]
                file_id = tail.split('/')[0]
                return file_id
            # Alternate format with id query param
            if 'id=' in value:
                try:
                    from urllib.parse import urlparse, parse_qs
                    parsed = urlparse(value)
                    qs = parse_qs(parsed.query)
                    return (qs.get('id') or [None])[0]
                except Exception:
                    return None
            return None
        return value

    def copy_presentation(self, template_presentation_id, new_title=None):
        """Create a new presentation by copying an existing template via Drive API.

        Returns the new presentation ID or None on failure.
        """
        try:
            if not template_presentation_id:
                self.logger.error("Template presentation ID is required to copy")
                return None

            # Accept full URL or raw ID
            file_id = self._extract_file_id(template_presentation_id)
            if not file_id:
                self.logger.error("Could not parse template presentation ID from value provided")
                return None

            # Verify the file exists and we have access before attempting to copy
            try:
                _ = self.drive_service.files().get(
                    fileId=file_id,
                    fields='id, name, mimeType',
                    supportsAllDrives=True
                ).execute()
            except HttpError as e:
                self.logger.error(
                    "Template not accessible. Share the template with the authorized account or update Drive scopes. "
                    f"Original: {e}"
                )
                return None

            file_metadata = {}
            if new_title:
                file_metadata['name'] = new_title

            copied = self.drive_service.files().copy(
                fileId=file_id,
                body=file_metadata,
                supportsAllDrives=True
            ).execute()

            new_id = copied.get('id')
            if new_id:
                self.logger.info(f"Copied presentation {template_presentation_id} -> {new_id}")
                return new_id
            else:
                self.logger.error("Drive copy returned no ID")
                return None
        except Exception as e:
            self.logger.error(f"Failed to copy presentation: {e}")
            return None

    def _authenticate(self):
        """Authenticate with Google Slides API"""
        try:
            if AUTH_MODE == 'oauth':
                creds = None
                if os.path.exists(GOOGLE_TOKEN_FILE):
                    creds = UserCredentials.from_authorized_user_file(GOOGLE_TOKEN_FILE, GOOGLE_SCOPES)
                if not creds or not creds.valid:
                    if creds and creds.expired and creds.refresh_token:
                        creds.refresh(Request())
                    else:
                        if not os.path.exists(GOOGLE_OAUTH_CLIENT_FILE):
                            raise FileNotFoundError(f"Missing OAuth client file at: {GOOGLE_OAUTH_CLIENT_FILE}")
                        flow = InstalledAppFlow.from_client_secrets_file(GOOGLE_OAUTH_CLIENT_FILE, GOOGLE_SCOPES)
                        creds = flow.run_local_server(port=0)
                    with open(GOOGLE_TOKEN_FILE, 'w') as token:
                        token.write(creds.to_json())
                credentials = creds
            else:
                credentials = service_account.Credentials.from_service_account_file(
                    GOOGLE_CREDENTIALS_FILE,
                    scopes=GOOGLE_SCOPES
                )
            # Store credentials for reuse by other Google APIs (e.g., Sheets)
            self._credentials = credentials
            self.service = build('slides', 'v1', credentials=credentials)
            self.drive_service = build('drive', 'v3', credentials=credentials)
            self.logger.info("Successfully authenticated with Google Slides and Drive API")
        except Exception as e:
            self.logger.error(f"Authentication failed: {e}")
            raise
    def get_credentials(self):
        """Get the authenticated credentials for use with other Google APIs"""
        return self._credentials if hasattr(self, '_credentials') else None
    def get_presentation(self, presentation_id):
        """Get presentation details"""
        try:
            presentation = self.service.presentations().get(
                presentationId=presentation_id
            ).execute()
            return presentation
        except HttpError as e:
            self.logger.error(f"Error getting presentation: {e}")
            return None
    
    def find_placeholders(self, presentation_id):
        """Find all placeholders in the presentation from shapes and tables"""
        presentation = self.get_presentation(presentation_id)
        if not presentation:
            return []

        placeholder_pattern = re.compile(r'\{\{([^}]+)\}\}')
        placeholders = []

        for slide in presentation.get('slides', []):
            slide_id = slide.get('objectId')
            for element in slide.get('pageElements', []):
                element_id = element.get('objectId')

                # Extract text from shapes
                if 'shape' in element and element['shape'].get('text'):
                    text_elements = element['shape']['text'].get('textElements', [])
                    buffer = []
                    for te in text_elements:
                        if 'textRun' in te and te['textRun'].get('content'):
                            buffer.append(te['textRun']['content'])
                        elif 'autoText' in te and te['autoText'].get('content'):
                            buffer.append(te['autoText']['content'])
                    text_content = ''.join(buffer)
                    for match in placeholder_pattern.findall(text_content or ''):
                        placeholders.append({
                            'placeholder': match,
                            'element_id': element_id,
                            'slide_id': slide_id,
                            'text_content': text_content
                        })

                # Extract text from tables
                if 'table' in element:
                    table = element['table']
                    rows = table.get('tableRows', [])
                    for row in rows:
                        cells = row.get('tableCells', [])
                        for cell in cells:
                            cell_text = cell.get('text')
                            if not cell_text:
                                continue
                            buffer = []
                            for te in cell_text.get('textElements', []):
                                if 'textRun' in te and te['textRun'].get('content'):
                                    buffer.append(te['textRun']['content'])
                            text_content = ''.join(buffer)
                            for match in placeholder_pattern.findall(text_content or ''):
                                placeholders.append({
                                    'placeholder': match,
                                    'element_id': element_id,
                                    'slide_id': slide_id,
                                    'text_content': text_content
                                })

        return placeholders
    
    def replace_placeholders(self, presentation_id, content_map):
        """Replace placeholders with generated content"""
        requests = []
        
        for placeholder, content in content_map.items():
            # Check if this is already a full placeholder (e.g., {{
            if placeholder.startswith('{{') and placeholder.endswith('}}'):
                # Use the placeholder as-is
                placeholder_text = placeholder
            else:
                # Wrap in braces
                placeholder_text = f'{{{{{placeholder}}}}}'
            
            requests.append({
                'replaceAllText': {
                    'containsText': {'text': placeholder_text},
                    'replaceText': content
                }
            })
        
        try:
            response = self.service.presentations().batchUpdate(
                presentationId=presentation_id,
                body={'requests': requests}
            ).execute()
            
            self.logger.info(f"Successfully replaced {len(requests)} placeholders")
            return response
            
        except HttpError as e:
            self.logger.error(f"Error replacing placeholders: {e}")
            return None

    def replace_mixed_placeholders(self, presentation_id, text_map, image_map):
        """Replace text placeholders only (images are handled separately)"""
        requests = []

        # Text replacements only
        for placeholder, content in (text_map or {}).items():
            # Use placeholder as-is if it's already wrapped in braces (e.g., {{u0022}})
            if isinstance(placeholder, str) and placeholder.startswith('{{') and placeholder.endswith('}}'):
                placeholder_text = placeholder
            else:
                placeholder_text = f'{{{{{placeholder}}}}}'

            requests.append({
                'replaceAllText': {
                    'containsText': {'text': placeholder_text},
                    'replaceText': content
                }
            })

        if not requests:
            self.logger.info("No text replacement requests to execute")
            return None

        try:
            response = self.service.presentations().batchUpdate(
                presentationId=presentation_id,
                body={'requests': requests}
            ).execute()
            self.logger.info(f"Replaced text: {len(text_map or {})}")
            return response
        except HttpError as e:
            self.logger.error(f"Error replacing text placeholders: {e}")
            return None
    
    def apply_text_styling(self, presentation_id, text_styling_map, theme=None):
        """Apply color and styling to text elements based on theme"""
        # Reload presentation to get current state after text replacements
        presentation = self.get_presentation(presentation_id)
        if not presentation:
            self.logger.warning("Could not load presentation for style validation")
            return None
        
        requests = []
        
        # Build a map of current element IDs to their text content for debugging
        element_text_map = {}
        # Also build reverse map: text content -> element_id (for fallback lookup)
        text_to_element_map = {}
        
        for slide in presentation.get('slides', []):
            slide_id = slide.get('objectId')
            for element in slide.get('pageElements', []):
                element_id = element.get('objectId')
                if element_id and 'shape' in element:
                    shape = element.get('shape', {})
                    if shape.get('text'):
                        text_elements = shape['text'].get('textElements', [])
                        text_content = ''
                        for te in text_elements:
                            if 'textRun' in te:
                                text_content += te.get('textRun', {}).get('content', '')
                        element_text_map[element_id] = text_content[:50]  # First 50 chars for logging
                        # Store full text for reverse lookup (normalized)
                        text_normalized = text_content.strip().lower()
                        if text_normalized:
                            text_to_element_map[text_normalized] = element_id
        
        # Try to apply styling using the stored element IDs
        elements_found = 0
        elements_not_found = 0
        elements_found_by_text = 0
        
        # Track which elements we've already processed to avoid duplicate styling
        processed_elements = {}  # element_id_to_use -> color info
        
        for original_element_id, styling in text_styling_map.items():
            element_id_to_use = original_element_id
            
            
            # Check if this element still exists and has text
            has_text = element_id_to_use in element_text_map
            
            if not has_text:
                # Element ID changed after text replacement - skip this element
                # Colors will be applied by other styling_map entries that find their elements correctly
                # This ensures we don't accidentally apply wrong colors via text search matching
                elements_not_found += 1
                self.logger.debug(f"⚠️ Element {original_element_id} not found - element IDs changed after text replacement, skipping (will be handled by other entries)")
                continue
            
            elements_found += 1
            color_hex = styling.get('color', 'NOT_SET')
            
            # Check if we've already processed this element - skip duplicates
            # This happens when multiple placeholder instances map to the same element after text replacement
            if element_id_to_use in processed_elements:
                continue
            
            # Track processed elements
            processed_elements[element_id_to_use] = {
                'color': color_hex,
                'styling': styling
            }
            
            # Log styling application (strictly from config files)
            self.logger.debug(f"Applying style to element {element_id_to_use} (original: {original_element_id}): color={color_hex}")
            
            style = {}
            fields = []

            if 'color' in styling and styling.get('color'):
                color_value = styling.get('color')
                # Use color as-is from config files - no overrides
                rgb_color = self._hex_to_rgb(color_value)
                style['foregroundColor'] = {
                    'opaqueColor': {
                        'rgbColor': rgb_color
                    }
                }
                fields.append('foregroundColor')

            if 'font_size' in styling and styling.get('font_size') is not None:
                style['fontSize'] = {
                    'magnitude': styling.get('font_size'),
                    'unit': 'PT'
                }
                fields.append('fontSize')

            if 'bold' in styling:
                style['bold'] = styling.get('bold')
                fields.append('bold')

            if 'italic' in styling:
                style['italic'] = styling.get('italic')
                fields.append('italic')

            if 'font_family' in styling and styling.get('font_family'):
                style['fontFamily'] = styling.get('font_family')
                fields.append('fontFamily')

            if not fields:
                continue

            style_request = {
                'updateTextStyle': {
                    'objectId': element_id_to_use,
                    'style': style,
                    'fields': ','.join(fields)
                }
            }
            requests.append(style_request)
            
        
        if requests:
            self.logger.info(f"📝 Applying styling to {len(requests)} elements (found: {elements_found}, found_by_text: {elements_found_by_text}, missing: {elements_not_found})")
            result = self.batch_update_requests(presentation_id, requests)
            if result:
                self.logger.info(f"✅ Successfully applied styling to {len(requests)} elements")
            else:
                self.logger.warning(f"⚠️ Failed to apply styling (batch_update returned None)")
            return result
        else:
            self.logger.warning(f"⚠️ No styling requests generated (found: {elements_found}, found_by_text: {elements_found_by_text}, missing: {elements_not_found})")
        return None


    def batch_update_requests(self, presentation_id, requests):
        """Execute arbitrary batchUpdate requests"""
        if not requests:
            return None
        try:
            return self.service.presentations().batchUpdate(
                presentationId=presentation_id,
                body={'requests': requests}
            ).execute()
        except HttpError as e:
            self.logger.error(f"Error executing batchUpdate: {e}")
            return None
    
    def reorder_page_elements(self, presentation_id, slide_id, element_order):
        """
        Reordering z-index is not supported by the Google Slides REST API.
        This method is a no-op and logs guidance.
        """
        self.logger.info(
            "Z-order reordering is not supported via Slides API. "
            "Consider designing the template so elements meant to be behind are backgrounds."
        )
        return None
    
    def bring_element_to_front(self, presentation_id, slide_id, element_id):
        """Not supported by Slides REST API (no-op)."""
        self.logger.info("bring_to_front not supported via Slides API (no-op)")
        return None
    
    def send_element_to_back(self, presentation_id, slide_id, element_id):
        """Not supported by Slides REST API (no-op)."""
        self.logger.info("send_to_back not supported via Slides API (no-op)")
        return None

    def get_presentation_url(self, presentation_id):
        """Get the shareable URL for the presentation"""
        return f"https://docs.google.com/presentation/d/{presentation_id}/edit"

    def add_hyperlink_to_placeholder(self, presentation_id, placeholder_text, display_text, url, slide_id=None, color=None):
        """
        Replace a text placeholder with hyperlinked display text using replaceAllText and updateTextStyle.
        
        Uses the recommended Google Slides API approach:
        1. Find placeholder positions before replacement
        2. replaceAllText to replace placeholder with display text
        3. updateTextStyle to add hyperlink only to the positions that were just replaced
        
        Args:
            presentation_id: The presentation ID
            placeholder_text: The placeholder text to replace (e.g., "{{placeholder}}")
            display_text: The text to display as the hyperlink
            url: The URL to link to
            slide_id: Optional slide ID to limit search to specific slide
            color: Optional hex color string (e.g., "#2563eb") for the hyperlink text. Defaults to blue if not provided.
        """
        try:
            self.logger.info(
                f"🔗 Hyperlink request: placeholder='{placeholder_text}', display='{display_text}', url='{url}', slide_id={slide_id}, color={color}"
            )
            
            # Step 0: Find placeholder positions BEFORE replacement to track which occurrences to hyperlink
            self.logger.info(f"📖 Step 0: Finding placeholder positions before replacement...")
            presentation_before = self.get_presentation(presentation_id)
            if not presentation_before:
                self.logger.error("Failed to get presentation before replacement")
                return False
            
            placeholder_positions = []  # List of (slide_id, element_id, start_index, end_index)
            
            for slide in presentation_before.get('slides', []):
                if slide_id and slide.get('objectId') != slide_id:
                    continue
                
                for element in slide.get('pageElements', []):
                    if 'shape' in element and element['shape'].get('text'):
                        element_id = element.get('objectId')
                        text_content = ''
                        text_elements = element['shape']['text'].get('textElements', [])
                        for text_element in text_elements:
                            if 'textRun' in text_element:
                                text_content += text_element['textRun'].get('content', '')
                        
                        # Find all occurrences of placeholder_text in this element
                        start_index = 0
                        while True:
                            idx = text_content.find(placeholder_text, start_index)
                            if idx == -1:
                                break
                            
                            end_idx = idx + len(placeholder_text)
                            placeholder_positions.append({
                                'slide_id': slide.get('objectId'),
                                'element_id': element_id,
                                'start_index': idx,
                                'end_index': end_idx
                            })
                            
                            # Move to next occurrence
                            start_index = end_idx
            
            if not placeholder_positions:
                self.logger.warning(f"⚠️ No occurrences found for placeholder: {placeholder_text}")
                return False
            
            self.logger.info(f"📍 Found {len(placeholder_positions)} occurrence(s) of '{placeholder_text}' to replace")
            
            # Step 1: Use replaceAllText to replace placeholder with display text
            replace_request = {
                'replaceAllText': {
                    'containsText': {
                        'text': placeholder_text,
                        'matchCase': False
                    },
                    'replaceText': display_text
                }
            }
            
            self.logger.info(f"📝 Step 1: Replacing '{placeholder_text}' with '{display_text}' using replaceAllText")
            
            # Execute replaceAllText
            replace_response = self.service.presentations().batchUpdate(
                presentationId=presentation_id,
                body={'requests': [replace_request]}
            ).execute()
            
            occurrences_replaced = replace_response.get('replies', [{}])[0].get('replaceAllText', {}).get('occurrencesChanged', 0)
            self.logger.info(f"✅ Replaced {occurrences_replaced} occurrence(s) of '{placeholder_text}' with '{display_text}'")
            
            if occurrences_replaced == 0:
                self.logger.warning(f"⚠️ No occurrences found for placeholder: {placeholder_text}")
                return False
            
            # Step 2: Reload presentation to find the new text positions
            self.logger.info(f"📖 Step 2: Reloading presentation to find replaced text positions...")
            presentation = self.get_presentation(presentation_id)
            if not presentation:
                self.logger.error("Failed to reload presentation after text replacement")
                return False
            
            # Step 3: Apply hyperlink only to the positions we tracked (now containing display_text)
            style_requests = []
            display_length = len(display_text)
            
            for pos_info in placeholder_positions:
                element_id = pos_info['element_id']
                original_start = pos_info['start_index']
                
                # After replacement, the position is the same start, but end is adjusted
                # Since we're replacing with display_text, the new end is start + display_length
                new_start = original_start
                new_end = original_start + display_length
                
                # Verify this element still exists and contains the display text at this position
                element_found = False
                for slide in presentation.get('slides', []):
                    if slide.get('objectId') != pos_info['slide_id']:
                        continue
                    for element in slide.get('pageElements', []):
                        if element.get('objectId') == element_id and 'shape' in element and element['shape'].get('text'):
                            text_content = ''
                            text_elements = element['shape']['text'].get('textElements', [])
                            for text_element in text_elements:
                                if 'textRun' in text_element:
                                    text_content += text_element['textRun'].get('content', '')
                            
                            # Check if display_text is at the expected position
                            if new_start < len(text_content) and new_end <= len(text_content):
                                expected_text = text_content[new_start:new_end]
                                if expected_text == display_text:
                                    element_found = True
                                    
                                    # Determine color for hyperlink
                                    if color:
                                        rgb_color = self._hex_to_rgb(color)
                                    else:
                                        # Default to blue if no color specified
                                        rgb_color = {'red': 0.0, 'green': 0.0, 'blue': 1.0}
                                    
                                    # Determine if underline should be applied (only for follow_reference_link_1 to follow_reference_link_6)
                                    should_underline = any(
                                        f'follow_reference_link_{i}' in placeholder_text 
                                        for i in range(1, 7)
                                    )
                                    
                                    # Apply hyperlink style to this specific occurrence
                                    style_requests.append({
                                        'updateTextStyle': {
                                            'objectId': element_id,
                                            'textRange': {
                                                'type': 'FIXED_RANGE',
                                                'startIndex': new_start,
                                                'endIndex': new_end
                                            },
                                            'style': {
                                                'link': {'url': url},
                                                'foregroundColor': {
                                                    'opaqueColor': {
                                                        'rgbColor': rgb_color
                                                    }
                                                },
                                                'underline': should_underline
                                            },
                                            'fields': 'link,foregroundColor,underline'
                                        }
                                    })
                                    
                                    self.logger.debug(f"  📍 Applying hyperlink to '{display_text}' at index {new_start}-{new_end} in element {element_id} on slide {pos_info['slide_id']}")
                                else:
                                    self.logger.warning(f"⚠️ Expected '{display_text}' at position {new_start}-{new_end}, but found '{expected_text}'")
                            break
                    if element_found:
                        break
                
                if not element_found:
                    self.logger.warning(f"⚠️ Could not find element {element_id} or display text at expected position after replacement")
            
            # Step 4: Apply hyperlink styles to tracked occurrences only
            if style_requests:
                self.logger.info(f"🔗 Step 3: Applying hyperlink styles to {len(style_requests)} occurrence(s) using updateTextStyle")
                
                # Execute all style updates in one batch
                style_response = self.service.presentations().batchUpdate(
                    presentationId=presentation_id,
                    body={'requests': style_requests}
                ).execute()
                
                self.logger.info(f"✅ Successfully added hyperlinks to {len(style_requests)} occurrence(s) of '{display_text}'")
                self.logger.info(f"🔗 Hyperlink URL: {url}")
                return True
            else:
                self.logger.warning(f"⚠️ No valid occurrences found to apply hyperlink")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error adding hyperlink to placeholder: {e}")
            import traceback
            traceback.print_exc()
            return False

    def build_google_sheets_url(self, sheets_id, gid=None):
        """Build a Google Sheets URL."""
        if not sheets_id:
            return None
        if gid is not None:
            return f"https://docs.google.com/spreadsheets/d/{sheets_id}/edit#gid={gid}"
        return f"https://docs.google.com/spreadsheets/d/{sheets_id}/edit"

    def delete_slide(self, presentation_id, slide_object_id):
        """Delete a slide from a presentation by its object ID.
        
        Args:
            presentation_id: The ID of the presentation
            slide_object_id: The object ID of the slide to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            requests = [{
                'deleteObject': {
                    'objectId': slide_object_id
                }
            }]
            
            result = self.service.presentations().batchUpdate(
                presentationId=presentation_id,
                body={'requests': requests}
            ).execute()
            
            self.logger.info(f"Successfully deleted slide {slide_object_id} from presentation {presentation_id}")
            return True
            
        except HttpError as e:
            self.logger.error(f"Failed to delete slide {slide_object_id}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error deleting slide: {e}")
            return False
    
    def delete_slides(self, presentation_id, slide_object_ids):
        """Delete multiple slides from a presentation by their object IDs.
        
        Args:
            presentation_id: The ID of the presentation
            slide_object_ids: List of slide object IDs to delete
            
        Returns:
            True if all deletions successful, False otherwise
        """
        try:
            if not slide_object_ids:
                self.logger.warning("No slide IDs provided for deletion")
                return False
            
            requests = []
            for slide_id in slide_object_ids:
                requests.append({
                    'deleteObject': {
                        'objectId': slide_id
                    }
                })
            
            result = self.service.presentations().batchUpdate(
                presentationId=presentation_id,
                body={'requests': requests}
            ).execute()
            
            self.logger.info(f"Successfully deleted {len(slide_object_ids)} slide(s) from presentation {presentation_id}")
            return True
            
        except HttpError as e:
            self.logger.error(f"Failed to delete slides: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error deleting slides: {e}")
            return False
    
    def get_slide_ids(self, presentation_id):
        """Get a list of all slide object IDs in a presentation.
        
        Args:
            presentation_id: The ID of the presentation
            
        Returns:
            List of slide object IDs, or empty list if error
        """
        try:
            presentation = self.get_presentation(presentation_id)
            if not presentation:
                return []
            
            slide_ids = [slide.get('objectId') for slide in presentation.get('slides', []) if slide.get('objectId')]
            return slide_ids
            
        except Exception as e:
            self.logger.error(f"Error getting slide IDs: {e}")
            return []

    def get_or_create_uploads_folder(self):
        """Get or create the 'Uploads' folder in Google Drive root"""
        try:
            # Search for existing "Uploads" folder
            query = "name='Uploads' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = self.drive_service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)'
            ).execute()
            
            folders = results.get('files', [])
            
            if folders:
                # Folder exists, return its ID
                folder_id = folders[0]['id']
                self.logger.info(f"Found existing 'Uploads' folder: {folder_id}")
                return folder_id
            else:
                # Create new folder
                folder_metadata = {
                    'name': 'Uploads',
                    'mimeType': 'application/vnd.google-apps.folder'
                }
                folder = self.drive_service.files().create(
                    body=folder_metadata,
                    fields='id'
                ).execute()
                folder_id = folder.get('id')
                self.logger.info(f"Created new 'Uploads' folder: {folder_id}")
                return folder_id
                
        except Exception as e:
            self.logger.error(f"Error getting/creating Uploads folder: {e}")
            return None
    
    def upload_image_to_drive(self, image_path, filename=None):
        """Upload image to Google Drive 'Uploads' folder, make it public, and return (file_id, public_url)"""
        try:
            if not os.path.exists(image_path):
                self.logger.error(f"Image file not found: {image_path}")
                return None
            
            if not filename:
                filename = os.path.basename(image_path)
            
            # Get or create the "Uploads" folder
            uploads_folder_id = self.get_or_create_uploads_folder()
            if not uploads_folder_id:
                self.logger.warning("Could not get Uploads folder, uploading to root instead")
                uploads_folder_id = None
            
            # Create file metadata with parent folder
            file_metadata = {
                'name': filename
            }
            
            # Add parent folder if available
            if uploads_folder_id:
                file_metadata['parents'] = [uploads_folder_id]
                self.logger.info(f"Uploading '{filename}' to 'Uploads' folder")
            else:
                self.logger.info(f"Uploading '{filename}' to root folder")
            
            # Choose MIME based on extension
            ext = os.path.splitext(image_path)[1].lower()
            if ext in ('.jpg', '.jpeg'):
                mime = 'image/jpeg'
            elif ext == '.png':
                mime = 'image/png'
            else:
                mime = 'application/octet-stream'

            # Upload file
            media = MediaFileUpload(image_path, mimetype=mime)
            file = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            file_id = file.get('id')
            # Make the file publicly readable
            try:
                self.drive_service.permissions().create(
                    fileId=file_id,
                    body={
                        'type': 'anyone',
                        'role': 'reader'
                    }
                ).execute()
            except Exception as e:
                self.logger.warning(f"Could not set public permission for file {file_id}: {e}")

            public_url = f"https://drive.google.com/uc?export=view&id={file_id}"
            self.logger.info(f"Image uploaded to Drive (Uploads folder): {file_id}")
            return file_id, public_url
            
        except Exception as e:
            self.logger.error(f"Error uploading image to Drive: {e}")
            return None

    def replace_image_placeholder(self, presentation_id, placeholder_text, image_path, slide_id=None, crop_properties=None, target_dimensions=None):
        """Replace image placeholder with uploaded image
        
        Args:
            target_dimensions: Optional dict with 'width', 'height', 'unit' to override placeholder size
                              If provided, image element will use these dimensions instead of placeholder size
        """
        try:
            # Special handling for companyLogo - use exact replacement method
            if 'companylogo' in (placeholder_text or '').lower():
                self.logger.info("🔒 Detected companyLogo - using EXACT replacement method")
                return self.replace_company_logo_exact(presentation_id, placeholder_text, image_path, slide_id)
            
            # Special-case background image placeholders
            if 'backgroundimage' in (placeholder_text or '').lower():
                return self.replace_background_placeholder(presentation_id, placeholder_text, image_path, slide_id=slide_id)

            # Upload image to Drive
            result = self.upload_image_to_drive(image_path)
            if not result:
                return False
            file_id, public_url = result
            
            # Find ALL elements that contain the placeholder text BEFORE replacing
            presentation = self.get_presentation(presentation_id)
            if not presentation:
                return False
            
            # Collect all matching elements
            matching_elements = []
            
            for slide in presentation.get('slides', []):
                if slide_id and slide.get('objectId') != slide_id:
                    continue
                    
                for idx, element in enumerate(slide.get('pageElements', [])):
                    if 'shape' in element and element['shape'].get('text'):
                        text_content = ''
                        for text_element in element['shape']['text'].get('textElements', []):
                            if 'textRun' in text_element:
                                text_content += text_element['textRun'].get('content', '')
                        
                        if placeholder_text in text_content:
                            matching_elements.append({
                                'element_id': element.get('objectId'),
                                'slide_id': slide.get('objectId'),
                                'size': element.get('size') or (element.get('elementProperties', {}) or {}).get('size'),
                                'transform': element.get('transform') or (element.get('elementProperties', {}) or {}).get('transform'),
                                'z_order': idx
                            })
            
            if not matching_elements:
                self.logger.warning(f"No matching elements found for placeholder: {placeholder_text}")
                return False
            
            self.logger.info(f"Found {len(matching_elements)} occurrence(s) of placeholder: {placeholder_text}")
            
            # Process each matching element - process in reverse order to minimize z-index disruption
            # (elements at the end of array will be created first, which helps maintain relative ordering)
            all_requests = []
            image_element_ids = []  # Track newly created image IDs
            
            # Sort by z_order in reverse (process back-to-front)
            # This way, when new elements are added, they'll be closer to their original positions
            matching_elements_sorted = sorted(matching_elements, key=lambda x: x.get('z_order', 0), reverse=True)
            
            # Special handling for companyLogo: Always get placeholder dimensions first to ensure we never exceed them
            is_company_logo = 'companylogo' in placeholder_text.lower()
            
            for element_info in matching_elements_sorted:
                props = {
                    'pageObjectId': element_info['slide_id']
                }
                
                # For companyLogo: Always get placeholder dimensions first and use them as maximum bounds
                placeholder_max_width = None
                placeholder_max_height = None
                if is_company_logo and element_info['size']:
                    placeholder_size = element_info['size']
                    ph_width_raw = placeholder_size.get('width', {}).get('magnitude', 0)
                    ph_height_raw = placeholder_size.get('height', {}).get('magnitude', 0)
                    
                    # Convert EMU to PT if needed (values > 10000 are likely EMU)
                    if ph_width_raw > 10000 or ph_height_raw > 10000:
                        placeholder_max_width = float(ph_width_raw) / 914400 * 72
                        placeholder_max_height = float(ph_height_raw) / 914400 * 72
                    else:
                        placeholder_max_width = float(ph_width_raw)
                        placeholder_max_height = float(ph_height_raw)
                    
                    self.logger.info(f"🔒 companyLogo placeholder bounds: {placeholder_max_width}x{placeholder_max_height} PT (will not exceed these dimensions)")
                
                # Use target dimensions from MANUAL_CROP_DIMS if available, otherwise use placeholder size
                # The image is pre-cropped to match these exact dimensions in pixels
                # At 72 DPI: 1 pixel = 1 PT, so we set size to match the cropped image dimensions
                # IMPORTANT: Normalize transform scale to 1.0 to prevent enlargement (use transform only for position)
                if target_dimensions and target_dimensions.get('width') and target_dimensions.get('height'):
                    # Use target dimensions from MANUAL_CROP_DIMS (already in PT)
                    target_width = float(target_dimensions['width'])
                    target_height = float(target_dimensions['height'])
                    
                    # For companyLogo: Ensure dimensions never exceed placeholder bounds
                    if is_company_logo and placeholder_max_width and placeholder_max_height:
                        # Scale down if target dimensions exceed placeholder bounds while maintaining aspect ratio
                        if target_width > placeholder_max_width or target_height > placeholder_max_height:
                            scale_w = placeholder_max_width / target_width if target_width > 0 else 1.0
                            scale_h = placeholder_max_height / target_height if target_height > 0 else 1.0
                            scale = min(scale_w, scale_h)  # Use the smaller scale to fit within bounds
                            target_width = target_width * scale
                            target_height = target_height * scale
                            self.logger.info(f"🔒 companyLogo dimensions scaled down to fit within placeholder: {target_width}x{target_height} PT (from {target_dimensions['width']}x{target_dimensions['height']})")
                        # Ensure we use placeholder dimensions as the maximum (never exceed)
                        target_width = min(target_width, placeholder_max_width)
                        target_height = min(target_height, placeholder_max_height)
                        self.logger.info(f"🔒 companyLogo final dimensions (clamped to placeholder): {target_width}x{target_height} PT")
                    
                    # Validate dimensions are reasonable (reject if > 1000 PT or <= 0)
                    if target_width > 0 and target_height > 0 and target_width < 1000 and target_height < 1000:
                        props['size'] = {
                            'width': {'magnitude': target_width, 'unit': target_dimensions.get('unit', 'PT')},
                            'height': {'magnitude': target_height, 'unit': target_dimensions.get('unit', 'PT')}
                        }
                        # CRITICAL: Preserve exact position from original placeholder, only normalize scale
                        # This ensures the image appears in the exact same position as the placeholder
                        if element_info['transform']:
                            # Deep copy transform to preserve all position values
                            transform = copy.deepcopy(element_info['transform'])
                            # Preserve ALL position and rotation values (translateX, translateY, unit, etc.)
                            # Only normalize scale to prevent enlargement/shrinking - DO NOT change position!
                            original_scaleX = transform.get('scaleX', 1.0)
                            original_scaleY = transform.get('scaleY', 1.0)
                            transform['scaleX'] = 1.0
                            transform['scaleY'] = 1.0
                            props['transform'] = transform
                            # Log position details for debugging
                            pos_info = f"translateX={transform.get('translateX')}, translateY={transform.get('translateY')}"
                            if 'unit' in transform:
                                pos_info += f", unit={transform.get('unit')}"
                            if 'rotate' in transform:
                                pos_info += f", rotate={transform.get('rotate')}"
                            self.logger.debug(f"Preserving position from placeholder: {pos_info} (scale changed from {original_scaleX}x{original_scaleY} to 1.0x1.0)")
                            if 'logo' in placeholder_text.lower():
                                self.logger.info(f"📍 Logo position preserved: {pos_info}")
                        else:
                            # If no transform, the position is already set by the element's default position
                            self.logger.warning(f"⚠️ No transform found for placeholder {placeholder_text} - position may not be preserved correctly!")
                        # Special logging for logos to confirm exact fit
                        if is_company_logo:
                            self.logger.info(f"✅ companyLogo placeholder: Using EXACT dimensions {target_width}x{target_height} PT (within placeholder bounds) with normalized transform scale (1.0)")
                        elif 'logo' in placeholder_text.lower():
                            self.logger.info(f"✅ Logo placeholder {placeholder_text}: Using EXACT dimensions {target_width}x{target_height} {target_dimensions.get('unit', 'PT')} with normalized transform scale (1.0)")
                        else:
                            self.logger.info(f"Using target dimensions: {target_width}x{target_height} {target_dimensions.get('unit', 'PT')} with normalized transform scale (1.0) for {placeholder_text}")
                    else:
                        self.logger.warning(f"Invalid target dimensions for {placeholder_text}: {target_width}x{target_height} PT, falling back to placeholder size")
                        # Fall through to use placeholder size
                        target_dimensions = None
                elif element_info['size']:
                    # Fallback: Use placeholder size and normalize transform scale
                    placeholder_size = element_info['size']
                    ph_width_raw = placeholder_size.get('width', {}).get('magnitude', 0)
                    ph_height_raw = placeholder_size.get('height', {}).get('magnitude', 0)
                    
                    # Convert EMU to PT if needed (values > 10000 are likely EMU)
                    if ph_width_raw > 10000 or ph_height_raw > 10000:
                        ph_width = float(ph_width_raw) / 914400 * 72
                        ph_height = float(ph_height_raw) / 914400 * 72
                        self.logger.debug(f"Converted placeholder size from EMU to PT: {ph_width}x{ph_height}")
                        # Use converted values
                        props['size'] = {
                            'width': {'magnitude': ph_width, 'unit': 'PT'},
                            'height': {'magnitude': ph_height, 'unit': 'PT'}
                        }
                    else:
                        # Use as-is (assume PT)
                        props['size'] = placeholder_size
                        ph_width = ph_width_raw
                        ph_height = ph_height_raw
                    
                    # For companyLogo: Ensure we're using exact placeholder dimensions (already set above)
                    if is_company_logo:
                        self.logger.info(f"🔒 companyLogo using exact placeholder dimensions: {ph_width}x{ph_height} PT (will not exceed)")
                    
                    # CRITICAL: Preserve exact position from original placeholder, only normalize scale
                    # This ensures the image appears in the exact same position as the placeholder
                    if element_info['transform']:
                        # Deep copy transform to preserve all position values
                        transform = copy.deepcopy(element_info['transform'])
                        # Preserve ALL position and rotation values (translateX, translateY, unit, etc.)
                        # Only normalize scale to prevent enlargement/shrinking - DO NOT change position!
                        original_scaleX = transform.get('scaleX', 1.0)
                        original_scaleY = transform.get('scaleY', 1.0)
                        transform['scaleX'] = 1.0
                        transform['scaleY'] = 1.0
                        props['transform'] = transform
                        # Log position details for debugging
                        pos_info = f"translateX={transform.get('translateX')}, translateY={transform.get('translateY')}"
                        if 'unit' in transform:
                            pos_info += f", unit={transform.get('unit')}"
                        if 'rotate' in transform:
                            pos_info += f", rotate={transform.get('rotate')}"
                        self.logger.debug(f"Preserving position from placeholder: {pos_info} (scale changed from {original_scaleX}x{original_scaleY} to 1.0x1.0)")
                        if 'logo' in placeholder_text.lower():
                            self.logger.info(f"📍 Logo position preserved: {pos_info}")
                    else:
                        self.logger.warning(f"⚠️ No transform found for placeholder {placeholder_text} - position may not be preserved correctly!")
                    if is_company_logo:
                        self.logger.info(f"✅ companyLogo placeholder: Using EXACT placeholder dimensions {ph_width}x{ph_height} PT with normalized transform scale (1.0)")
                    else:
                        self.logger.info(f"Using placeholder size: {ph_width}x{ph_height} PT with normalized transform scale (1.0) for {placeholder_text}")
                elif element_info['transform']:
                    # Only transform available - preserve position, normalize scale to 1.0
                    # For companyLogo: Warn if size is not available as we cannot ensure exact fit
                    if is_company_logo:
                        self.logger.warning(f"⚠️ companyLogo: No size information available, cannot guarantee exact fit within placeholder bounds")
                    # Deep copy transform to preserve all position values
                    transform = copy.deepcopy(element_info['transform'])
                    # Preserve ALL position and rotation values (translateX, translateY, unit, etc.)
                    # Only normalize scale to prevent enlargement/shrinking - DO NOT change position!
                    original_scaleX = transform.get('scaleX', 1.0)
                    original_scaleY = transform.get('scaleY', 1.0)
                    transform['scaleX'] = 1.0
                    transform['scaleY'] = 1.0
                    props['transform'] = transform
                    # Log position details for debugging
                    pos_info = f"translateX={transform.get('translateX')}, translateY={transform.get('translateY')}"
                    if 'unit' in transform:
                        pos_info += f", unit={transform.get('unit')}"
                    if 'rotate' in transform:
                        pos_info += f", rotate={transform.get('rotate')}"
                    self.logger.debug(f"Preserving position from placeholder: {pos_info} (scale changed from {original_scaleX}x{original_scaleY} to 1.0x1.0)")
                    if 'logo' in placeholder_text.lower():
                        self.logger.info(f"📍 Logo position preserved: {pos_info}")
                
                # Store original z-order
                original_z_order = element_info.get('z_order', 0)
                
                # Create requests to delete text element and create image element
                delete_request = {
                    'deleteObject': {
                        'objectId': element_info['element_id']
                    }
                }
                
                create_request = {
                    'createImage': {
                        'url': public_url,
                        'elementProperties': props
                    }
                }
                
                all_requests.append(delete_request)
                all_requests.append(create_request)
                
                # Store info for reordering after creation
                image_element_ids.append({
                    'slide_id': element_info['slide_id'],
                    'original_z_order': original_z_order,
                    'element_id_placeholder': f'_created_image_{len(image_element_ids)}'
                })
            
            # Execute all requests in one batch to get created element IDs
            if all_requests:
                response = self.service.presentations().batchUpdate(
                    presentationId=presentation_id,
                    body={'requests': all_requests}
                ).execute()
                
                # Get the IDs of newly created image elements from response
                created_ids = []
                if response.get('replies'):
                    image_index = 0
                    for reply in response.get('replies', []):
                        if 'createImage' in reply:
                            created_id = reply['createImage'].get('objectId')
                            if created_id and image_index < len(matching_elements):
                                created_ids.append({
                                    'id': created_id,
                                    'slide_id': matching_elements[image_index]['slide_id'],
                                    'original_z_order': matching_elements[image_index].get('z_order', 0)
                                })
                                image_index += 1
                
                # Note: Images are now pre-cropped before upload, so no API crop needed
                # Crop properties are None and images are already the correct size
                if crop_properties:
                    self.logger.debug(f"Crop properties provided but unused (images are pre-cropped): {crop_properties}")

                # Z-order handling note
                if created_ids:
                    self.logger.info(
                        "Note: Google Slides REST API does not support z-index reordering. "
                        "Newly created elements may appear on top. To ensure items are behind, "
                        "design the template with background shapes or set as slide background."
                    )
                
                self.logger.info(f"Successfully converted {len(matching_elements)} placeholder(s) to image(s)")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error replacing image placeholder: {e}")
            return False

    def replace_background_placeholder(self, presentation_id, placeholder_text, image_path, slide_id=None, target_dimensions=None):
        """Replace a background placeholder by setting the slide background and removing the placeholder shape.
        
        Args:
            presentation_id: The presentation ID
            placeholder_text: The placeholder text to find
            image_path: Path to the image file (should already be cropped/resized to exact slide dimensions)
            slide_id: Optional specific slide ID
            target_dimensions: Optional dict with 'width', 'height', 'unit' - if not provided, will use slide page size
        """
        try:
            # Find placeholder location (slide + element) and get slide page size
            presentation = self.get_presentation(presentation_id)
            if not presentation:
                return False

            # Get actual slide page size from presentation
            page_size = presentation.get('pageSize', {})
            slide_width_emu = page_size.get('width', {}).get('magnitude', 9144000)  # Default: 10 inches in EMU
            slide_height_emu = page_size.get('height', {}).get('magnitude', 5143500)  # Default: 5.625 inches in EMU
            
            # Convert EMU to PT (1 inch = 914400 EMU = 72 PT)
            slide_width_pt = (slide_width_emu / 914400.0) * 72.0
            slide_height_pt = (slide_height_emu / 914400.0) * 72.0
            
            self.logger.info(f"Slide page size: {slide_width_pt:.2f} x {slide_height_pt:.2f} PT (from EMU: {slide_width_emu} x {slide_height_emu})")
            
            # Use target_dimensions if provided, otherwise use slide page size
            if target_dimensions:
                target_width = float(target_dimensions.get('width', slide_width_pt))
                target_height = float(target_dimensions.get('height', slide_height_pt))
                unit = target_dimensions.get('unit', 'PT').upper()
                if unit in ('IN', 'INCH', 'INCHES'):
                    target_width = target_width * 72.0
                    target_height = target_height * 72.0
            else:
                target_width = slide_width_pt
                target_height = slide_height_pt

            target_slide_id = slide_id
            target_element_id = None

            for slide in presentation.get('slides', []):
                if target_slide_id and slide.get('objectId') != target_slide_id:
                    continue
                for element in slide.get('pageElements', []):
                    if 'shape' in element and element['shape'].get('text'):
                        text_content = ''
                        for text_element in element['shape']['text'].get('textElements', []):
                            if 'textRun' in text_element:
                                text_content += text_element['textRun'].get('content', '')
                        if placeholder_text in text_content:
                            target_slide_id = slide.get('objectId')
                            target_element_id = element.get('objectId')
                            break
                if target_slide_id and target_element_id:
                    break

            if not target_slide_id:
                self.logger.warning("Background slide not found for placeholder")
                return False

            # Upload image to Drive (image should already be cropped/resized to exact dimensions)
            result = self.upload_image_to_drive(image_path)
            if not result:
                return False
            file_id, public_url = result

            # Build requests: set slide background, then delete placeholder shape if found
            requests = [
                {
                    'updatePageProperties': {
                        'objectId': target_slide_id,
                        'pageProperties': {
                            'pageBackgroundFill': {
                                'stretchedPictureFill': {
                                    'contentUrl': public_url
                                }
                            }
                        },
                        'fields': 'pageBackgroundFill'
                    }
                }
            ]

            if target_element_id:
                requests.append({
                    'deleteObject': {
                        'objectId': target_element_id
                    }
                })
                self.logger.warning(
                    "⚠️ Background placeholder element deleted - this may affect z-index (element order) "
                    "for other elements on this slide. Background is now set at slide level."
                )

            self.batch_update_requests(presentation_id, requests)
            self.logger.info(f"Slide background updated from placeholder (image dimensions should match slide: {target_width:.2f}x{target_height:.2f} PT)")
            return True
        except Exception as e:
            self.logger.error(f"Error replacing background placeholder: {e}")
            return False

    def replace_company_logo_exact(self, presentation_id, placeholder_text, image_path, slide_id=None):
        """Replace companyLogo placeholder with EXACT dimensions from template
        
        This method ensures the logo fits EXACTLY within the placeholder bounds,
        preserving the exact position, width, and height from the template.
        
        Args:
            presentation_id: The presentation ID
            placeholder_text: The placeholder text (e.g., "{{companyLogo}}")
            image_path: Path to the logo image file
            slide_id: Optional slide ID to search in
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.logger.info(f"🔒 EXACT LOGO REPLACEMENT: Starting for {placeholder_text}")
            
            # Upload image to Drive
            result = self.upload_image_to_drive(image_path)
            if not result:
                self.logger.error("❌ Failed to upload logo to Drive")
                return False
            file_id, public_url = result
            
            # Get current presentation state
            presentation = self.get_presentation(presentation_id)
            if not presentation:
                self.logger.error("❌ Failed to get presentation")
                return False
            
            # Find the companyLogo placeholder
            logo_element = None
            logo_slide_id = None
            
            for slide in presentation.get('slides', []):
                if slide_id and slide.get('objectId') != slide_id:
                    continue
                    
                for element in slide.get('pageElements', []):
                    if 'shape' in element and element['shape'].get('text'):
                        text_content = ''
                        for text_element in element['shape']['text'].get('textElements', []):
                            if 'textRun' in text_element:
                                text_content += text_element['textRun'].get('content', '')
                        
                        if placeholder_text in text_content:
                            logo_element = element
                            logo_slide_id = slide.get('objectId')
                            break
                
                if logo_element:
                    break
            
            if not logo_element:
                self.logger.error(f"❌ companyLogo placeholder not found: {placeholder_text}")
                return False
            
            # Extract EXACT dimensions and position from placeholder
            element_id = logo_element.get('objectId')
            element_props = logo_element.get('elementProperties', {}) or {}
            
            # Get size - prefer top-level, then elementProperties
            size = logo_element.get('size') or element_props.get('size')
            if not size:
                self.logger.error("❌ No size information found for companyLogo placeholder")
                return False
            
            # Get transform for position - prefer top-level, then elementProperties
            transform = logo_element.get('transform') or element_props.get('transform')
            
            # Extract exact dimensions in PT
            width_info = size.get('width', {})
            height_info = size.get('height', {})
            
            width_magnitude = width_info.get('magnitude', 0)
            height_magnitude = height_info.get('magnitude', 0)
            unit = width_info.get('unit', 'PT')
            
            # Convert EMU to PT if needed (1 inch = 914400 EMU = 72 PT)
            if width_magnitude > 10000 or height_magnitude > 10000:
                # Likely EMU, convert to PT
                exact_width = float(width_magnitude) / 914400 * 72
                exact_height = float(height_magnitude) / 914400 * 72
                unit = 'PT'
                self.logger.info(f"📐 Converted dimensions from EMU to PT: {exact_width:.2f}x{exact_height:.2f}")
            else:
                exact_width = float(width_magnitude)
                exact_height = float(height_magnitude)
            
            self.logger.info(f"📐 EXACT placeholder dimensions: {exact_width:.2f}x{exact_height:.2f} {unit}")
            
            # Extract exact position from transform
            exact_position = {
                'scaleX': 1.0,  # Force scale to 1.0 for exact sizing
                'scaleY': 1.0,
            }
            
            if transform:
                # Copy position but force scale to 1.0
                exact_position.update({
                    'translateX': transform.get('translateX'),
                    'translateY': transform.get('translateY'),
                    'unit': transform.get('unit', 'PT')
                })
                
                # Preserve any rotation/shear if present
                if 'shearX' in transform:
                    exact_position['shearX'] = transform['shearX']
                if 'shearY' in transform:
                    exact_position['shearY'] = transform['shearY']
                if 'rotate' in transform:
                    exact_position['rotate'] = transform.get('rotate')
                
                self.logger.info(f"📍 EXACT position: translateX={exact_position.get('translateX')}, translateY={exact_position.get('translateY')}")
            else:
                self.logger.warning("⚠️ No transform found for companyLogo placeholder - using default position")
            
            # Create the new image element with EXACT dimensions
            create_request = {
                'createImage': {
                    'url': public_url,
                    'elementProperties': {
                        'pageObjectId': logo_slide_id,
                        'size': {
                            'width': {'magnitude': exact_width, 'unit': unit},
                            'height': {'magnitude': exact_height, 'unit': unit}
                        },
                        'transform': exact_position
                    }
                }
            }
            
            # Build requests: delete old placeholder, create new image
            requests = [
                {
                    'deleteObject': {
                        'objectId': element_id
                    }
                },
                create_request
            ]
            
            # Execute requests
            response = self.service.presentations().batchUpdate(
                presentationId=presentation_id,
                body={'requests': requests}
            ).execute()
            
            # Verify the created image
            if response.get('replies'):
                for reply in response.get('replies', []):
                    if 'createImage' in reply:
                        created_id = reply['createImage'].get('objectId')
                        self.logger.info(f"✅ EXACT LOGO REPLACEMENT SUCCESSFUL")
                        self.logger.info(f"   📐 Dimensions: {exact_width:.2f}x{exact_height:.2f} {unit}")
                        self.logger.info(f"   📍 Position preserved from template")
                        self.logger.info(f"   🆔 New Element ID: {created_id}")
                        return True
            
            self.logger.warning("⚠️ Logo created but couldn't verify dimensions")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error in exact logo replacement: {e}")
            import traceback
            traceback.print_exc()
            return False

    def replace_color_placeholder(self, presentation_id, placeholder_text, color, slide_id=None):
        """Replace color placeholder by filling the shape with solid color"""
        try:
            # Find the placeholder element
            presentation = self.service.presentations().get(presentationId=presentation_id).execute()
            target_element_id = None
            target_slide_id = slide_id
            
            # Search through slides for the placeholder
            for slide in presentation.get('slides', []):
                if target_slide_id and slide.get('objectId') != target_slide_id:
                    continue
                    
                for element in slide.get('pageElements', []):
                    if 'shape' in element and 'text' in element['shape']:
                        text_content = element['shape']['text'].get('textElements', [])
                        full_text = ''.join([
                            text_elem.get('textRun', {}).get('content', '') 
                            for text_elem in text_content 
                            if 'textRun' in text_elem
                        ])
                        
                        if placeholder_text in full_text:
                            target_element_id = element.get('objectId')
                            target_slide_id = slide.get('objectId')
                            break
                
                if target_element_id:
                    break
            
            if not target_element_id:
                self.logger.warning(f"Color placeholder {placeholder_text} not found")
                return False
            
            # Convert hex color to RGB
            rgb_color = self._hex_to_rgb(color)
            
            # Create request to fill the shape with solid color
            requests = [{
                'updateShapeProperties': {
                    'objectId': target_element_id,
                    'shapeProperties': {
                        'shapeBackgroundFill': {
                            'solidFill': {
                                'color': {
                                    'rgbColor': rgb_color
                                }
                            }
                        }
                    },
                    'fields': 'shapeBackgroundFill'
                }
            }]
            
            # Also remove the placeholder text
            requests.append({
                'deleteText': {
                    'objectId': target_element_id,
                    'textRange': {
                        'type': 'ALL'
                    }
                }
            })
            
            self.batch_update_requests(presentation_id, requests)
            self.logger.info(f"Successfully filled color placeholder {placeholder_text} with color {color}")
            
            # Note: Slides API doesn't support programmatic z-order changes (send to back/front).
            # Ensure circles intended as backgrounds are set as backgrounds in the template.
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error replacing color placeholder {placeholder_text}: {e}")
            return False

    def _hex_to_rgb(self, hex_color):
        """Convert hex color to RGB values for Google Slides API"""
        hex_color = hex_color.lstrip('#')
        return {
            'red': int(hex_color[0:2], 16) / 255.0,
            'green': int(hex_color[2:4], 16) / 255.0,
            'blue': int(hex_color[4:6], 16) / 255.0
        }
