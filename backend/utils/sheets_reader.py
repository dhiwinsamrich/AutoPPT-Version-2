"""
Google Sheets Reader for PPT Automation
Fetches placeholder values from Google Sheets
"""
from typing import Dict, Optional, List
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from utils.logger import get_logger
from utils.project_analyzer import ProjectAnalyzer
from config import (
    GOOGLE_SHEETS_ID,
    GOOGLE_SHEETS_RANGE,
    LOG_LEVEL,
    LOG_FILE,
    SHEET_LINKED_PLACEHOLDERS,
)


def extract_sheet_id(sheet_id_or_url: Optional[str]) -> Optional[str]:
    """
    Extract Google Sheet ID from a plain ID or a full Sheets URL.
    
    Supports formats like:
    - Plain ID: "1abc123..."
    - Full URL: "https://docs.google.com/spreadsheets/d/1abc123.../edit"
    - URL with gid: "https://docs.google.com/spreadsheets/d/1abc123.../edit#gid=0"
    """
    if not sheet_id_or_url:
        return None
    
    value = str(sheet_id_or_url).strip()
    
    # If it looks like a full URL, try to extract the /d/<ID>/ segment
    if value.startswith('http://') or value.startswith('https://'):
        # Typical format: https://docs.google.com/spreadsheets/d/<ID>/edit
        parts = value.split('/d/')
        if len(parts) > 1:
            tail = parts[1]
            # Remove everything after the ID (like /edit, #gid=, etc.)
            file_id = tail.split('/')[0].split('#')[0].split('?')[0]
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
    
    # Return as-is if it's already a plain ID
    return value


def extract_gid_from_url(url: Optional[str]) -> Optional[int]:
    """
    Extract GID (sheet tab ID) from Google Sheets URL.
    
    Example: https://docs.google.com/spreadsheets/d/ID/edit#gid=1751820002
    Returns: 1751820002
    """
    if not url:
        return None
    
    try:
        if '#gid=' in url:
            gid_str = url.split('#gid=')[1].split('&')[0].split('#')[0]
            return int(gid_str)
    except (ValueError, IndexError):
        pass
    
    return None


class SheetsReader:
    def __init__(self, credentials):
        """Initialize with the same credentials used for Slides API
        
        Works with both OAuth and Service Account credentials.
        OAuth credentials use the logged-in user's permissions.
        Service Account credentials require the sheet to be shared with the service account email.
        """
        self.logger = get_logger(__name__, LOG_LEVEL, LOG_FILE)
        
        # Detect credential type for logging
        from google.oauth2.credentials import Credentials as UserCredentials
        from google.oauth2 import service_account
        
        if isinstance(credentials, UserCredentials):
            auth_type = "OAuth (User Account)"
            self.logger.info(f"🔐 Using OAuth credentials - will use your Google account permissions")
        elif isinstance(credentials, service_account.Credentials):
            auth_type = "Service Account"
            service_account_email = getattr(credentials, 'service_account_email', 'unknown')
            self.logger.info(f"🔐 Using Service Account credentials: {service_account_email}")
            self.logger.info(f"   Make sure the Google Sheet is shared with: {service_account_email}")
        else:
            auth_type = "Unknown"
            self.logger.warning(f"⚠️ Unknown credential type: {type(credentials)}")
        
        self.service = build('sheets', 'v4', credentials=credentials)
        # Also build Drive service for alternative access methods
        try:
            self.drive_service = build('drive', 'v3', credentials=credentials)
            self.logger.debug(f"✅ Drive service initialized ({auth_type})")
        except Exception as e:
            self.logger.warning(f"⚠️ Could not initialize Drive service: {e}")
            self.drive_service = None
        self.sheets_id = GOOGLE_SHEETS_ID
        self.sheets_range = GOOGLE_SHEETS_RANGE
        self.linked_placeholders = SHEET_LINKED_PLACEHOLDERS
        self.cache: Dict[str, Dict[str, str]] = {}
        
        # Initialize Gemini AI analyzer
        self.logger.info("🔧 Initializing ProjectAnalyzer with Gemini AI...")
        try:
            self.project_analyzer = ProjectAnalyzer()
            if self.project_analyzer.gemini_available:
                self.logger.info("✅ ProjectAnalyzer initialized successfully - Gemini AI is available")
            else:
                self.logger.warning("⚠️ ProjectAnalyzer initialized but Gemini AI is not available")
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize ProjectAnalyzer: {e}")
            import traceback
            traceback.print_exc()
            self.project_analyzer = None

    def fetch_placeholder_values(self, sheets_id: Optional[str] = None, sheets_range: Optional[str] = None, sheet_names: Optional[List[str]] = None) -> Dict[str, str]:
        """
        Fetch all placeholder values from Google Sheets and analyze with Gemini AI

        This method:
        1. Reads data from multiple sheets (default: "Effort Estimation" and "Investment Breakup")
        2. Combines all sheet data
        3. Sends combined data to Gemini AI for analysis
        4. Returns analyzed placeholder values (p_r_1-3, s_r_1-3, days, p_b, d_b, d_v, d_p)

        Args:
            sheets_id: Sheet ID or full URL (will extract ID automatically)
            sheets_range: Single sheet name like "Sheet1" (optional, overridden by sheet_names)
            sheet_names: List of sheet names to analyze (e.g., ["Effort Estimation", "Investment Breakup"])
                        If None, defaults to ["Effort Estimation", "Investment Breakup"]

        Returns:
            dict: {placeholder_name: value} including Gemini-analyzed values
        """
        try:
            # Extract ID from URL if provided
            raw_sheets_id = sheets_id or self.sheets_id
            extracted_sheets_id = extract_sheet_id(raw_sheets_id) if raw_sheets_id else None
            
            # Also extract GID if present in URL (for direct sheet tab access)
            gid = extract_gid_from_url(raw_sheets_id) if raw_sheets_id else None
            if gid:
                self.logger.info(f"📋 Found GID in URL: {gid}")
            
            sheets_id = extracted_sheets_id
            if not sheets_id:
                self.logger.warning("No Google Sheets ID configured")
                return {}

            # Validate that the file is actually a Google Sheet (not Excel/other format)
            if self.drive_service:
                try:
                    file_info = self.drive_service.files().get(
                        fileId=sheets_id,
                        fields='name,mimeType'
                    ).execute()
                    
                    mime_type = file_info.get('mimeType', 'unknown')
                    file_name = file_info.get('name', 'unknown')
                    
                    self.logger.info(f"📄 File: {file_name}")
                    self.logger.info(f"📄 MIME type: {mime_type}")
                    
                    # Check if it's a native Google Sheet
                    if mime_type == 'application/vnd.google-apps.spreadsheet':
                        self.logger.info("✅ Confirmed: This is a native Google Sheet - API access should work")
                    elif 'spreadsheet' in mime_type.lower() and 'google-apps' in mime_type:
                        self.logger.info("✅ Confirmed: This is a Google Sheet - API access should work")
                    else:
                        self.logger.error(f"❌ WARNING: This file is NOT a native Google Sheet!")
                        self.logger.error(f"   MIME type: {mime_type}")
                        self.logger.error(f"   Expected: application/vnd.google-apps.spreadsheet")
                        self.logger.error("")
                        self.logger.error("🔧 SOLUTION:")
                        self.logger.error("   1. Open the file in Google Drive")
                        self.logger.error("   2. Go to File → Save as Google Sheets")
                        self.logger.error("   3. Use the NEW Google Sheet ID/URL")
                        self.logger.error("")
                        return {}  # Don't proceed if it's not a Google Sheet
                except Exception as e:
                    self.logger.warning(f"⚠️ Could not verify file type: {e}")
                    self.logger.info("   Proceeding anyway - will attempt to read the sheet")

            # Determine which sheets to analyze
            # Priority: sheet_names parameter > sheets_range > default sheets
            sheets_to_read = []
            
            # Try to get spreadsheet metadata first (optional - if it fails, we'll use defaults)
            available_sheet_names = []
            try:
                spreadsheet_metadata = self.service.spreadsheets().get(
                    spreadsheetId=sheets_id
                ).execute()
                
                sheets_info = spreadsheet_metadata.get('sheets', [])
                available_sheet_names = [sheet['properties']['title'] for sheet in sheets_info]
                self.logger.info(f"📋 Available sheets in spreadsheet: {available_sheet_names}")
            except HttpError as e:
                self.logger.warning(f"⚠️ Could not get spreadsheet metadata (this is OK): {e}")
                self.logger.info("📋 Will try reading sheets directly using known names")
            
            # ALWAYS analyze both "Effort Estimation" and "Investment Breakup" regardless of sheets_range
            # sheets_range is ignored - we always want both sheets for complete analysis
            default_sheets = ["Effort Estimation", "Investment Breakup"]
            
            if available_sheet_names:
                # Verify which default sheets exist
                sheets_to_read = [name for name in default_sheets if name in available_sheet_names]
                if len(sheets_to_read) < len(default_sheets):
                    missing = [name for name in default_sheets if name not in available_sheet_names]
                    self.logger.warning(f"⚠️ Some default sheets not found: {missing}")
                    if not sheets_to_read:
                        # If neither default sheet exists, try first available
                        if available_sheet_names:
                            sheets_to_read = [available_sheet_names[0]]
                            self.logger.warning(f"⚠️ Default sheets not found, using first available: {sheets_to_read[0]}")
            else:
                # Metadata not available, try default names directly
                sheets_to_read = default_sheets
                self.logger.info(f"📋 Will try reading default sheets directly: {sheets_to_read}")
            
            # If sheet_names parameter is explicitly provided, use that instead
            if sheet_names:
                if available_sheet_names:
                    sheets_to_read = [name for name in sheet_names if name in available_sheet_names]
                    if len(sheets_to_read) < len(sheet_names):
                        missing = [name for name in sheet_names if name not in available_sheet_names]
                        self.logger.warning(f"⚠️ Some specified sheets not found: {missing}")
                else:
                    sheets_to_read = sheet_names
                    self.logger.info(f"📋 Will try reading specified sheets directly: {sheets_to_read}")
            
            if not sheets_to_read:
                self.logger.error("❌ No valid sheets found to read")
                return {}
            
            self.logger.info(f"📊 Will analyze {len(sheets_to_read)} sheet(s): {sheets_to_read}")

            # Cache key based on sheets being read
            cache_key = f"{sheets_id}:{','.join(sheets_to_read)}"
            if cache_key in self.cache:
                self.logger.debug("Using cached sheet data")
                return self.cache[cache_key]

            # Read data from all specified sheets and combine
            all_values = []
            for sheet_name in sheets_to_read:
                self.logger.info(f"📥 Fetching data from sheet: '{sheet_name}'")
                sheet_read_success = False
                
                # Try multiple range formats
                # For sheet names with spaces, we need to quote them
                if ' ' in sheet_name or '-' in sheet_name:
                    quoted_name = f"'{sheet_name}'"
                else:
                    quoted_name = sheet_name
                
                range_formats = [
                    f"{quoted_name}!A1:ZZ1000",  # Quoted sheet name with range
                    f"{sheet_name}!A1:ZZ1000",  # Unquoted (might work for some)
                    quoted_name,  # Just quoted sheet name
                    sheet_name,  # Just sheet name
                ]
                
                for range_format in range_formats:
                    try:
                        self.logger.debug(f"🔄 Trying range format: {range_format}")
                        result = self.service.spreadsheets().values().get(
                            spreadsheetId=sheets_id,
                            range=range_format,
                        ).execute()
                        
                        sheet_values = result.get('values', [])
                        if sheet_values:
                            # Add a header row to identify which sheet this data is from
                            all_values.append([f"=== DATA FROM SHEET: {sheet_name} ==="])
                            all_values.extend(sheet_values)
                            self.logger.info(f"✅ Read {len(sheet_values)} rows from '{sheet_name}' using range: {range_format}")
                            sheet_read_success = True
                            break
                        else:
                            self.logger.warning(f"⚠️ No data found in sheet '{sheet_name}' with range: {range_format}")
                            
                    except HttpError as e:
                        error_msg = str(e)
                        error_code = e.resp.status if hasattr(e, 'resp') else None
                        last_error = e
                        
                        if "not supported" in error_msg.lower() or error_code == 400:
                            self.logger.error(f"❌ ERROR: Cannot read sheet '{sheet_name}'")
                            self.logger.error(f"   Error message: {error_msg}")
                            self.logger.error(f"   Error code: {error_code}")
                            self.logger.error("")
                            self.logger.error("🔍 TROUBLESHOOTING:")
                            self.logger.error("   1. Ensure the Google Sheet is a REGULAR spreadsheet (not a Form response sheet)")
                            self.logger.error("   2. Verify the sheet is shared with your Google account/service account")
                            self.logger.error("   3. Check that the sheet name is exactly: 'Effort Estimation' or 'Investment Breakup'")
                            self.logger.error("   4. Try opening the sheet in browser and verify it's accessible")
                            self.logger.error("   5. If it's a Form response sheet, create a copy as a regular sheet")
                            self.logger.error("")
                            
                            # Try to get document info to help diagnose
                            if self.drive_service:
                                try:
                                    file_info = self.drive_service.files().get(
                                        fileId=sheets_id,
                                        fields='name,mimeType,capabilities'
                                    ).execute()
                                    mime_type = file_info.get('mimeType', 'unknown')
                                    self.logger.info(f"📄 Document type: {mime_type}")
                                    if 'spreadsheet' not in mime_type.lower():
                                        self.logger.error(f"❌ Document is not a Google Sheet! Type: {mime_type}")
                                except Exception as drive_error:
                                    self.logger.debug(f"Could not get file info: {drive_error}")
                        else:
                            self.logger.debug(f"⚠️ Range format '{range_format}' failed: {e}")
                        continue
                    except Exception as e:
                        self.logger.debug(f"⚠️ Unexpected error with range '{range_format}': {e}")
                        continue
                
                if not sheet_read_success:
                    self.logger.warning(f"⚠️ Standard Sheets API failed for '{sheet_name}', trying alternative methods...")
                    
                    # Method 1: Try batchGet API
                    try:
                        self.logger.info(f"🔄 Method 1: Trying batchGet API for '{sheet_name}'")
                        batch_result = self.service.spreadsheets().values().batchGet(
                            spreadsheetId=sheets_id,
                            ranges=[f"'{sheet_name}'!A1:ZZ1000", f"{sheet_name}!A1:ZZ1000"],
                        ).execute()
                        
                        value_ranges = batch_result.get('valueRanges', [])
                        for value_range in value_ranges:
                            sheet_values = value_range.get('values', [])
                            if sheet_values:
                                all_values.append([f"=== DATA FROM SHEET: {sheet_name} ==="])
                                all_values.extend(sheet_values)
                                self.logger.info(f"✅ Successfully read {len(sheet_values)} rows using batchGet API")
                                sheet_read_success = True
                                break
                    except Exception as batch_error:
                        self.logger.debug(f"batchGet API failed: {batch_error}")
                    
                    # Method 2: Try using get() with includeGridData (sometimes works for restricted sheets)
                    if not sheet_read_success:
                        try:
                            self.logger.info(f"🔄 Method 2: Trying get() with includeGridData for '{sheet_name}'")
                            
                            # Try to get the sheet by name using get() method
                            # This sometimes works when values().get() doesn't
                            spreadsheet = self.service.spreadsheets().get(
                                spreadsheetId=sheets_id,
                                ranges=[f"'{sheet_name}'!A1:ZZ1000"],
                                includeGridData=True
                            ).execute()
                            
                            # Extract data from the response
                            sheets = spreadsheet.get('sheets', [])
                            for sheet in sheets:
                                sheet_props = sheet.get('properties', {})
                                if sheet_props.get('title') == sheet_name:
                                    data = sheet.get('data', [])
                                    if data:
                                        rows = data[0].get('rowData', [])
                                        sheet_values = []
                                        for row in rows:
                                            row_values = []
                                            for cell in row.get('values', []):
                                                # Get cell value
                                                cell_value = cell.get('userEnteredValue', {})
                                                if 'stringValue' in cell_value:
                                                    row_values.append(cell_value['stringValue'])
                                                elif 'numberValue' in cell_value:
                                                    row_values.append(str(cell_value['numberValue']))
                                                elif 'formulaValue' in cell_value:
                                                    row_values.append(cell_value['formulaValue'])
                                                else:
                                                    row_values.append('')
                                            if row_values:
                                                sheet_values.append(row_values)
                                        
                                        if sheet_values:
                                            all_values.append([f"=== DATA FROM SHEET: {sheet_name} ==="])
                                            all_values.extend(sheet_values)
                                            self.logger.info(f"✅ Successfully read {len(sheet_values)} rows using get() with includeGridData")
                                            sheet_read_success = True
                                            break
                        except Exception as get_error:
                            error_msg = str(get_error)
                            if "not supported" not in error_msg.lower():
                                self.logger.debug(f"get() with includeGridData failed: {get_error}")
                    
                    # Method 3: Try Drive API export as CSV (last resort)
                    if not sheet_read_success and self.drive_service:
                        try:
                            self.logger.info(f"🔄 Method 3: Trying Drive API CSV export (exports all sheets)")
                            
                            # Export entire spreadsheet as CSV
                            # Note: This exports all sheets, we'll need to identify which rows belong to which sheet
                            from googleapiclient.http import MediaIoBaseDownload
                            import io
                            
                            request = self.drive_service.files().export_media(
                                fileId=sheets_id,
                                mimeType='text/csv'
                            )
                            
                            fh = io.BytesIO()
                            downloader = MediaIoBaseDownload(fh, request)
                            done = False
                            while done is False:
                                status, done = downloader.next_chunk()
                            
                            fh.seek(0)
                            csv_content = fh.read().decode('utf-8')
                            
                            # Parse CSV
                            import csv
                            csv_reader = csv.reader(io.StringIO(csv_content))
                            sheet_values = list(csv_reader)
                            
                            if sheet_values:
                                all_values.append([f"=== DATA FROM SHEET: {sheet_name} (via CSV export) ==="])
                                all_values.extend(sheet_values)
                                self.logger.info(f"✅ Successfully read {len(sheet_values)} rows using Drive API CSV export")
                                sheet_read_success = True
                                
                        except Exception as csv_error:
                            self.logger.debug(f"Drive API CSV export failed: {csv_error}")
                    
                    if not sheet_read_success:
                        self.logger.error(f"❌ All methods failed for sheet '{sheet_name}'")
                        self.logger.error(f"   This sheet cannot be accessed via Google Sheets API")
                        self.logger.error(f"   Possible reasons:")
                        self.logger.error(f"   1. It's a Google Form response sheet (has API restrictions)")
                        self.logger.error(f"   2. The sheet is not properly shared with your account")
                        self.logger.error(f"   3. The document type doesn't support Sheets API")
                        self.logger.error(f"   SOLUTION: Create a copy of the sheet as a regular Google Sheet")
            
            if not all_values:
                self.logger.warning("No data found in any Google Sheet")
                return {}
            
            values = all_values
            self.logger.info(f"📊 Total rows from all sheets: {len(values)}")

            placeholder_data: Dict[str, str] = {}
            
            # Define placeholders that MUST come from Gemini analysis (not manual entries)
            analysis_based_placeholders = {
                'p_r_1', 'p_r_2', 'p_r_3',
                's_r_1', 's_r_2', 's_r_3',
                'days', 'p_b', 'd_b', 'd_v', 'd_p'
            }

            # First, get manually entered values for non-analysis placeholders
            # Skip header row
            for row in values[1:]:
                if len(row) >= 2:
                    placeholder_name = str(row[0]).strip()
                    placeholder_value = str(row[1]).strip()

                    # Only add manual values for placeholders that are NOT analysis-based
                    if placeholder_name in self.linked_placeholders and placeholder_name not in analysis_based_placeholders:
                        placeholder_data[placeholder_name] = placeholder_value
                        self.logger.info(f"📋 Loaded from Sheet (manual): {placeholder_name} = {placeholder_value}")

            # Second, ALWAYS analyze the entire sheet with Gemini AI to extract project data
            # This will populate: p_r_1-3, s_r_1-3, days, p_b, d_b, d_v, d_p
            # Gemini analysis takes priority for these placeholders
            self.logger.info("=" * 80)
            self.logger.info("🤖 STARTING GEMINI AI ANALYSIS OF GOOGLE SHEETS DATA")
            self.logger.info("=" * 80)
            self.logger.info(f"📊 Sheet has {len(values)} rows of data")
            self.logger.info(f"🔍 Project analyzer initialized: {self.project_analyzer is not None}")
            
            if not self.project_analyzer:
                self.logger.error("❌ ProjectAnalyzer is None - cannot run Gemini analysis")
                self.logger.error("   Analysis-based placeholders will be empty")
            elif not self.project_analyzer.gemini_available:
                self.logger.error("❌ Gemini AI is not available in ProjectAnalyzer")
                self.logger.error("   Check GEMINI_API_KEY configuration")
            else:
                self.logger.info("✅ ProjectAnalyzer and Gemini AI are ready - proceeding with analysis")
            
            try:
                if not self.project_analyzer:
                    analyzed_data = {}
                else:
                    analyzed_data = self.project_analyzer.analyze_project_data(values)
                
                if analyzed_data:
                    self.logger.info(f"✅ Gemini returned {len(analyzed_data)} placeholder values")
                    # Gemini analysis results take priority - override any manual entries for analysis-based placeholders
                    analyzed_count = 0
                    for key, value in analyzed_data.items():
                        if value:  # Only add if has value
                            placeholder_data[key] = value
                            if key in analysis_based_placeholders:
                                self.logger.info(f"🤖 Analyzed (Gemini): {key} = {value}")
                                analyzed_count += 1
                            else:
                                self.logger.info(f"🤖 Analyzed (additional): {key} = {value}")
                    
                    self.logger.info(f"✅ Gemini analysis populated {analyzed_count} analysis-based placeholders")
                    self.logger.info(f"✅ Total placeholders from Gemini: {len([k for k in analyzed_data.keys() if analyzed_data.get(k)])}")
                else:
                    self.logger.error("❌ Gemini analysis returned no data - analysis-based placeholders will be empty")
                    self.logger.error("   This means Gemini AI did not return valid results")
            except Exception as e:
                self.logger.error(f"❌ EXCEPTION during Gemini analysis: {e}")
                import traceback
                self.logger.error(traceback.format_exc())
                self.logger.error("⚠️ Continuing without Gemini analysis results")
            
            self.logger.info("=" * 80)

            self.cache[cache_key] = placeholder_data
            self.logger.info(f"\u2705 Fetched {len(placeholder_data)} placeholder values from Sheet (manual + analyzed)")
            return placeholder_data

        except HttpError as e:
            self.logger.error(f"Google Sheets API error: {e}")
            self.logger.error("Make sure the Sheet ID is correct and shared with the service account")
            return {}
        except Exception as e:
            self.logger.error(f"Error fetching from Google Sheets: {e}")
            return {}

    def get_placeholder_value(self, placeholder_name: str) -> Optional[str]:
        data = self.fetch_placeholder_values()
        return data.get(placeholder_name)

    def is_sheet_linked_placeholder(self, placeholder_name: str) -> bool:
        return placeholder_name in self.linked_placeholders

    def clear_cache(self) -> None:
        self.cache.clear()
        self.logger.debug("Sheet data cache cleared")

    def get_sheet_url(self, sheets_id: Optional[str] = None, gid: Optional[int] = None) -> Optional[str]:
        """
        Return a Google Sheets URL for the given sheet id (or configured default).
        
        Args:
            sheets_id: Sheet ID or full URL (will extract ID automatically)
            gid: Optional sheet GID (for specific sheet within workbook)
        """
        raw_sheets_id = sheets_id or self.sheets_id
        if not raw_sheets_id:
            self.logger.warning("No Google Sheets ID available")
            return None
        
        # Extract ID from URL if provided
        extracted_id = extract_sheet_id(raw_sheets_id)
        if not extracted_id:
            self.logger.warning(f"Could not extract Sheet ID from: {raw_sheets_id}")
            return None
        
        if gid is not None:
            url = f"https://docs.google.com/spreadsheets/d/{extracted_id}/edit#gid={gid}"
        else:
            url = f"https://docs.google.com/spreadsheets/d/{extracted_id}/edit"
        self.logger.info(f"\ud83d\udccd Generated Sheet URL: {url}")
        return url


