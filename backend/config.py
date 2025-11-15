"""
Configuration settings for the PPT Automation Prototype
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Google Slides/Drive API Configuration
AUTH_MODE = os.getenv('AUTH_MODE', 'oauth')  # 'service_account' or 'oauth'
GOOGLE_CREDENTIALS_FILE = os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials/service_account.json')
GOOGLE_OAUTH_CLIENT_FILE = os.getenv('GOOGLE_OAUTH_CLIENT_FILE', 'credentials/credentials.json')
GOOGLE_TOKEN_FILE = os.getenv('GOOGLE_TOKEN_FILE', 'token.json')
GOOGLE_SCOPES = [
    'https://www.googleapis.com/auth/presentations',
    # Use full Drive scope so we can read/copy templates the user already owns or has access to
    'https://www.googleapis.com/auth/drive',
    # Full access to Google Sheets (read and write) for placeholder values and analysis
    'https://www.googleapis.com/auth/spreadsheets'
]

# Gemini (Google Generative AI) Configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.5-pro')
GEMINI_IMAGE_MODEL = os.getenv('GEMINI_IMAGE_MODEL', 'gemini-2.5-flash-image-preview')

# Template Configuration
TEMPLATE_PRESENTATION_ID = os.getenv('TEMPLATE_PRESENTATION_ID')  # You'll set this after creating template

# Placeholder Configuration
PLACEHOLDERS = {
    'TITLE': '{{TITLE}}',
    'SUBTITLE': '{{SUBTITLE}}',
    'CONTENT_1': '{{CONTENT_1}}',
    'CONTENT_2': '{{CONTENT_2}}',
    'BULLET_1': '{{BULLET_1}}',
    'BULLET_2': '{{BULLET_2}}',
    'BULLET_3': '{{BULLET_3}}',
    'FOOTER': '{{FOOTER}}'
}

GEMINI_IMAGE_MODEL = "gemini-2.5-flash-image-preview"

# Default image URL if none provided for an image placeholder
DEFAULT_IMAGE_URL = os.getenv('DEFAULT_IMAGE_URL', 'https://via.placeholder.com/800x600/2563eb/ffffff?text=Company+Image')

# Bing Image Search (optional)
BING_IMAGE_SEARCH_KEY = os.getenv('BING_IMAGE_SEARCH_KEY')
BING_IMAGE_SEARCH_ENDPOINT = os.getenv('BING_IMAGE_SEARCH_ENDPOINT', 'https://api.bing.microsoft.com/v7.0/images/search')

# Logging configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = None  # Disabled - logs will only appear in console, not stored to files

# Image cropping configuration
IMAGE_CROP_SETTINGS = {
    'enabled': True,
    'max_crop_percentage': 0.9,  # Don't crop more than 40%
    'center_crop': True,
    'preserve_logos': True,
    'crop_only': True,  # If True: only crop to match aspect ratio (no resize to exact pixels). If False: crop + resize to exact dimensions
}

# Optional manual dimensions for cropping per placeholder name.
# If provided, these take precedence over auto-detected placeholder sizes.
# Units: use 'IN' for inches (will be converted to PT: 1in = 72pt), or 'PT'.
# Dimensions extracted from prompts_image.json file.
MANUAL_CROP_DIMS = {
    # Main image placeholders
    'image_1': {'width': 8.47, 'height': 10.63, 'unit': 'IN'},  # Portrait
    'image_2': {'width': 12.5, 'height': 4.17, 'unit': 'IN'},  # Landscape
    'image_3': {'width': 8.33, 'height': 10.83, 'unit': 'IN'},  # Portrait
    'backgroundImage': {'width': 26.67, 'height': 15.0, 'unit': 'IN'},  # Landscape
    
    # Scope image placeholders (all same size - portrait)
    'scope_img_1': {'width': 5.75, 'height': 12.74, 'unit': 'IN'},  # Portrait
    'scope_img_2': {'width': 5.75, 'height': 12.74, 'unit': 'IN'},  # Portrait
    'scope_img_3': {'width': 5.75, 'height': 12.74, 'unit': 'IN'},  # Portrait
    'scope_img_4': {'width': 5.75, 'height': 12.74, 'unit': 'IN'},  # Portrait
    'scope_img_5': {'width': 5.75, 'height': 12.74, 'unit': 'IN'},  # Portrait
    'scope_img_6': {'width': 5.75, 'height': 12.74, 'unit': 'IN'},  # Portrait
    'scope_img_7': {'width': 5.75, 'height': 12.74, 'unit': 'IN'},  # Portrait
    'scope_img_8': {'width': 5.75, 'height': 12.74, 'unit': 'IN'},  # Portrait
    'scope_img_9': {'width': 5.75, 'height': 12.74, 'unit': 'IN'},  # Portrait
    'scope_img_10': {'width': 5.75, 'height': 12.74, 'unit': 'IN'},  # Portrait
    'scope_img_11': {'width': 5.75, 'height': 12.74, 'unit': 'IN'},  # Portrait
    'scope_img_12': {'width': 5.75, 'height': 12.74, 'unit': 'IN'},  # Portrait
    'scope_img_13': {'width': 5.75, 'height': 12.74, 'unit': 'IN'},  # Portrait
    'scope_img_14': {'width': 5.75, 'height': 12.74, 'unit': 'IN'},  # Portrait
    'scope_img_15': {'width': 5.75, 'height': 12.74, 'unit': 'IN'},  # Portrait
    
    # Logo placeholders - use numbered variants if you have multiple companyLogo with different sizes
    # Update these dimensions based on your actual template placeholders
    'companyLogo_1': {'width': 3.22, 'height': 2.6, 'unit': 'IN'},  # First companyLogo (adjust dimensions)
    'companyLogo_2': {'width': 4.34, 'height': 3.84, 'unit': 'IN'},  # Second companyLogo (adjust dimensions)
    # Keep 'companyLogo' for backward compatibility if you have a single one
    # 'companyLogo': {'width': 200, 'height': 200, 'unit': 'IN'},  # Default companyLogo (used if no numbered variant matches)
    
    # Note: chart_1, d_i_image_1, d_i_image_2 use dynamic dimensions from placeholder
    # Note: logo dimensions should be set manually if needed
}

# Google Sheets Configuration
GOOGLE_SHEETS_ID = os.getenv('GOOGLE_SHEETS_ID')  # Can be ID or full URL
GOOGLE_SHEETS_RANGE = os.getenv('GOOGLE_SHEETS_RANGE', 'Sheet1')  # Default to whole sheet (just sheet name)

# Placeholders that should be fetched from Google Sheets
# These can be manually entered OR automatically analyzed by Gemini AI
SHEET_LINKED_PLACEHOLDERS = [
    'days',
    'p_b',
    'd_p',
    'd_v',
    'd_b',
    # Resource placeholders (top 6 resources from project analysis)
    'p_r_1',
    'p_r_2',
    'p_r_3',
    's_r_1',
    's_r_2',
    's_r_3',
]

# Placeholders that should be hyperlinked to Google Sheets
HYPERLINKED_PLACEHOLDERS = {
    'Open Cost Estimate': {
        'text': 'Open Cost Estimate',
        'use_sheet_link': True,
        'sheet_id_key': 'GOOGLE_SHEETS_ID',
    },
    'View Estimate': {
        'text': 'View Estimate',
        'use_sheet_link': True,
        'sheet_id_key': 'GOOGLE_SHEETS_ID',
    },
    'follow_reference_link_1': {
        'text': 'Follow Reference Link',
        'use_sheet_link': False,
        'extract_from_description': True,
        'color': 'primary',
    },
    'follow_reference_link_2': {
        'text': 'Follow Reference Link',
        'use_sheet_link': False,
        'extract_from_description': True,
        'color': 'primary',
    },
    'follow_reference_link_3': {
        'text': 'Follow Reference Link',
        'use_sheet_link': False,
        'extract_from_description': True,
        'color': 'primary',
    },
    'follow_reference_link_4': {
        'text': 'Follow Reference Link',
        'use_sheet_link': False,
        'extract_from_description': True,
        'color': 'secondary',
    },
    'follow_reference_link_5': {
        'text': 'Follow Reference Link',
        'use_sheet_link': False,
        'extract_from_description': True,
        'color': 'secondary',
    },
    'follow_reference_link_6': {
        'text': 'Follow Reference Link',
        'use_sheet_link': False,
        'extract_from_description': True,
        'color': 'secondary',
    },
}
