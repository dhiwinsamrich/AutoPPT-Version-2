"""
Main PPT Automation System
Orchestrates the entire process of AI-powered presentation generation
"""
from .generator import ContentGenerator
from .slides_client import SlidesClient
from utils.placeholder_matcher import PlaceholderMatcher
from utils.logger import get_logger
from utils.color_manager import color_manager
from utils.sheets_reader import SheetsReader
from config import TEMPLATE_PRESENTATION_ID, DEFAULT_IMAGE_URL, BING_IMAGE_SEARCH_KEY, BING_IMAGE_SEARCH_ENDPOINT, LOG_LEVEL, LOG_FILE, MANUAL_CROP_DIMS
from utils.placeholder_analyzer import analyze_presentation
import requests
import os


class PPTAutomation:
    def __init__(self, use_ai=True):
        """Initialize the PPT Automation system"""
        self.use_ai = use_ai  # Store use_ai as instance attribute
        self.logger = get_logger(__name__, LOG_LEVEL, LOG_FILE)
        self.slides_client = SlidesClient()
        self.placeholder_matcher = PlaceholderMatcher()
        
        # Initialize Sheets Reader using the same credentials as Slides
        credentials = self.slides_client.get_credentials()
        self.sheets_reader = SheetsReader(credentials) if credentials else None
        
        if use_ai:
            self.content_generator = ContentGenerator()
            self.placeholder_matcher.set_content_generator(self.content_generator)
            self.logger.info("AI Content Generator initialized")
        else:
            raise ValueError("AI Content Generator is required")

    def _select_property_set(self, project_description):
        """
        Analyze project description and select the appropriate property set.
        Each property gets ONE value from the selected set.
        
        Returns:
            tuple: (property1, property2, property3) - each is a single value from the selected set
        """
        if not project_description:
            # Default to set 1 if no description
            return (
                'Aesthetically Appealing',
                'Enhanced User Experience',
                'Mobile Responsive'
            )
        
        desc_lower = str(project_description).lower()
        
        # Set 1: Design/UI/UX focused
        # Values: "Aesthetically Appealing", "Enhanced User Experience", "Mobile Responsive"
        set1_keywords = ['design', 'ui', 'ux', 'aesthetic', 'visual', 'interface', 'user experience', 
                        'mobile', 'responsive', 'frontend', 'appearance', 'look', 'feel', 'styling',
                        'beautiful', 'appealing', 'modern design', 'user interface']
        set1_values = ['Aesthetically Appealing', 'Enhanced User Experience', 'Mobile Responsive']
        
        # Set 2: E-commerce/Shopify focused
        # Values: "Elegant & Purposeful Design", "Frictionless User Experience", "Shopify-Optimised Experience"
        set2_keywords = ['shopify', 'ecommerce', 'e-commerce', 'online store', 'retail', 'shopping', 
                        'checkout', 'cart', 'payment', 'merchant', 'storefront', 'product catalog',
                        'frictionless', 'seamless', 'optimized', 'optimised']
        set2_values = ['Elegant & Purposeful Design', 'Frictionless User Experience', 'Shopify-Optimised Experience']
        
        # Set 3: Architecture/Technical focused
        # Values: "Modular by Design", "Custom-Built Architecture", "Adaptable Structure"
        set3_keywords = ['architecture', 'modular', 'scalable', 'custom-built', 'system', 'infrastructure',
                        'backend', 'api', 'framework', 'structure', 'adaptable', 'flexible', 'technical',
                        'development', 'platform', 'solution', 'enterprise', 'integration']
        set3_values = ['Modular by Design', 'Custom-Built Architecture', 'Adaptable Structure']
        
        # Count keyword matches for each set
        set1_score = sum(1 for keyword in set1_keywords if keyword in desc_lower)
        set2_score = sum(1 for keyword in set2_keywords if keyword in desc_lower)
        set3_score = sum(1 for keyword in set3_keywords if keyword in desc_lower)
        
        self.logger.info(f"Property set selection scores - Set 1: {set1_score}, Set 2: {set2_score}, Set 3: {set3_score}")
        
        # Select set with highest score, default to set 1 if tie
        if set2_score > set1_score and set2_score > set3_score:
            # Set 2: Shopify/E-commerce
            self.logger.info("✅ Selected property Set 2 (Shopify/E-commerce focused)")
            return tuple(set2_values)
        elif set3_score > set1_score:
            # Set 3: Architecture/Technical
            self.logger.info("✅ Selected property Set 3 (Architecture/Technical focused)")
            return tuple(set3_values)
        else:
            # Set 1: Design/UI/UX (default)
            self.logger.info("✅ Selected property Set 1 (Design/UI/UX focused)")
            return tuple(set1_values)
    
    def _extract_side_headings_from_description(self, description):
        """Parse project description text for side_heading_1..15 overrides.

        Expected formats (case-insensitive):
        - side_heading_1: Value
        - side-heading-2 - Value
        - Side_Heading_3: Value
        - side_heading_3: Value
        - side heading 3 Value (last variant requires a colon or dash to be safe)

        Returns dict like { 'side_Heading_1': 'Value', ... }
        """
        import re
        overrides = {}
        if not description:
            return overrides
        lines = str(description).splitlines()
        pattern = re.compile(r"^\s*side[\s_\-]?heading[\s_\-]?([1-9]|1[0-5])\s*[:\-]\s*(.+)$", re.IGNORECASE)
        for line in lines:
            m = pattern.match(line.strip())
            if not m:
                continue
            idx = m.group(1)
            value = m.group(2).strip()
            if value:
                key = f"side_Heading_{idx}"
                overrides[key] = value
        return overrides
    
    def _split_side_headings(self, content_map, available_placeholders):
        """Split side_Heading content between side_Heading_X and side_Head_X if both exist.
        
        Args:
            content_map: Dictionary of placeholder content
            available_placeholders: Set/list of available placeholder names in the template
        
        Returns:
            Updated content_map with split content
        """
        import re
        
        # Find which side_Heading and side_Head placeholders exist
        available_set = set(available_placeholders) if not isinstance(available_placeholders, set) else available_placeholders
        heading_pattern = re.compile(r'^side_Heading_(\d+)$', re.IGNORECASE)
        head_pattern = re.compile(r'^side_Head_(\d+)$', re.IGNORECASE)
        
        # Detect available side_Headings and side_Heads
        available_headings = set()
        available_heads = set()
        for placeholder_name in available_set:
            match = heading_pattern.match(placeholder_name)
            if match:
                available_headings.add(int(match.group(1)))
            match = head_pattern.match(placeholder_name)
            if match:
                available_heads.add(int(match.group(1)))
        
        # Find pairs that need splitting (both side_Heading_X and side_Head_X exist)
        pairs_to_split = available_headings & available_heads
        
        if not pairs_to_split:
            return content_map
        
        self.logger.info(f"✂️ Splitting side_Heading content for pairs: {sorted(pairs_to_split)}")
        
        for num in pairs_to_split:
            heading_key = f'side_Heading_{num}'
            head_key = f'side_Head_{num}'
            
            # Only split if side_Heading has content and side_Head doesn't (or is empty)
            if heading_key in content_map and (head_key not in content_map or not content_map.get(head_key)):
                full_text = str(content_map[heading_key]).strip()
                words = full_text.split()
                
                if len(words) == 1:
                    # 1 word: Keep in side_Heading, leave side_Head empty
                    content_map[heading_key] = words[0]
                    content_map[head_key] = ""
                    self.logger.info(f"✂️ Split {heading_key}: '{words[0]}' | {head_key}: (empty)")
                elif len(words) == 2:
                    # 2 words: First word in side_Heading, second in side_Head
                    content_map[heading_key] = words[0]
                    content_map[head_key] = words[1]
                    self.logger.info(f"✂️ Split {heading_key}: '{words[0]}' | {head_key}: '{words[1]}'")
                elif len(words) >= 3:
                    # 3+ words: First 1-2 words in side_Heading, rest in side_Head
                    split_at = 1 if len(words) == 3 else 2
                    content_map[heading_key] = ' '.join(words[:split_at])
                    content_map[head_key] = ' '.join(words[split_at:])
                    self.logger.info(f"✂️ Split {heading_key}: '{content_map[heading_key]}' | {head_key}: '{content_map[head_key]}'")
        
        return content_map

    def _find_max_side_heading_number(self, detected_placeholders):
        """Find the maximum side_Heading number from detected placeholders.
        
        Args:
            detected_placeholders: List of placeholder dictionaries with 'name' or 'placeholder' field
            
        Returns:
            Maximum side_Heading number found, or 0 if none found
        """
        import re
        max_number = 0
        pattern = re.compile(r'^side_Heading_(\d+)$', re.IGNORECASE)
        
        for ph in detected_placeholders:
            # Support both 'name' (from analyze_presentation) and 'placeholder' (from find_placeholders)
            name = ph.get('name') or ph.get('placeholder', '')
            if not name:
                continue
            
            match = pattern.match(name)
            if match:
                number = int(match.group(1))
                max_number = max(max_number, number)
        
        return max_number
    
    def _find_slides_to_delete_for_side_headings(self, detected_placeholders, max_side_heading_number):
        """Find slide IDs that contain side_Heading placeholders beyond the maximum number.
        
        Args:
            detected_placeholders: List of placeholder dictionaries with 'name' or 'placeholder' and 'slide_id' fields
            max_side_heading_number: Maximum side_Heading number to keep
            
        Returns:
            Set of slide IDs to delete
        """
        import re
        pattern = re.compile(r'^side_Heading_(\d+)$', re.IGNORECASE)
        slides_to_delete = set()
        
        for ph in detected_placeholders:
            # Support both 'name' (from analyze_presentation) and 'placeholder' (from find_placeholders)
            name = ph.get('name') or ph.get('placeholder', '')
            slide_id = ph.get('slide_id')
            
            if not name or not slide_id:
                continue
            
            match = pattern.match(name)
            if match:
                number = int(match.group(1))
                if number > max_side_heading_number:
                    slides_to_delete.add(slide_id)
        
        return slides_to_delete

    def _extract_placeholder_overrides_from_description(self, description, available_placeholders):
        """Parse generic placeholder overrides from a free-form description.

        Supports lines like (case-insensitive):
          projectOverview: Detailed text here
          Head1_para - Short paragraph text
          proposalName : Technical Proposal
          target_audience: B2B

        Multi-line values are supported when subsequent indented lines start with two spaces or a dash.
        Parsing stops when a new key line is encountered.
        Only keys that exist in available_placeholders are returned.
        """
        import re
        overrides: dict[str, str] = {}
        if not description:
            return overrides
        lines = description.splitlines()
        key_line = re.compile(r"^\s*([A-Za-z0-9_\- ]{2,})\s*[:\-]\s*(.*)$")

        def normalize_key(raw: str) -> str:
            k = raw.strip().replace('-', '_').replace(' ', '_')
            # common case mismatches from templates
            return k

        current_key = None
        buffer: list[str] = []
        for raw in lines + ['\n']:  # sentinel
            m = key_line.match(raw)
            if m:
                # flush previous
                if current_key and buffer:
                    text = '\n'.join([t.strip(' -') for t in buffer]).strip()
                    if text and current_key in available_placeholders and current_key not in overrides:
                        overrides[current_key] = text
                # start new
                nk = normalize_key(m.group(1))
                current_key = nk
                buffer = [m.group(2)] if m.group(2) else []
                continue
            # continuation line if indented or bullet
            if current_key:
                if raw.startswith('  ') or raw.strip().startswith('- '):
                    buffer.append(raw)
                    continue
            # otherwise ignore
        return overrides
    
    def generate_presentation_auto(self, context, template_id=None, output_title=None,
                                   profile=None, project_name=None, project_description=None, 
                                   company_name=None, proposal_type=None, company_website=None,
                                   sheets_id=None, sheets_range=None, primary_color=None, 
                                   secondary_color=None, accent_color=None):
        """Auto-detect placeholders (type + name) and fill text/images accordingly."""
        def _normalize_dims(dims):
            if not dims:
                return None
            unit = str(dims.get('unit') or 'PT').upper()
            width = dims.get('width')
            height = dims.get('height')
            if unit in ('IN', 'INCH', 'INCHES'):
                try:
                    return {'width': float(width) * 72.0, 'height': float(height) * 72.0, 'unit': 'PT'}
                except Exception:
                    return dims
            return dims
        
        if not template_id:
            template_id = TEMPLATE_PRESENTATION_ID
        if not template_id:
            raise ValueError("No template presentation ID provided")

        self.logger.info(f"Auto-detect flow started for: {context}")

        if hasattr(self, 'content_generator'):
            self.content_generator.reset_token_usage()

        # Duplicate the template deck using Drive (reliable way to clone all slides)
        working_title = output_title or f"{company_name or context} - Generated"
        new_presentation_id = self.slides_client.copy_presentation(template_id, working_title)
        if not new_presentation_id:
            return {
                'success': False,
                'error': 'COPY_FAILED',
                'message': 'Could not copy the template. Ensure the template ID/URL is correct and shared with the authorized account.',
                'token_usage': self.content_generator.get_token_usage_summary() if hasattr(self, 'content_generator') else None
            }
        target_id = new_presentation_id

        # ============================================================================
        # STEP 1: INITIAL ANALYSIS - Analyze placeholders to identify structure
        # ============================================================================
        self.logger.info("📊 Step 1: Analyzing presentation to detect placeholders...")
        report = analyze_presentation(target_id)
        detected = report.get('placeholders') or []
        if not detected:
            self.logger.error("No placeholders found via analyzer")
            return None
        self.logger.info(f"Found {len(detected)} placeholders in initial analysis")

        # ============================================================================
        # STEP 2: IDENTIFY MAX SIDE_HEADING - Find the maximum side_Heading number
        # Priority: Check project_description first, then fall back to template detection
        # ============================================================================
        self.logger.info("🔍 Step 2: Identifying maximum side_Heading number...")
        
        # First, check if project_description specifies any side_Headings
        # This takes priority over template detection
        max_side_heading_from_description = 0
        if project_description:
            side_heading_overrides = self._extract_side_headings_from_description(project_description)
            if side_heading_overrides:
                # Find max from description overrides
                import re
                pattern = re.compile(r'^side_Heading_(\d+)$', re.IGNORECASE)
                for key in side_heading_overrides.keys():
                    match = pattern.match(key)
                    if match:
                        number = int(match.group(1))
                        max_side_heading_from_description = max(max_side_heading_from_description, number)
                if max_side_heading_from_description > 0:
                    self.logger.info(f"📝 Found side_Headings in project description: max = {max_side_heading_from_description}")
        
        # Log all detected side_Headings from template for debugging
        import re
        pattern = re.compile(r'^side_Heading_(\d+)$', re.IGNORECASE)
        detected_side_headings = []
        for ph in detected:
            name = ph.get('name') or ph.get('placeholder', '')
            if name:
                match = pattern.match(name)
                if match:
                    number = int(match.group(1))
                    detected_side_headings.append((number, name))
        
        if detected_side_headings:
            detected_side_headings.sort()
            self.logger.info(f"📋 Template contains side_Heading placeholders: {[f'side_Heading_{num}' for num, _ in detected_side_headings]}")
        
        max_side_heading_from_template = self._find_max_side_heading_number(detected)
        
        # Use description max if provided, otherwise use template max
        if max_side_heading_from_description > 0:
            max_side_heading = max_side_heading_from_description
            self.logger.info(f"✓ Using maximum side_Heading from project description: {max_side_heading} (template has up to {max_side_heading_from_template})")
        elif max_side_heading_from_template > 0:
            max_side_heading = max_side_heading_from_template
            self.logger.info(f"✓ Maximum side_Heading identified from template: {max_side_heading}")
        else:
            max_side_heading = 0
            self.logger.info("No side_Heading placeholders found - skipping slide deletion")

        # ============================================================================
        # STEP 3: DELETE EXCESS SLIDES - Remove slides with side_Headings beyond max
        # ============================================================================
        if max_side_heading > 0:
            self.logger.info(f"🗑️  Step 3: Identifying and deleting slides with side_Headings beyond {max_side_heading}...")
            slides_to_delete = self._find_slides_to_delete_for_side_headings(detected, max_side_heading)
            
            if slides_to_delete:
                self.logger.info(f"📋 Found {len(slides_to_delete)} slide(s) to delete: {list(slides_to_delete)}")
                delete_success = self.slides_client.delete_slides(target_id, list(slides_to_delete))
                
                if delete_success:
                    self.logger.info(f"✅ Successfully deleted {len(slides_to_delete)} slide(s)")
                else:
                    self.logger.error(f"❌ Failed to delete slides. Continuing with existing slides.")
                
                # Re-analyze after deletion to get clean placeholder list
                self.logger.info("🔄 Re-analyzing presentation after slide deletion...")
                report = analyze_presentation(target_id)
                detected = report.get('placeholders') or []
                self.logger.info(f"✓ Re-analysis complete: {len(detected)} placeholders remaining")
                
                # Verify deletion was successful
                remaining_max = self._find_max_side_heading_number(detected)
                if remaining_max <= max_side_heading:
                    self.logger.info(f"✓ Verified: Maximum side_Heading after deletion is {remaining_max} (within limit)")
                else:
                    self.logger.warning(f"⚠️ Warning: Maximum side_Heading after deletion is {remaining_max} (expected <= {max_side_heading})")
            else:
                self.logger.info(f"✓ No slides to delete - all side_Headings are within range 1-{max_side_heading}")

        # ============================================================================
        # STEP 4: CONTINUE WITH CONTENT GENERATION - Process cleaned presentation
        # ============================================================================
        self.logger.info("🚀 Step 4: Proceeding with content generation...")
        
        # Build simple structures
        placeholder_names = [p.get('name') for p in detected if p.get('name')]
        self.logger.debug(f"Detected placeholders: {placeholder_names}")

        # Generate content via matcher using only names we can match
        # Include all detected placeholders for styling, even quote placeholders (u0022)
        placeholders_for_matcher = [{
            'placeholder': p.get('name') if not p.get('is_quote') else 'u0022',
            'element_id': p.get('element_id'),
            'slide_id': p.get('slide_id'),
            'is_quote': p.get('is_quote', False)
        } for p in detected if p.get('name') or p.get('is_quote')]

        match_result = self.placeholder_matcher.match_placeholders(placeholders_for_matcher)
        self.logger.info(f"Matched {match_result['total_matched']}/{match_result['total_found']} placeholders (auto)")
        
        # ============================================================================
        # STEP 4.1: PROCESS HYPERLINKED PLACEHOLDERS IMMEDIATELY AFTER MATCHING
        # ============================================================================
        try:
            from config import HYPERLINKED_PLACEHOLDERS, GOOGLE_SHEETS_ID
        except Exception as e:
            self.logger.error(f"❌ Error importing HYPERLINKED_PLACEHOLDERS: {e}")
            HYPERLINKED_PLACEHOLDERS = {}
            GOOGLE_SHEETS_ID = None

        self.logger.info(f"🔗 Step 4.1: Checking for hyperlinked placeholders: HYPERLINKED_PLACEHOLDERS={list(HYPERLINKED_PLACEHOLDERS.keys()) if HYPERLINKED_PLACEHOLDERS else 'None'}")
        self.logger.info(f"🔗 Step 4.1: HYPERLINKED_PLACEHOLDERS type: {type(HYPERLINKED_PLACEHOLDERS)}, length: {len(HYPERLINKED_PLACEHOLDERS) if HYPERLINKED_PLACEHOLDERS else 0}")
        
        sheet_url = None
        self.logger.info(f"🔗 Step 4.1: Checking sheets_reader: {self.sheets_reader is not None}")
        if self.sheets_reader:
            sheets_id_to_use = sheets_id or GOOGLE_SHEETS_ID
            self.logger.info(f"📊 Sheets ID check: sheets_id={sheets_id}, GOOGLE_SHEETS_ID={GOOGLE_SHEETS_ID}, sheets_id_to_use={sheets_id_to_use}")
            if sheets_id_to_use:
                try:
                    sheet_url = self.sheets_reader.get_sheet_url(sheets_id_to_use)
                    self.logger.info(f"📎 Generated sheet URL: {sheet_url}")
                except Exception as e:
                    self.logger.error(f"❌ Error generating sheet URL: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                self.logger.warning("⚠️ No Google Sheets ID provided - hyperlinks will not be created")
        else:
            self.logger.warning("⚠️ SheetsReader not initialized - hyperlinks will not be created")
        
        self.logger.info(f"🔗 Step 4.1: Final check - sheet_url={sheet_url is not None}, HYPERLINKED_PLACEHOLDERS={bool(HYPERLINKED_PLACEHOLDERS)}")

        # Extract URLs and "Follow Reference Link" text from project description for follow_reference_link placeholders
        def extract_urls_from_description(description):
            """Extract URLs from project description using regex"""
            import re
            if not description:
                return []
            # Pattern to match http://, https://, or www. URLs
            url_pattern = r'(https?://[^\s<>"{}|\\^`\[\]]+|www\.[^\s<>"{}|\\^`\[\]]+)'
            urls = re.findall(url_pattern, description)
            # Ensure URLs starting with www. have http:// prefix
            urls = [url if url.startswith('http') else f'https://{url}' for url in urls]
            return urls

        def extract_link_text_from_description(description):
            """Extract 'Follow Reference Link' text from project description if present"""
            if not description:
                return None
            import re
            # Look for "Follow Reference Link" (case-insensitive, allowing variations)
            pattern = r'Follow\s+Reference\s+Link'
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                # Return the exact matched text (preserving original case)
                return match.group(0)
            return None

        description_urls = extract_urls_from_description(project_description) if project_description else []
        link_display_text = extract_link_text_from_description(project_description) if project_description else None
        
        # Use extracted text if found, otherwise fall back to default
        if link_display_text:
            self.logger.info(f"🔗 Step 4.1: Extracted link display text from project description: '{link_display_text}'")
        else:
            link_display_text = 'Follow Reference Link'
            self.logger.info(f"🔗 Step 4.1: Using default link display text: '{link_display_text}'")
        
        self.logger.info(f"🔗 Step 4.1: Extracted {len(description_urls)} URL(s) from project description: {description_urls}")

        if HYPERLINKED_PLACEHOLDERS:
            # Separate follow_reference_link placeholders from others
            follow_reference_placeholders = {}
            other_placeholders = {}
            
            for placeholder_name, cfg in HYPERLINKED_PLACEHOLDERS.items():
                if cfg.get('extract_from_description', False):
                    follow_reference_placeholders[placeholder_name] = cfg
                else:
                    other_placeholders[placeholder_name] = cfg

            # Check all detected placeholders (matched and unmatched) for hyperlinked ones
            all_placeholder_names = [p.get('name') for p in detected if p.get('name')]
            self.logger.info(f"🔗 Step 4.1: Found {len(all_placeholder_names)} total placeholder names in presentation")
            self.logger.debug(f"🔗 Step 4.1: All placeholder names: {all_placeholder_names}")

            # Process follow_reference_link placeholders (use URLs from description)
            if follow_reference_placeholders:
                self.logger.info(f"🔗 Step 4.1: Processing {len(follow_reference_placeholders)} follow_reference_link placeholders from project description...")
                # Sort by placeholder number to ensure correct URL mapping
                sorted_placeholders = sorted(
                    follow_reference_placeholders.items(),
                    key=lambda x: int(x[0].split('_')[-1]) if x[0].split('_')[-1].isdigit() else 999
                )
                for placeholder_name, cfg in sorted_placeholders:
                    if placeholder_name not in all_placeholder_names:
                        self.logger.warning(f"⚠️ Step 4.1: Placeholder '{placeholder_name}' not found in presentation")
                        continue
                    
                    # Extract number from placeholder name (e.g., "follow_reference_link_1" -> 1)
                    try:
                        placeholder_num = int(placeholder_name.split('_')[-1])
                    except (ValueError, IndexError):
                        self.logger.warning(f"⚠️ Step 4.1: Could not extract number from placeholder '{placeholder_name}', skipping")
                        continue
                    
                    # Get URL from description (1-indexed: link_1 -> urls[0], link_2 -> urls[1], etc.)
                    url_index = placeholder_num - 1
                    if url_index < len(description_urls):
                        url = description_urls[url_index]
                        # Use extracted text from description if available, otherwise use config default
                        display_text = link_display_text or cfg.get('text', 'Follow Reference Link')
                        placeholder_text = f"{{{{{placeholder_name}}}}}"
                        
                        # Get color from primary_color/secondary_color parameters or theme
                        color = None
                        if placeholder_num <= 3:  # Links 1-3 use primary color
                            color = primary_color or '#2563eb'
                        else:  # Links 4-6 use secondary color
                            color = secondary_color or '#1e40af'
                        
                        self.logger.info(f"🔗 Step 4.1: Adding hyperlink: '{placeholder_name}' -> '{display_text}' -> {url} (color: {color})")
                        try:
                            success = self.slides_client.add_hyperlink_to_placeholder(
                                target_id,
                                placeholder_text,
                                display_text,
                                url,
                                color=color
                            )
                            if success:
                                self.logger.info(f"✅ Step 4.1: Successfully added hyperlink for '{placeholder_name}'")
                            else:
                                self.logger.warning(f"⚠️ Step 4.1: Failed to add hyperlink for '{placeholder_name}'")
                        except Exception as e:
                            self.logger.error(f"❌ Step 4.1: Exception adding hyperlink for '{placeholder_name}': {e}")
                            import traceback
                            traceback.print_exc()
                    else:
                        self.logger.warning(f"⚠️ Step 4.1: No URL available for '{placeholder_name}' (index {url_index}, found {len(description_urls)} URLs)")

            # Process other hyperlinked placeholders (use sheet URL)
            if other_placeholders and sheet_url:
                self.logger.info(f"🔗 Step 4.1: Processing {len(other_placeholders)} hyperlinked placeholders (standard mode)...")
                for placeholder_name, cfg in other_placeholders.items():
                    # Always try to add hyperlink - let add_hyperlink_to_placeholder search for the placeholder text
                    # This handles cases where the name might not match exactly in all_placeholder_names
                    display_text = cfg.get('text', placeholder_name)
                    placeholder_text = f"{{{{{placeholder_name}}}}}"
                    self.logger.info(f"🔗 Step 4.1: Attempting to add hyperlink for '{placeholder_name}' -> '{display_text}' -> {sheet_url}")
                    
                    # Log if placeholder name is in detected list for debugging
                    if placeholder_name in all_placeholder_names:
                        self.logger.debug(f"🔗 Step 4.1: Placeholder '{placeholder_name}' found in detected placeholders")
                    else:
                        self.logger.debug(f"🔗 Step 4.1: Placeholder '{placeholder_name}' not in detected list, but will search for '{placeholder_text}' directly")
                    
                    try:
                        success = self.slides_client.add_hyperlink_to_placeholder(
                            target_id,
                            placeholder_text,
                            display_text,
                            sheet_url
                        )
                        
                        if success:
                            self.logger.info(f"✅ Step 4.1: Successfully added hyperlink for '{placeholder_name}'")
                        else:
                            self.logger.warning(f"⚠️ Step 4.1: Failed to add hyperlink for '{placeholder_name}' - placeholder text '{placeholder_text}' not found in presentation")
                    except Exception as e:
                        self.logger.error(f"❌ Step 4.1: Exception adding hyperlink for '{placeholder_name}': {e}")
                        import traceback
                        traceback.print_exc()
            elif other_placeholders and not sheet_url:
                self.logger.warning("⚠️ Step 4.1: No Google Sheets URL available - skipping standard hyperlink processing")
        else:
            if not HYPERLINKED_PLACEHOLDERS:
                self.logger.warning("⚠️ Step 4.1: No hyperlinked placeholders configured")
        
        # Display unmatched placeholders for easier analysis
        if match_result.get('unmatched'):
            self.logger.warning("=" * 80)
            self.logger.warning("📋 UNMATCHED PLACEHOLDERS REPORT (Auto Mode)")
            self.logger.warning("=" * 80)
            self.logger.warning(f"⚠️ Total unmatched: {len(match_result['unmatched'])}")
            self.logger.warning("")
            
            unmatched_names = []
            unmatched_by_slide = {}
            
            for unmatched in match_result['unmatched']:
                if isinstance(unmatched, dict):
                    name = unmatched.get('name') or unmatched.get('placeholder') or 'unknown'
                    slide = unmatched.get('slide_id') or 'n/a'
                    placeholder_text = unmatched.get('placeholder', 'unknown')
                    
                    unmatched_names.append(name)
                    
                    if slide not in unmatched_by_slide:
                        unmatched_by_slide[slide] = []
                    unmatched_by_slide[slide].append({
                        'name': name,
                        'placeholder': placeholder_text
                    })
                else:
                    unmatched_names.append(str(unmatched))
            
            # Display by slide
            for slide_id, items in unmatched_by_slide.items():
                self.logger.warning(f"Slide ID: {slide_id}")
                for item in items:
                    self.logger.warning(f"  • {item['name']} (placeholder: {item['placeholder']})")
                self.logger.warning("")
            
            # Quick reference
            self.logger.warning("-" * 80)
            self.logger.warning("Quick reference (comma-separated):")
            self.logger.warning(f"  {', '.join(unmatched_names)}")
            self.logger.warning("=" * 80)

        # Pre-seed content_map: Google Sheets data (highest priority), then description overrides
        content_map = {}
        
        # Fetch data from Google Sheets if configured
        self.logger.info("=" * 80)
        self.logger.info("📊 CHECKING GOOGLE SHEETS DATA FETCH")
        self.logger.info("=" * 80)
        self.logger.info(f"🔍 sheets_reader exists: {self.sheets_reader is not None}")
        self.logger.info(f"🔍 sheets_id provided: {sheets_id is not None} (value: {sheets_id})")
        self.logger.info(f"🔍 sheets_range provided: {sheets_range is not None} (value: {sheets_range})")
        
        if self.sheets_reader:
            self.logger.info("✅ sheets_reader is available - proceeding to fetch data")
            try:
                self.logger.info(f"📥 Calling fetch_placeholder_values with sheets_id={sheets_id}, sheets_range={sheets_range}")
                sheet_data = self.sheets_reader.fetch_placeholder_values(
                    sheets_id=sheets_id,
                    sheets_range=sheets_range,
                )
                self.logger.info(f"📊 fetch_placeholder_values returned: {type(sheet_data)}, length: {len(sheet_data) if sheet_data else 0}")
                
                if sheet_data:
                    for k, v in sheet_data.items():
                        content_map[k] = v
                        self.logger.info(f"📋 Added to content_map: {k} = {v}")
                        if k.startswith(('p_r_', 's_r_', 'pr_desc_', 'sr_desc_')):
                            self.logger.info(f"🧾 Content map update (Sheets/AI mapping): {k} = {v}")
                    self.logger.info(f"✅ Using {len(sheet_data)} values from Google Sheets (including Gemini analysis)")
                else:
                    self.logger.warning("⚠️ fetch_placeholder_values returned empty dict - no data from Sheets")
            except Exception as e:
                self.logger.error(f"❌ EXCEPTION fetching from Google Sheets: {e}")
                import traceback
                self.logger.error(traceback.format_exc())
        else:
            self.logger.warning("⚠️ sheets_reader is None - cannot fetch Google Sheets data")
            self.logger.warning("   This means SheetsReader was not initialized properly")
        
        self.logger.info("=" * 80)
        side_heading_overrides = self._extract_side_headings_from_description(project_description)
        if side_heading_overrides:
            self.logger.info(f"Using side_heading overrides from description: {list(side_heading_overrides.keys())}")
            # Only include keys that are actually present in this template
            available = {ph.get('placeholder') for ph in detected}
            for key, val in side_heading_overrides.items():
                if key in available and key not in content_map:
                    content_map[key] = val
            
            # Split side_Heading content between side_Heading_X and side_Head_X if both exist
            content_map = self._split_side_headings(content_map, available)

        # Also parse generic placeholder overrides from description
        available_keys = {ph.get('placeholder') for ph in detected}
        generic_overrides = self._extract_placeholder_overrides_from_description(project_description or '', available_keys)
        if generic_overrides:
            used = []
            for k, v in generic_overrides.items():
                if k in available_keys and k not in content_map:
                    content_map[k] = v
                    used.append(k)
            if used:
                self.logger.info(f"Using description overrides: {used}")

        # Try comprehensive content generation first to mirror interactive behavior
        comprehensive_content = None
        if self.use_ai:
            try:
                self.logger.info("Attempting comprehensive content generation (auto mode)...")
                comprehensive_content = self.content_generator.generate_comprehensive_content(
                    project_name=project_name or f"{context} Project",
                    company_name=company_name or context,
                    project_description=project_description or context,
                    context=context,
                    detected_placeholders=detected,
                    preset_values=content_map
                )
                if comprehensive_content:
                    mapped = self.content_generator._map_comprehensive_to_placeholders(
                        comprehensive_content, detected
                    )
                    # Do not overwrite existing entries (e.g., from Sheets/overrides)
                    # EXCEPT for side_Heading and side_Head which may have been split
                    added = 0
                    overwritten = 0
                    for k, v in (mapped or {}).items():
                        # Allow overwriting side_Heading and side_Head placeholders (they may have been split)
                        if k.startswith('side_Heading_') or k.startswith('side_Head_'):
                            if k in content_map:
                                overwritten += 1
                            content_map[k] = v
                            added += 1
                        elif k not in content_map:
                            content_map[k] = v
                            added += 1
                    self.logger.info(f"Mapped comprehensive content to {added} placeholders ({overwritten} overwritten) without overwriting others (auto mode)")
            except Exception as e:
                self.logger.warning(f"Comprehensive content generation (auto) failed: {e}")
        
        # Auto-fill known text placeholders BEFORE calling placeholder matcher
        # This ensures UI-provided values are used instead of AI generation
        if 'projectName' in placeholder_names:
            if project_name:
                # Use the exact project name provided by user
                content_map['projectName'] = project_name
        if 'companyName' in placeholder_names and company_name:
            content_map['companyName'] = company_name
        if 'proposalName' in placeholder_names:
            # Use proposal_type from UI input, not AI generation
            content_map['proposalName'] = proposal_type or 'Project Proposal'
            self.logger.info(f"✅ Using UI input for proposalName: '{content_map['proposalName']}'")
        
        # Set property values based on project description analysis (not AI-generated)
        if any(prop in placeholder_names for prop in ['property1', 'property2', 'property3', 'property_1', 'property_2', 'property_3']):
            prop1_val, prop2_val, prop3_val = self._select_property_set(project_description)
            
            if 'property1' in placeholder_names or 'property_1' in placeholder_names:
                content_map['property1'] = prop1_val
                if 'property_1' in placeholder_names:
                    content_map['property_1'] = prop1_val
                self.logger.info(f"✅ Set property1 based on project description: '{prop1_val}'")
            if 'property2' in placeholder_names or 'property_2' in placeholder_names:
                content_map['property2'] = prop2_val
                if 'property_2' in placeholder_names:
                    content_map['property_2'] = prop2_val
                self.logger.info(f"✅ Set property2 based on project description: '{prop2_val}'")
            if 'property3' in placeholder_names or 'property_3' in placeholder_names:
                content_map['property3'] = prop3_val
                if 'property_3' in placeholder_names:
                    content_map['property_3'] = prop3_val
                self.logger.info(f"✅ Set property3 based on project description: '{prop3_val}'")
        
        # Fill remaining via matcher per placeholder
        remaining_map = self.placeholder_matcher.generate_content_for_placeholders(
            match_result['matched'], context, company_name, project_name, project_description,
            existing_content=content_map
        )
        # Don't overwrite comprehensive values or hyperlinked placeholders
        for k, v in (remaining_map or {}).items():
            # Skip hyperlinked placeholders - they're already processed in Step 4.1
            if k in HYPERLINKED_PLACEHOLDERS:
                self.logger.debug(f"Skipping '{k}' from remaining_map - already hyperlinked in Step 4.1")
                continue
            if k not in content_map:
                content_map[k] = v
                if k.startswith(('p_r_', 's_r_', 'pr_desc_', 'sr_desc_')):
                    self.logger.info(f"🧾 Content map update (remaining generation): {k} = {v}")

        # Cache for companyLogo - reuse same logo for all variants (just resize)
        
        # Handle u0022 quote placeholder - replace with literal quote character
        # This must be done BEFORE generating text_map to ensure it's included
        self.logger.info(f"🔍 Checking {len(detected)} detected placeholders for u0022...")
        for ph in detected:
            is_quote = ph.get('is_quote', False)
            placeholder_text = ph.get('placeholder', '')
            name = ph.get('name', '')
            
            # self.logger.info(f"  Placeholder: '{placeholder_text}', name: '{name}', is_quote: {is_quote}")
            
            if is_quote:
                # For u0022, replace with actual curly quote character - add to content_map
                if 'u0022' in placeholder_text.lower() or name == 'u0022':
                    # Add to content map to replace u0022 placeholder with curly quote character
                    # Using left double quotation mark (") which is commonly used
                    content_map[placeholder_text] = '\u201c'  # Left double quotation mark "
                    self.logger.info(f"✅ Added u0022 placeholder '{placeholder_text}' to content_map, will be replaced with curly quote: '\u201c'")
                else:
                    self.logger.warning(f"⚠️ Quote placeholder detected but not u0022: placeholder='{placeholder_text}', name='{name}'")

        # Theme generation - uses user-provided colors or company name analysis (no logo analysis)
        theme = None
        if profile == 'company' and (company_name or context):
            # Priority 1: Use user-provided colors if available
            if primary_color or secondary_color or accent_color:
                self.logger.info("✓ USER COLORS DETECTED - No logo analysis will be performed")
                self.logger.info(f"Input colors: Primary={primary_color}, Secondary={secondary_color}, Accent={accent_color}")
                theme = {
                    "primary_color": primary_color or '#2563eb',
                    "secondary_color": secondary_color or '#1e40af',
                    "accent_color": accent_color or '#3b82f6',
                    "brand_personality": 'professional',
                    "target_audience": 'B2B',
                    "industry": 'General',
                    "theme_description": f"Custom theme with user-provided colors for {company_name or context}",
                    "source": "user_provided_colors"
                }
                self.logger.info(f"✓ Theme generated from USER COLORS: Primary={theme['primary_color']}, Secondary={theme['secondary_color']}, Accent={theme['accent_color']}")
            else:
                self.logger.info("⚠ No user colors provided - Generating theme from company name only (no logo analysis)")
                theme = self.content_generator.generate_company_theme_name_only(company_name or context, project_name)

        # Split text vs images using analyzer inferred_type
        text_map = {}
        image_targets = []  # list of tuples (name, slide_id, element_id)
        image_1_path = None  # Store image_1 path for backgroundImage use
        processed_images = set()  # Track which images have already been processed
        # Initialize final_image_map early to track extracted logos (will be populated later)
        final_image_map = {}
        
        # First pass: generate image_1
        for ph in detected:
            name = ph.get('name')
            if name == 'image_1':
                try:
                    # Find dimensions for image_1
                    image_1_dimensions = None
                    if ph.get('size'):
                        size = ph['size']
                        image_1_dimensions = {
                            'width': size.get('width', {}).get('magnitude'),
                            'height': size.get('height', {}).get('magnitude'),
                            'unit': size.get('width', {}).get('unit', 'PT')
                        }
                    # Prefer manual override if provided
                    if MANUAL_CROP_DIMS.get('image_1'):
                        image_1_dimensions = _normalize_dims(MANUAL_CROP_DIMS.get('image_1'))
                    
                    image_1_path, image_1_crop, image_1_original = self.content_generator.generate_image(
                        placeholder_type='image_1',
                        context=context,
                        company_name=company_name or context,
                        project_name=project_name or f"{context} Project",
                        project_description=project_description,
                        image_requirements=None,
                        theme=theme,
                        placeholder_dimensions=image_1_dimensions
                    )
                    if image_1_path and os.path.exists(image_1_path):
                        # Replace image_1 placeholder
                        self.slides_client.replace_image_placeholder(
                            target_id,
                            "{{image_1}}",
                            image_1_path,
                            slide_id=ph.get('slide_id'),
                            crop_properties=image_1_crop,
                            target_dimensions=image_1_dimensions
                        )
                        self.logger.info("Successfully replaced image_1 placeholder with project context")
                        processed_images.add('image_1')
                except Exception as e:
                    self.logger.warning(f"Image_1 generation failed: {e}")
                break  # Exit after processing image_1
        
        # Second pass: process all other placeholders
        for ph in detected:
            name = ph.get('name')
            inferred = (ph.get('inferred_type') or '').upper()
            if not name:
                continue
            # Handle numeric placeholders {{1}}..{{4}} as literal text with auto-contrast styling
            if name in ['1', '2', '3', '4']:
                text_map[name] = name
                continue
                
            # Handle backgroundImage by copying and cropping image_1
            if name == 'backgroundImage':
                try:
                    # Get background dimensions
                    bg_dimensions = None
                    if ph.get('size'):
                        size = ph['size']
                        bg_dimensions = {
                            'width': size.get('width', {}).get('magnitude'),
                            'height': size.get('height', {}).get('magnitude'),
                            'unit': size.get('width', {}).get('unit', 'PT')
                        }
                    if MANUAL_CROP_DIMS.get('backgroundImage'):
                        bg_dimensions = _normalize_dims(MANUAL_CROP_DIMS.get('backgroundImage'))
                    
                    # Use the original uncropped image_1 to create backgroundImage
                    if image_1_original and os.path.exists(image_1_original):
                        self.logger.info(f"Creating backgroundImage from original image_1 copy (dimensions: {bg_dimensions})")
                        bg_image_path = self.content_generator.crop_existing_image(
                            source_image_path=image_1_original,
                            target_dimensions=bg_dimensions,
                            output_filename=f"backgroundImage_{company_name.replace(' ', '_') if company_name else 'auto'}.jpg"
                        )
                        if bg_image_path and os.path.exists(bg_image_path):
                            self.slides_client.replace_image_placeholder(
                                target_id,
                                "{{backgroundImage}}",
                                bg_image_path,
                                slide_id=ph.get('slide_id'),
                                crop_properties=None,
                                target_dimensions=bg_dimensions
                            )
                            self.logger.info("Successfully replaced backgroundImage placeholder using cropped copy of image_1")
                            processed_images.add('backgroundImage')
                        else:
                            self.logger.warning("Failed to create backgroundImage from image_1 original")
                    else:
                        self.logger.warning("image_1 original not available for backgroundImage, skipping")
                except Exception as e:
                    self.logger.warning(f"Background image replacement failed: {e}")
                continue
            
            if inferred == 'IMAGE' or name.lower().startswith('image') or name.lower() in ('logo', 'companylogo') or name.lower().startswith('companylogo'):
                image_targets.append((name, ph.get('slide_id'), ph.get('element_id')))
            elif inferred == 'COLOR' or name.lower().startswith('color') or name.lower().startswith('circle'):
                # Handle color placeholders - get color from theme or config
                if name in ['color1', 'color2', 'circle_1', 'circle_2']:
                    # Priority: 1. Theme colors (for color1/circle1 and color2/circle2), 2. AI-detected color, 3. Default colors
                    
                    # Always use theme colors for primary/secondary color placeholders
                    if theme and name == 'color1':
                        color = theme.get('primary_color', '#2563eb')
                        self.logger.info(f"Using primary theme color {color} for {name}")
                    elif theme and name == 'color2':
                        color = theme.get('secondary_color', '#1e40af')
                        self.logger.info(f"Using secondary theme color {color} for {name}")
                    elif theme and name == 'circle_1':
                        color = theme.get('primary_color', '#2563eb')
                        self.logger.info(f"Using primary theme color {color} for {name}")
                    elif theme and name == 'circle_2':
                        color = theme.get('secondary_color', '#1e40af')
                        self.logger.info(f"Using secondary theme color {color} for {name}")
                    else:
                        # No theme available, try AI-detected color
                        ai_detected_color = self.content_generator.get_placeholder_color(name)
                        if ai_detected_color:
                            color = ai_detected_color
                            self.logger.info(f"Using AI-detected color {color} for {name}")
                        else:
                            # Fallback to default colors
                            if name in ['color1', 'circle_1']:
                                color = '#2563eb'  # Default primary blue
                            elif name in ['color2', 'circle_2']:
                                color = '#1e40af'  # Default secondary blue
                            else:
                                color = '#3b82f6'  # Generic blue
                    
                    # Replace color placeholder by filling the shape
                    self.slides_client.replace_color_placeholder(
                        target_id,
                        f"{{{{{name}}}}}",
                        color,
                        slide_id=ph.get('slide_id')
                    )
                    self.logger.info(f"Successfully filled {name} placeholder with color {color}")
            elif inferred == 'EMOJI' or name.lower().startswith('logo'):
                # DETERMINISTIC EMOJI SELECTION
                # Handle emoji placeholders as text content
                if name in content_map:
                    text_map[name] = content_map[name]
                    self.logger.debug(f"Using provided emoji for {name}: {content_map[name]}")
                else:
                    # Extract corresponding heading text if available (logo_1 uses Heading_1, etc.)
                    heading_text = None
                    if name.startswith('logo_') or name.startswith('logo'):
                        # Extract number from logo_1, logo_2, etc. or logo2, logo3, etc.
                        import re
                        match = re.search(r'logo[_\s]?(\d+)', name, re.IGNORECASE)
                        if match:
                            heading_num = match.group(1)
                            heading_key = f'Heading_{heading_num}'
                            heading_text = content_map.get(heading_key)
                            if heading_text:
                                self.logger.debug(f"Found corresponding {heading_key}: {heading_text} for {name}")
                    
                    # Call deterministic selection function
                    try:
                        emoji_content = self.content_generator.select_emoji_deterministic(
                            project_name=project_name or f"{context} Project",
                            project_description=project_description or "",
                            placeholder_name=name,
                            heading_text=heading_text
                        )
                        
                        # Validate (should always be single character)
                        if len(emoji_content) == 1:
                            text_map[name] = emoji_content
                            self.logger.info(f"Selected emoji for {name}: {emoji_content}")
                        else:
                            # Should never happen, but safety check
                            from backend.core.generator import FALLBACK_EMOJIS
                            fallback = FALLBACK_EMOJIS.get(name, '🚀')
                            text_map[name] = fallback
                            self.logger.error(f"Invalid emoji generated for {name}, using fallback: {fallback}")
                    except Exception as e:
                        self.logger.warning(f"Emoji selection failed for {name}: {e}")
                        # Use fallback
                        from backend.core.generator import FALLBACK_EMOJIS
                        fallback = FALLBACK_EMOJIS.get(name, '🚀')
                        text_map[name] = fallback
            else:
                # Only add to text_map if it's not an image placeholder
                # Also check for u0022 placeholder (which has full placeholder text as key)
                # Skip hyperlinked placeholders - they're already processed in Step 4.1
                try:
                    from config import HYPERLINKED_PLACEHOLDERS
                except Exception:
                    HYPERLINKED_PLACEHOLDERS = {}
                
                if name in content_map and name not in ['logo', 'companyLogo', 'image_1', 'image_2', 'image_3', 'chart_1', 'backgroundImage']:
                    if name in HYPERLINKED_PLACEHOLDERS:
                        self.logger.debug(f"Skipping '{name}' from text_map - already hyperlinked in Step 4.1")
                    else:
                        text_map[name] = content_map[name]
            
            # Special handling for u0022 quote placeholder
            # Check if there's a u0022 entry in content_map that needs to be added
            for key in content_map.keys():
                if 'u0022' in key and key not in text_map and 'u0022' in key:
                    text_map[key] = content_map[key]
                    self.logger.info(f"Added u0022 placeholder {key} to text_map")
        
        # Ensure effort estimation placeholders always get text replacements (special characters can break detection)
        if 'effort_estimation_?' in content_map:
            text_map['effort_estimation_?'] = content_map['effort_estimation_?']
        if 'effort_estimation_q' in content_map:
            text_map['effort_estimation_q'] = content_map['effort_estimation_q']

        for name, slide_id, element_id in image_targets:
            if name in ['image_1', 'backgroundImage']:
                continue  # Skip these as they're handled separately
            
            # Skip if already processed
            if name in processed_images:
                self.logger.debug(f"Skipping already processed image: {name}")
                continue
                
            try:
                # Find dimensions for this placeholder
                placeholder_dimensions = None
                for ph in detected:
                    if ph.get('name') == name and ph.get('element_id') == element_id:
                        if ph.get('size'):
                            size = ph['size']
                            width = size.get('width', {}).get('magnitude')
                            height = size.get('height', {}).get('magnitude')
                            # Validate dimensions - reject obviously invalid values (like 3000000)
                            if width and height:
                                # Convert EMU to PT if needed (1 inch = 914400 EMU = 72 PT, so 1 EMU = 72/914400 PT)
                                # But if values are > 10000, they're likely EMU, otherwise assume PT
                                if width > 10000 or height > 10000:
                                    # Likely EMU, convert to PT
                                    width = float(width) / 914400 * 72
                                    height = float(height) / 914400 * 72
                                    self.logger.debug(f"Converted {name} dimensions from EMU to PT: {width}x{height}")
                                else:
                                    width = float(width)
                                    height = float(height)
                                
                                # Validate reasonable dimensions (reject if > 1000 PT which is ~14 inches)
                                if width > 0 and height > 0 and width < 1000 and height < 1000:
                                    placeholder_dimensions = {
                                        'width': width,
                                        'height': height,
                                        'unit': 'PT'
                                    }
                                    self.logger.debug(f"Detected dimensions for {name}: {width}x{height} PT")
                                else:
                                    self.logger.warning(f"Invalid dimensions detected for {name}: {width}x{height} PT, using manual/default")
                            break
                # Prefer manual override by placeholder name
                if MANUAL_CROP_DIMS.get(name):
                    placeholder_dimensions = _normalize_dims(MANUAL_CROP_DIMS.get(name))
                    self.logger.info(f"Using MANUAL_CROP_DIMS for {name}: {placeholder_dimensions}")
                
                is_company_logo = name.lower() == 'companylogo' or name.lower().startswith('companylogo_')
                if is_company_logo:
                    self.logger.info(f"⏭️ Skipping automatic generation for {name}. Provide a custom logo via overrides to replace this placeholder.")
                    continue
                
                image_path, image_crop, _ = self.content_generator.generate_image(
                    placeholder_type=name,
                    context=context,
                    company_name=company_name or context,
                    project_name=project_name or f"{context} Project",
                    project_description=project_description,
                    image_requirements=None,
                    theme=theme,
                    placeholder_dimensions=placeholder_dimensions
                )
                
                if image_path and os.path.exists(image_path):
                    # Replace - exact handling for companyLogo is done automatically in replace_image_placeholder
                    success = self.slides_client.replace_image_placeholder(
                        target_id,
                        f"{{{{{name}}}}}",
                        image_path,
                        slide_id=slide_id,
                        crop_properties=None,  # No crop needed - exact replacement handles sizing
                        target_dimensions=placeholder_dimensions  # Pass for reference (companyLogo uses exact method)
                    )
                    
                    if success:
                        processed_images.add(name)
                        self.logger.info(f"Successfully replaced image placeholder: {name}")
                    else:
                        self.logger.warning(f"Failed to replace {name} placeholder")
            except Exception as e:
                self.logger.warning(f"Image replacement failed for {name}: {e}")

        # Add any u0022 entries from content_map to text_map before replacement
        # Also check detected placeholders directly to ensure we have it
        u0022_found = False
        for ph in detected:
            if ph.get('is_quote') and ph.get('name') == 'u0022':
                placeholder_text = ph.get('placeholder', '')
                if placeholder_text in content_map:
                    text_map[placeholder_text] = content_map[placeholder_text]
                    u0022_found = True
                    self.logger.info(f"✅ Found u0022 in detected placeholders, added to text_map: '{placeholder_text}' → '{content_map[placeholder_text]}'")
                    break
        
        # Fallback: check content_map for any u0022 keys
        if not u0022_found:
            for key in list(content_map.keys()):
                if 'u0022' in key and key not in text_map:
                    text_map[key] = content_map[key]
                    self.logger.info(f"✅ Adding u0022 placeholder '{key}' with value '{content_map[key]}' to text_map (fallback)")
        
        # Note: Hyperlinks are already processed in Step 4.1 (before any content replacement)
        # This ensures placeholders are found and hyperlinked before they get replaced with content

        # Replace text placeholders (excluding already hyperlinked ones)
        if text_map:
            self.logger.info(f"📝 About to replace {len(text_map)} placeholders: {list(text_map.keys())}")
            self.slides_client.replace_placeholders(target_id, text_map)
            
            # Format bullets for conclusion_para if it contains bullet markers
            # Using dedicated function to avoid affecting other components
            if 'conclusion_para' in text_map:
                conclusion_content = text_map['conclusion_para']
                # Check if content contains bullet markers
                if '* ' in conclusion_content:
                    self.logger.info("🔍 conclusion_para contains bullet markers, formatting bullets...")
                    # Find the element containing conclusion_para content using dedicated function
                    element_info = self.slides_client.find_conclusion_para_element(target_id, conclusion_content)
                    
                    if element_info:
                        # Format bullets
                        success = self.slides_client.format_bullets_for_element(
                            target_id,
                            element_info['element_id'],
                            element_info['slide_id'],
                            bullet_marker='* '
                        )
                        if success:
                            self.logger.info("✅ Successfully formatted bullets for conclusion_para")
                        else:
                            self.logger.warning("⚠️ Failed to format bullets for conclusion_para")
                    else:
                        self.logger.warning("⚠️ Could not find element containing conclusion_para content")

        # Apply theme-based styling if available
        if theme:
            self.logger.debug("Applying theme styling...")
            text_styling_map = self._create_text_styling_map(placeholders_for_matcher, theme)
            if text_styling_map:
                self.slides_client.apply_text_styling(target_id, text_styling_map, theme)
            
            # Apply special styling for "Project" and "Overview" text elements
            self._apply_special_text_styling(target_id, theme)

        token_usage_summary = None
        if hasattr(self, 'content_generator'):
            token_usage_summary = self.content_generator.get_token_usage_summary()
            self.logger.info(
                f"🧮 Token usage this run → prompt: {token_usage_summary['prompt_tokens']}, "
                f"candidates: {token_usage_summary['candidates_tokens']}, "
                f"total: {token_usage_summary['total_tokens']}"
            )

        presentation_url = self.slides_client.get_presentation_url(target_id)
        return {
            'success': True,
            'presentation_id': target_id,
            'presentation_url': presentation_url,
            'placeholders_replaced': len(text_map) + len(image_targets),
            'token_usage': token_usage_summary
        }
    
    def generate_presentation(self, context, template_id=None, output_title=None, image_overrides=None, 
                            profile=None, project_name=None, project_description=None, company_name=None, proposal_type=None, company_website=None,
                            sheets_id=None, sheets_range=None, primary_color=None, secondary_color=None, accent_color=None):
        """Generate a complete presentation from template"""
        def _normalize_dims(dims):
            if not dims:
                return None
            unit = str(dims.get('unit') or 'PT').upper()
            width = dims.get('width')
            height = dims.get('height')
            if unit in ('IN', 'INCH', 'INCHES'):
                try:
                    return {'width': float(width) * 72.0, 'height': float(height) * 72.0, 'unit': 'PT'}
                except Exception:
                    return dims
            return dims
        if not template_id:
            template_id = TEMPLATE_PRESENTATION_ID
        
        if not template_id:
            raise ValueError("No template presentation ID provided")
        
        self.logger.info(f"Starting presentation generation for: {context}")

        if hasattr(self, 'content_generator'):
            self.content_generator.reset_token_usage()
        
        # Duplicate the template deck using Drive (reliable way to clone all slides)
        working_title = output_title or f"{company_name or context} - Generated"
        new_presentation_id = self.slides_client.copy_presentation(template_id, working_title)
        if not new_presentation_id:
            return {
                'success': False,
                'error': 'COPY_FAILED',
                'message': 'Could not copy the template. Ensure the template ID/URL is correct and shared with the authorized account.',
                'token_usage': self.content_generator.get_token_usage_summary() if hasattr(self, 'content_generator') else None
            }
        target_id = new_presentation_id

        # ============================================================================
        # STEP 1: INITIAL ANALYSIS - Find placeholders in template
        # ============================================================================
        self.logger.info("📊 Step 1: Analyzing template for placeholders...")
        placeholders = self.slides_client.find_placeholders(target_id)
        
        if not placeholders:
            self.logger.error("No placeholders found in template")
            return None
        self.logger.info(f"Found {len(placeholders)} placeholders in initial analysis")

        # ============================================================================
        # STEP 2: IDENTIFY MAX SIDE_HEADING - Find the maximum side_Heading number
        # Priority: Check project_description first, then fall back to template detection
        # ============================================================================
        self.logger.info("🔍 Step 2: Identifying maximum side_Heading number...")
        
        # First, check if project_description specifies any side_Headings
        # This takes priority over template detection
        max_side_heading_from_description = 0
        if project_description:
            side_heading_overrides = self._extract_side_headings_from_description(project_description)
            if side_heading_overrides:
                # Find max from description overrides
                import re
                pattern = re.compile(r'^side_Heading_(\d+)$', re.IGNORECASE)
                for key in side_heading_overrides.keys():
                    match = pattern.match(key)
                    if match:
                        number = int(match.group(1))
                        max_side_heading_from_description = max(max_side_heading_from_description, number)
                if max_side_heading_from_description > 0:
                    self.logger.info(f"📝 Found side_Headings in project description: max = {max_side_heading_from_description}")
        
        # Log all detected side_Headings from template for debugging
        import re
        pattern = re.compile(r'^side_Heading_(\d+)$', re.IGNORECASE)
        detected_side_headings = []
        for ph in placeholders:
            name = ph.get('name') or ph.get('placeholder', '')
            if name:
                match = pattern.match(name)
                if match:
                    number = int(match.group(1))
                    detected_side_headings.append((number, name))
        
        if detected_side_headings:
            detected_side_headings.sort()
            self.logger.info(f"📋 Template contains side_Heading placeholders: {[f'side_Heading_{num}' for num, _ in detected_side_headings]}")
        
        max_side_heading_from_template = self._find_max_side_heading_number(placeholders)
        
        # Use description max if provided, otherwise use template max
        if max_side_heading_from_description > 0:
            max_side_heading = max_side_heading_from_description
            self.logger.info(f"✓ Using maximum side_Heading from project description: {max_side_heading} (template has up to {max_side_heading_from_template})")
        elif max_side_heading_from_template > 0:
            max_side_heading = max_side_heading_from_template
            self.logger.info(f"✓ Maximum side_Heading identified from template: {max_side_heading}")
        else:
            max_side_heading = 0
            self.logger.info("No side_Heading placeholders found - skipping slide deletion")

        # ============================================================================
        # STEP 3: DELETE EXCESS SLIDES - Remove slides with side_Headings beyond max
        # ============================================================================
        if max_side_heading > 0:
            self.logger.info(f"🗑️  Step 3: Identifying and deleting slides with side_Headings beyond {max_side_heading}...")
            slides_to_delete = self._find_slides_to_delete_for_side_headings(placeholders, max_side_heading)
            
            if slides_to_delete:
                self.logger.info(f"📋 Found {len(slides_to_delete)} slide(s) to delete: {list(slides_to_delete)}")
                delete_success = self.slides_client.delete_slides(target_id, list(slides_to_delete))
                
                if delete_success:
                    self.logger.info(f"✅ Successfully deleted {len(slides_to_delete)} slide(s)")
                else:
                    self.logger.error(f"❌ Failed to delete slides. Continuing with existing slides.")
                
                # Re-analyze after deletion to get clean placeholder list
                self.logger.info("🔄 Re-analyzing presentation after slide deletion...")
                placeholders = self.slides_client.find_placeholders(target_id)
                self.logger.info(f"✓ Re-analysis complete: {len(placeholders)} placeholders remaining")
                
                # Verify deletion was successful
                remaining_max = self._find_max_side_heading_number(placeholders)
                if remaining_max <= max_side_heading:
                    self.logger.info(f"✓ Verified: Maximum side_Heading after deletion is {remaining_max} (within limit)")
                else:
                    self.logger.warning(f"⚠️ Warning: Maximum side_Heading after deletion is {remaining_max} (expected <= {max_side_heading})")
            else:
                self.logger.info(f"✓ No slides to delete - all side_Headings are within range 1-{max_side_heading}")

        # ============================================================================
        # STEP 4: CONTINUE WITH CONTENT GENERATION - Process cleaned presentation
        # ============================================================================
        self.logger.info("🚀 Step 4: Proceeding with content generation...")
        
        placeholder_types = list(set([p['placeholder'] for p in placeholders]))
        self.logger.debug(f"Found placeholders: {placeholder_types}")
        
        # Step 2: Match placeholders and generate content
        self.logger.debug("Matching placeholders with predefined mappings...")
        match_result = self.placeholder_matcher.match_placeholders(placeholders)
        self.logger.info(f"✅ Matched {match_result['total_matched']}/{match_result['total_found']} placeholders")
        
        # ============================================================================
        # STEP 4.1: PROCESS HYPERLINKED PLACEHOLDERS IMMEDIATELY AFTER MATCHING
        # ============================================================================
        try:
            from config import HYPERLINKED_PLACEHOLDERS, GOOGLE_SHEETS_ID
        except Exception as e:
            self.logger.error(f"❌ Error importing HYPERLINKED_PLACEHOLDERS: {e}")
            HYPERLINKED_PLACEHOLDERS = {}
            GOOGLE_SHEETS_ID = None

        self.logger.info(f"🔗 Step 4.1: Checking for hyperlinked placeholders: HYPERLINKED_PLACEHOLDERS={list(HYPERLINKED_PLACEHOLDERS.keys()) if HYPERLINKED_PLACEHOLDERS else 'None'}")
        self.logger.info(f"🔗 Step 4.1: HYPERLINKED_PLACEHOLDERS type: {type(HYPERLINKED_PLACEHOLDERS)}, length: {len(HYPERLINKED_PLACEHOLDERS) if HYPERLINKED_PLACEHOLDERS else 0}")
        
        sheet_url = None
        self.logger.info(f"🔗 Step 4.1: Checking sheets_reader: {self.sheets_reader is not None}")
        if self.sheets_reader:
            sheets_id_to_use = sheets_id or GOOGLE_SHEETS_ID
            self.logger.info(f"📊 Sheets ID check: sheets_id={sheets_id}, GOOGLE_SHEETS_ID={GOOGLE_SHEETS_ID}, sheets_id_to_use={sheets_id_to_use}")
            if sheets_id_to_use:
                try:
                    sheet_url = self.sheets_reader.get_sheet_url(sheets_id_to_use)
                    self.logger.info(f"📎 Generated sheet URL: {sheet_url}")
                except Exception as e:
                    self.logger.error(f"❌ Error generating sheet URL: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                self.logger.warning("⚠️ No Google Sheets ID provided - hyperlinks will not be created")
        else:
            self.logger.warning("⚠️ SheetsReader not initialized - hyperlinks will not be created")
        
        self.logger.info(f"🔗 Step 4.1: Final check - sheet_url={sheet_url is not None}, HYPERLINKED_PLACEHOLDERS={bool(HYPERLINKED_PLACEHOLDERS)}")

        # Extract URLs and "Follow Reference Link" text from project description for follow_reference_link placeholders
        def extract_urls_from_description(description):
            """Extract URLs from project description using regex"""
            import re
            if not description:
                return []
            # Pattern to match http://, https://, or www. URLs
            url_pattern = r'(https?://[^\s<>"{}|\\^`\[\]]+|www\.[^\s<>"{}|\\^`\[\]]+)'
            urls = re.findall(url_pattern, description)
            # Ensure URLs starting with www. have http:// prefix
            urls = [url if url.startswith('http') else f'https://{url}' for url in urls]
            return urls

        def extract_link_text_from_description(description):
            """Extract 'Follow Reference Link' text from project description if present"""
            if not description:
                return None
            import re
            # Look for "Follow Reference Link" (case-insensitive, allowing variations)
            pattern = r'Follow\s+Reference\s+Link'
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                # Return the exact matched text (preserving original case)
                return match.group(0)
            return None

        description_urls = extract_urls_from_description(project_description) if project_description else []
        link_display_text = extract_link_text_from_description(project_description) if project_description else None
        
        # Use extracted text if found, otherwise fall back to default
        if link_display_text:
            self.logger.info(f"🔗 Step 4.1: Extracted link display text from project description: '{link_display_text}'")
        else:
            link_display_text = 'Follow Reference Link'
            self.logger.info(f"🔗 Step 4.1: Using default link display text: '{link_display_text}'")
        
        self.logger.info(f"🔗 Step 4.1: Extracted {len(description_urls)} URL(s) from project description: {description_urls}")

        if HYPERLINKED_PLACEHOLDERS:
            # Separate follow_reference_link placeholders from others
            follow_reference_placeholders = {}
            other_placeholders = {}
            
            for placeholder_name, cfg in HYPERLINKED_PLACEHOLDERS.items():
                if cfg.get('extract_from_description', False):
                    follow_reference_placeholders[placeholder_name] = cfg
                else:
                    other_placeholders[placeholder_name] = cfg

            # Check all detected placeholders (matched and unmatched) for hyperlinked ones
            all_placeholder_names = [p.get('name') or p.get('placeholder', '') for p in placeholders if p.get('name') or p.get('placeholder')]
            self.logger.info(f"🔗 Step 4.1: Found {len(all_placeholder_names)} total placeholder names in presentation")
            self.logger.debug(f"🔗 Step 4.1: All placeholder names: {all_placeholder_names}")

            # Process follow_reference_link placeholders (use URLs from description)
            if follow_reference_placeholders:
                self.logger.info(f"🔗 Step 4.1: Processing {len(follow_reference_placeholders)} follow_reference_link placeholders from project description...")
                # Sort by placeholder number to ensure correct URL mapping
                sorted_placeholders = sorted(
                    follow_reference_placeholders.items(),
                    key=lambda x: int(x[0].split('_')[-1]) if x[0].split('_')[-1].isdigit() else 999
                )
                for placeholder_name, cfg in sorted_placeholders:
                    if placeholder_name not in all_placeholder_names:
                        self.logger.warning(f"⚠️ Step 4.1: Placeholder '{placeholder_name}' not found in presentation")
                        continue
                    
                    # Extract number from placeholder name (e.g., "follow_reference_link_1" -> 1)
                    try:
                        placeholder_num = int(placeholder_name.split('_')[-1])
                    except (ValueError, IndexError):
                        self.logger.warning(f"⚠️ Step 4.1: Could not extract number from placeholder '{placeholder_name}', skipping")
                        continue
                    
                    # Get URL from description (1-indexed: link_1 -> urls[0], link_2 -> urls[1], etc.)
                    url_index = placeholder_num - 1
                    if url_index < len(description_urls):
                        url = description_urls[url_index]
                        # Use extracted text from description if available, otherwise use config default
                        display_text = link_display_text or cfg.get('text', 'Follow Reference Link')
                        placeholder_text = f"{{{{{placeholder_name}}}}}"
                        
                        # Get color from primary_color/secondary_color parameters or theme
                        color = None
                        if placeholder_num <= 3:  # Links 1-3 use primary color
                            color = primary_color or '#2563eb'
                        else:  # Links 4-6 use secondary color
                            color = secondary_color or '#1e40af'
                        
                        self.logger.info(f"🔗 Step 4.1: Adding hyperlink: '{placeholder_name}' -> '{display_text}' -> {url} (color: {color})")
                        try:
                            success = self.slides_client.add_hyperlink_to_placeholder(
                                target_id,
                                placeholder_text,
                                display_text,
                                url,
                                color=color
                            )
                            if success:
                                self.logger.info(f"✅ Step 4.1: Successfully added hyperlink for '{placeholder_name}'")
                            else:
                                self.logger.warning(f"⚠️ Step 4.1: Failed to add hyperlink for '{placeholder_name}'")
                        except Exception as e:
                            self.logger.error(f"❌ Step 4.1: Exception adding hyperlink for '{placeholder_name}': {e}")
                            import traceback
                            traceback.print_exc()
                    else:
                        self.logger.warning(f"⚠️ Step 4.1: No URL available for '{placeholder_name}' (index {url_index}, found {len(description_urls)} URLs)")

            # Process other hyperlinked placeholders (use sheet URL)
            if other_placeholders and sheet_url:
                self.logger.info(f"🔗 Step 4.1: Processing {len(other_placeholders)} hyperlinked placeholders (standard mode)...")
                for placeholder_name, cfg in other_placeholders.items():
                    # Always try to add hyperlink - let add_hyperlink_to_placeholder search for the placeholder text
                    # This handles cases where the name might not match exactly in all_placeholder_names
                    display_text = cfg.get('text', placeholder_name)
                    placeholder_text = f"{{{{{placeholder_name}}}}}"
                    self.logger.info(f"🔗 Step 4.1: Attempting to add hyperlink for '{placeholder_name}' -> '{display_text}' -> {sheet_url}")
                    
                    # Log if placeholder name is in detected list for debugging
                    if placeholder_name in all_placeholder_names:
                        self.logger.debug(f"🔗 Step 4.1: Placeholder '{placeholder_name}' found in detected placeholders")
                    else:
                        self.logger.debug(f"🔗 Step 4.1: Placeholder '{placeholder_name}' not in detected list, but will search for '{placeholder_text}' directly")
                    
                    try:
                        success = self.slides_client.add_hyperlink_to_placeholder(
                            target_id,
                            placeholder_text,
                            display_text,
                            sheet_url
                        )
                        
                        if success:
                            self.logger.info(f"✅ Step 4.1: Successfully added hyperlink for '{placeholder_name}'")
                        else:
                            self.logger.warning(f"⚠️ Step 4.1: Failed to add hyperlink for '{placeholder_name}' - placeholder text '{placeholder_text}' not found in presentation")
                    except Exception as e:
                        self.logger.error(f"❌ Step 4.1: Exception adding hyperlink for '{placeholder_name}': {e}")
                        import traceback
                        traceback.print_exc()
            elif other_placeholders and not sheet_url:
                self.logger.warning("⚠️ Step 4.1: No Google Sheets URL available - skipping standard hyperlink processing")
        else:
            if not HYPERLINKED_PLACEHOLDERS:
                self.logger.warning("⚠️ Step 4.1: No hyperlinked placeholders configured")
        
        if match_result['unmatched']:
            self.logger.warning("=" * 80)
            self.logger.warning("📋 UNMATCHED PLACEHOLDERS REPORT")
            self.logger.warning("=" * 80)
            self.logger.warning(f"⚠️ Total unmatched: {len(match_result['unmatched'])}")
            self.logger.warning("")
            self.logger.warning("Unmatched placeholders list:")
            self.logger.warning("-" * 80)
            
            # Group by slide for better organization
            unmatched_by_slide = {}
            unmatched_names = []
            
            for unmatched in match_result['unmatched']:
                if isinstance(unmatched, dict):
                    name = unmatched.get('name', 'unknown')
                    placeholder = unmatched.get('placeholder', 'unknown')
                    slide_id = unmatched.get('slide_id', 'unknown')
                    element_id = unmatched.get('element_id', 'unknown')
                    
                    unmatched_names.append(name)
                    
                    if slide_id not in unmatched_by_slide:
                        unmatched_by_slide[slide_id] = []
                    unmatched_by_slide[slide_id].append({
                        'name': name,
                        'placeholder': placeholder,
                        'element_id': element_id
                    })
                else:
                    unmatched_names.append(str(unmatched))
            
            # Display by slide
            for slide_id, items in unmatched_by_slide.items():
                self.logger.warning(f"Slide ID: {slide_id}")
                for item in items:
                    self.logger.warning(f"  • Name: {item['name']}")
                    self.logger.warning(f"    Placeholder: {item['placeholder']}")
                    self.logger.warning(f"    Element ID: {item['element_id']}")
                self.logger.warning("")
            
            # Display simple list for easy copy-paste
            self.logger.warning("-" * 80)
            self.logger.warning("Quick reference (comma-separated):")
            self.logger.warning(f"  {', '.join(unmatched_names)}")
            self.logger.warning("")
            self.logger.warning("=" * 80)
        
        # Pre-seed content_map: Google Sheets data (highest priority), then description overrides
        content_map = {}
        
        # Fetch data from Google Sheets if configured (MUST BE FIRST - highest priority)
        self.logger.info("=" * 80)
        self.logger.info("📊 CHECKING GOOGLE SHEETS DATA FETCH (generate_presentation)")
        self.logger.info("=" * 80)
        self.logger.info(f"🔍 sheets_reader exists: {self.sheets_reader is not None}")
        self.logger.info(f"🔍 sheets_id provided: {sheets_id is not None} (value: {sheets_id})")
        self.logger.info(f"🔍 sheets_range provided: {sheets_range is not None} (value: {sheets_range})")
        
        if self.sheets_reader:
            self.logger.info("✅ sheets_reader is available - proceeding to fetch data")
            try:
                self.logger.info(f"📥 Calling fetch_placeholder_values with sheets_id={sheets_id}, sheets_range={sheets_range}")
                sheet_data = self.sheets_reader.fetch_placeholder_values(
                    sheets_id=sheets_id,
                    sheets_range=sheets_range,
                )
                self.logger.info(f"📊 fetch_placeholder_values returned: {type(sheet_data)}, length: {len(sheet_data) if sheet_data else 0}")
                
                if sheet_data:
                    for k, v in sheet_data.items():
                        content_map[k] = v
                        self.logger.info(f"📋 Added to content_map: {k} = {v}")
                        if k.startswith(('p_r_', 's_r_', 'pr_desc_', 'sr_desc_')):
                            self.logger.info(f"🧾 Content map update (Sheets/AI mapping): {k} = {v}")
                    self.logger.info(f"✅ Using {len(sheet_data)} values from Google Sheets (including Gemini analysis)")
                else:
                    self.logger.warning("⚠️ fetch_placeholder_values returned empty dict - no data from Sheets")
            except Exception as e:
                self.logger.error(f"❌ EXCEPTION fetching from Google Sheets: {e}")
                import traceback
                self.logger.error(traceback.format_exc())
        else:
            self.logger.warning("⚠️ sheets_reader is None - cannot fetch Google Sheets data")
            self.logger.warning("   This means SheetsReader was not initialized properly")
        
        self.logger.info("=" * 80)
        
        # Generate content for matched placeholders
        self.logger.debug("Generating AI content...")
        
        # Try comprehensive content generation first
        comprehensive_content = None
        if self.use_ai:
            try:
                self.logger.info("Attempting comprehensive content generation...")
                comprehensive_content = self.content_generator.generate_comprehensive_content(
                    project_name=project_name or f"{context} Project",
                    company_name=company_name or context,
                    project_description=project_description or context,
                    context=context,
                    detected_placeholders=placeholders,
                    preset_values=content_map
                )
                
                if comprehensive_content:
                    self.logger.info(f"✅ Successfully generated comprehensive content with {len(comprehensive_content)} placeholders")
                    # Map comprehensive content to actual placeholder names
                    mapped_content = self.content_generator._map_comprehensive_to_placeholders(
                        comprehensive_content, placeholders
                    )
                    # Don't overwrite Google Sheets data (highest priority)
                    # EXCEPT for side_Heading and side_Head which may have been split
                    added = 0
                    overwritten = 0
                    for k, v in mapped_content.items():
                        # Allow overwriting side_Heading and side_Head placeholders (they may have been split)
                        if k.startswith('side_Heading_') or k.startswith('side_Head_'):
                            if k in content_map:
                                self.logger.info(f"🔄 Overwriting {k}: '{content_map[k]}' → '{v}' (split content)")
                                overwritten += 1
                            content_map[k] = v
                            added += 1
                        elif k not in content_map:  # Only add if not already from Sheets
                            content_map[k] = v
                            added += 1
                    self.logger.info(f"Mapped comprehensive content to {added} placeholders ({overwritten} overwritten) without overwriting Sheets data")
                else:
                    self.logger.warning("Comprehensive content generation failed, falling back to individual generation")
            except Exception as e:
                self.logger.error(f"Comprehensive content generation error: {e}")
                self.logger.info("Falling back to individual content generation")
        
        # Pre-seed content_map with side_heading overrides parsed from project_description
        # (content_map already initialized above with Google Sheets data)
        side_heading_overrides = self._extract_side_headings_from_description(project_description)
        if side_heading_overrides:
            self.logger.info(f"Using side_heading overrides from description: {list(side_heading_overrides.keys())}")
            # Only include keys that are actually present in this template
            available = {ph['placeholder'] for ph in placeholders}
            for key, val in side_heading_overrides.items():
                if key in available and key not in content_map:
                    content_map[key] = val
            
            # Split side_Heading content between side_Heading_X and side_Head_X if both exist
            content_map = self._split_side_headings(content_map, available)

        # Also parse generic placeholder overrides from description
        available_keys = {ph['placeholder'] for ph in placeholders}
        generic_overrides = self._extract_placeholder_overrides_from_description(project_description or '', available_keys)
        if generic_overrides:
            used = []
            for k, v in generic_overrides.items():
                if k in available_keys and k not in content_map:
                    content_map[k] = v
                    used.append(k)
            if used:
                self.logger.info(f"Using description overrides: {used}")

        # If comprehensive generation failed or not used, fall back to individual generation
        if not comprehensive_content:
            # First pass: Generate Heading placeholders sequentially since they reference each other
            heading_order = ['Heading_1', 'Heading_2', 'Heading_3', 'Heading_4', 'Heading_5', 'Heading_6']
            generated_headings = {}
            
            # Generate each heading in order
            for heading_name in heading_order:
                # Check if this heading is in placeholders
                if any(ph.get('placeholder') == heading_name for ph in placeholders):
                    try:
                        heading_content = self.content_generator.generate_content(
                            placeholder_type=heading_name,
                            context=context,
                            company_name=company_name or context,
                            project_name=project_name or f"{context} Project",
                            project_description=project_description,
                            previous_headings=generated_headings
                        )
                        generated_headings[heading_name] = heading_content
                        # Find all instances of this heading in placeholders
                        for ph in placeholders:
                            if ph.get('placeholder') == heading_name:
                                content_map[heading_name] = heading_content
                        self.logger.info(f"✓ Generated {heading_name}: {heading_content}")
                    except Exception as e:
                        self.logger.error(f"Failed to generate {heading_name}: {e}")
            
            # Generate paragraph placeholders with access to their corresponding headings
            para_order = ['Head1_para', 'Head2_para', 'Head3_para', 'Head4_para', 'Head5_para', 'Head6_para']
            for para_name in para_order:
                # Check if this para is in placeholders
                if any(ph.get('placeholder') == para_name for ph in placeholders):
                    try:
                        # Get corresponding heading (e.g., Head1_para -> Heading_1)
                        heading_number = para_name.replace('Head', '').replace('_para', '')
                        corresponding_heading_name = f'Heading_{heading_number}'
                        corresponding_heading_content = generated_headings.get(corresponding_heading_name, '')
                        
                        # Generate para with heading context
                        para_content = self.content_generator.generate_content(
                            placeholder_type=para_name,
                            context=context,
                            company_name=company_name or context,
                            project_name=project_name or f"{context} Project",
                            project_description=project_description,
                            heading_content=corresponding_heading_content
                        )
                        
                        # Find all instances of this para in placeholders
                        content_map[para_name] = para_content
                        self.logger.info(f"✓ Generated {para_name} (based on {corresponding_heading_name}): {para_content}")
                    except Exception as e:
                        self.logger.error(f"Failed to generate {para_name}: {e}")
            
            # Auto-fill known placeholders BEFORE calling placeholder matcher
            # This ensures UI-provided values are used instead of AI generation
            if 'projectName' in placeholder_types:
                if project_name:
                    # Use the exact project name provided by user
                    content_map['projectName'] = project_name
                elif profile == 'company':
                    content_map['projectName'] = f"{context} Project"
            if 'companyName' in placeholder_types:
                if company_name:
                    content_map['companyName'] = company_name
                elif profile == 'company':
                    content_map['companyName'] = context
            if 'proposalName' in placeholder_types:
                # Use proposal_type from UI input, not AI generation
                if proposal_type:
                    content_map['proposalName'] = proposal_type
                else:
                    # Use default proposal type
                    content_map['proposalName'] = 'Project Proposal'
                self.logger.info(f"✅ Using UI input for proposalName: '{content_map['proposalName']}'")
            
            # Set property values based on project description analysis (not AI-generated)
            if any(prop in placeholder_types for prop in ['property1', 'property2', 'property3', 'property_1', 'property_2', 'property_3']):
                prop1_val, prop2_val, prop3_val = self._select_property_set(project_description)
                
                if 'property1' in placeholder_types or 'property_1' in placeholder_types:
                    content_map['property1'] = prop1_val
                    if 'property_1' in placeholder_types:
                        content_map['property_1'] = prop1_val
                    self.logger.info(f"✅ Set property1 based on project description: '{prop1_val}'")
                if 'property2' in placeholder_types or 'property_2' in placeholder_types:
                    content_map['property2'] = prop2_val
                    if 'property_2' in placeholder_types:
                        content_map['property_2'] = prop2_val
                    self.logger.info(f"✅ Set property2 based on project description: '{prop2_val}'")
                if 'property3' in placeholder_types or 'property_3' in placeholder_types:
                    content_map['property3'] = prop3_val
                    if 'property_3' in placeholder_types:
                        content_map['property_3'] = prop3_val
                    self.logger.info(f"✅ Set property3 based on project description: '{prop3_val}'")
            
            # Generate remaining placeholders that aren't headings or paras
            remaining_content = self.placeholder_matcher.generate_content_for_placeholders(
                match_result['matched'], 
                context, 
                company_name, 
                project_name,
                project_description,
                existing_content=content_map
            )
            content_map.update(remaining_content)
        
        # Initialize final_image_map
        final_image_map = image_overrides or {}
        
        # Generate company theme if in company mode - based on user colors or company name (no logo analysis)
        theme = None
        logo_path = None
        
        if profile == 'company' and (company_name or context):
            try:
                # Priority 1: Use user-provided colors if available
                if primary_color or secondary_color or accent_color:
                    self.logger.info("=" * 80)
                    self.logger.info("✓ USER COLORS DETECTED - No logo analysis will be performed")
                    self.logger.info(f"Input colors: Primary={primary_color}, Secondary={secondary_color}, Accent={accent_color}")
                    self.logger.info("=" * 80)
                    theme = {
                        "primary_color": primary_color or '#2563eb',
                        "secondary_color": secondary_color or '#1e40af',
                        "accent_color": accent_color or '#3b82f6',
                        "brand_personality": 'professional',
                        "target_audience": 'B2B',
                        "industry": 'General',
                        "theme_description": f"Custom theme with user-provided colors for {company_name or context}",
                        "source": "user_provided_colors"
                    }
                    self.logger.info(f"✓ Theme generated from USER COLORS: Primary={theme['primary_color']}, Secondary={theme['secondary_color']}, Accent={theme['accent_color']}")
                else:
                    # Priority 2: Generate theme based on company name only (no logo extraction/analysis)
                    self.logger.info("⚠ No user colors provided - Generating theme from company name only (NO LOGO ANALYSIS)")
                    theme = self.content_generator.generate_company_theme_name_only(
                        company_name or context, 
                        project_name
                    )
                
                # Log theme details
                if theme:
                    self.logger.info(f"Theme: {theme.get('theme_description', 'Default theme')}")
                    self.logger.debug(f"Industry: {theme.get('industry', 'General')} | Brand: {theme.get('brand_personality', 'Professional')} | Audience: {theme.get('target_audience', 'B2B')}")
                    self.logger.debug(f"Colors: primary={theme.get('primary_color')}, secondary={theme.get('secondary_color')}, accent={theme.get('accent_color')}")
                    self.logger.debug(f"Theme source: {theme.get('source', 'unknown')}")
                    
            except Exception as e:
                self.logger.error(f"Theme generation failed: {e}")
                raise e
        
        # Step 3: Handle images
        self.logger.debug("Processing images...")
        image_map = image_overrides or {}

        # Generate image_1 first and store it for reuse
        image_1_path = None
        if 'image_1' in placeholder_types:
            try:
                # Find image_1 placeholder dimensions
                image_1_dimensions = None
                for ph in placeholders:
                    if ph['placeholder'] == 'image_1':
                        element = ph.get('element_properties', {})
                        size = element.get('size')
                        if size:
                            image_1_dimensions = {
                                'width': size.get('width', {}).get('magnitude'),
                                'height': size.get('height', {}).get('magnitude'),
                                'unit': size.get('width', {}).get('unit', 'PT')
                            }
                        break
                if MANUAL_CROP_DIMS.get('image_1'):
                    image_1_dimensions = _normalize_dims(MANUAL_CROP_DIMS.get('image_1'))
                
                image_1_path, image_1_crop, _ = self.content_generator.generate_image(
                    placeholder_type='image_1',
                    context=context,
                    company_name=company_name or context,
                    project_name=project_name or f"{context} Project",
                    project_description=project_description,
                    image_requirements=None,
                    theme=theme,
                    placeholder_dimensions=image_1_dimensions
                )
                if image_1_path and os.path.exists(image_1_path):
                    # Replace image_1 placeholder
                    self.slides_client.replace_image_placeholder(
                        target_id,
                        "{{image_1}}",
                        image_1_path,
                        crop_properties=image_1_crop,
                        target_dimensions=image_1_dimensions
                    )
                    self.logger.info("Successfully replaced image_1 placeholder")
            except Exception as e:
                self.logger.warning(f"Image_1 generation failed: {e}")

        # Background image: generate a themed background image
        if 'backgroundImage' in placeholder_types:
            try:
                # Get ACTUAL slide page size from presentation (not placeholder dimensions)
                presentation = self.slides_client.get_presentation(target_id)
                if presentation:
                    page_size = presentation.get('pageSize', {})
                    slide_width_emu = page_size.get('width', {}).get('magnitude', 9144000)  # Default: 10 inches in EMU
                    slide_height_emu = page_size.get('height', {}).get('magnitude', 5143500)  # Default: 5.625 inches in EMU
                    
                    # Convert EMU to PT (1 inch = 914400 EMU = 72 PT)
                    slide_width_pt = (slide_width_emu / 914400.0) * 72.0
                    slide_height_pt = (slide_height_emu / 914400.0) * 72.0
                    
                    bg_dimensions = {
                        'width': slide_width_pt,
                        'height': slide_height_pt,
                        'unit': 'PT'
                    }
                    self.logger.info(f"Using actual slide page size for background: {slide_width_pt:.2f} x {slide_height_pt:.2f} PT")
                else:
                    # Fallback to manual dimensions or placeholder dimensions
                    bg_dimensions = None
                    for ph in placeholders:
                        if ph['placeholder'] == 'backgroundImage':
                            element = ph.get('element_properties', {})
                            size = element.get('size')
                            if size:
                                bg_dimensions = {
                                    'width': size.get('width', {}).get('magnitude'),
                                    'height': size.get('height', {}).get('magnitude'),
                                    'unit': size.get('width', {}).get('unit', 'PT')
                                }
                            break
                    if MANUAL_CROP_DIMS.get('backgroundImage'):
                        bg_dimensions = _normalize_dims(MANUAL_CROP_DIMS.get('backgroundImage'))
                    self.logger.warning(f"Could not get slide page size, using fallback dimensions: {bg_dimensions}")
                
                # Generate a new themed background image using image_1 as reference
                # For generate_presentation (non-auto), check if we have image_1_original
                # If not, try to find it from the generated image_1
                image_1_original = None
                if image_1_path and os.path.exists(image_1_path):
                    # Try to find the original by replacing the filename pattern
                    base_dir = os.path.dirname(image_1_path)
                    base_name = os.path.basename(image_1_path)
                    # Look for _original version
                    original_name = base_name.replace('.jpg', '_original.jpg').replace('.png', '_original.jpg')
                    original_path = os.path.join(base_dir, original_name)
                    if os.path.exists(original_path):
                        image_1_original = original_path
                
                # Use the original uncropped image_1 to create backgroundImage
                if image_1_original and os.path.exists(image_1_original) and bg_dimensions:
                    self.logger.info(f"Creating backgroundImage from original image_1 copy (dimensions: {bg_dimensions})")
                    # Crop and resize to EXACT slide dimensions for proper background fit (no stretching)
                    bg_image_path = self.content_generator.crop_existing_image(
                        source_image_path=image_1_original,
                        target_dimensions=bg_dimensions,
                        output_filename=f"backgroundImage_{company_name.replace(' ', '_') if company_name else 'auto'}.jpg",
                        resize_to_exact=True  # Resize to exact slide dimensions after cropping
                    )
                    if bg_image_path and os.path.exists(bg_image_path):
                        self.slides_client.replace_image_placeholder(
                            target_id,
                            "{{backgroundImage}}",
                            bg_image_path,
                            crop_properties=None,
                            target_dimensions=bg_dimensions
                        )
                        self.logger.info("Successfully replaced backgroundImage placeholder using cropped and resized copy of image_1 to exact slide dimensions")
                    else:
                        self.logger.error("Background image cropping failed")
                        raise ValueError("Background image cropping failed")
                else:
                    self.logger.warning("image_1 original not available for backgroundImage, skipping")
            except Exception as e:
                self.logger.warning(f"Background image generation failed: {e}")
        # Skip image_1 here since it's already handled above

        # Step 4: Replace placeholders with generated content
        self.logger.debug("Replacing placeholders...")
        text_map = {}
        
        # Get hyperlinked placeholders to exclude them
        try:
            from config import HYPERLINKED_PLACEHOLDERS
        except Exception:
            HYPERLINKED_PLACEHOLDERS = {}
        
        # Separate text and image content
        for key, value in content_map.items():
            if key.startswith('IMAGE_'):
                # This is an image placeholder
                final_image_map[key] = value
            else:
                # Skip hyperlinked placeholders - they're already processed in Step 4.1
                if key in HYPERLINKED_PLACEHOLDERS:
                    self.logger.debug(f"Skipping '{key}' from text_map - already hyperlinked in Step 4.1")
                    continue
                # This is text content
                text_map[key] = value

        # Ensure numeric placeholders {{1}}..{{4}} are filled with their numeral if present in template
        for ph in placeholders:
            ph_name = ph['placeholder']
            if ph_name in ['1', '2', '3', '4'] and ph_name not in text_map:
                text_map[ph_name] = ph_name
        
        # Ensure effort estimation placeholders always get text replacements (special characters can break detection)
        if 'effort_estimation_?' in content_map:
            text_map['effort_estimation_?'] = content_map['effort_estimation_?']
        if 'effort_estimation_q' in content_map:
            text_map['effort_estimation_q'] = content_map['effort_estimation_q']

        # Note: CTA placeholders 'View Estimate' and 'Open Cost Estimate' are hyperlinked in Step 4.1
        # They should NOT be added to text_map here as they're already processed

        # Upload and replace image placeholders FIRST (before text replacement)
        if final_image_map:
            self.logger.debug("Generating themed images, uploading to Drive, and replacing placeholders...")
            # Generate themed images when map contains logical keys (e.g., IMAGE_image_1)
            # Only generate images for specific required placeholders
            required_image_types = ['image_1', 'image_2', 'image_3', 'logo', 'companyLogo', 'chart_1']
            
            for placeholder_name in list(final_image_map.keys()):
                logical_name = placeholder_name.replace('IMAGE_', '')
                
                # Skip if not a required image type
                if logical_name not in required_image_types:
                    self.logger.debug(f"Skipping unused image placeholder: {placeholder_name}")
                    final_image_map.pop(placeholder_name, None)
                    continue
                
                image_info = final_image_map.get(placeholder_name)
                if logical_name.lower() == 'companylogo' or logical_name.lower().startswith('companylogo_'):
                    has_manual_logo = False
                    if isinstance(image_info, dict):
                        has_manual_logo = bool(image_info.get('path'))
                    elif isinstance(image_info, str):
                        has_manual_logo = bool(image_info)
                    
                    if has_manual_logo:
                        self.logger.info(f"✅ Manual logo provided for {logical_name}; skipping automatic generation.")
                        continue
                    
                    self.logger.info(f"⏭️ Skipping automatic company logo generation for {logical_name}. Provide a custom logo via overrides to replace this placeholder.")
                    final_image_map.pop(placeholder_name, None)
                    continue
                
                # Process all placeholders including companyLogo through standard flow
                try:
                    # Find dimensions for this placeholder
                    placeholder_dimensions = None
                    for ph in placeholders:
                        if ph['placeholder'] == logical_name:
                            element = ph.get('element_properties', {})
                            size = element.get('size')
                            if size:
                                placeholder_dimensions = {
                                    'width': size.get('width', {}).get('magnitude'),
                                    'height': size.get('height', {}).get('magnitude'),
                                    'unit': size.get('width', {}).get('unit', 'PT')
                                }
                            break
                    if MANUAL_CROP_DIMS.get(logical_name):
                        placeholder_dimensions = _normalize_dims(MANUAL_CROP_DIMS.get(logical_name))

                    image_info = final_image_map.get(placeholder_name)
                    if logical_name.lower() == 'companylogo' or logical_name.lower().startswith('companylogo_'):
                        has_manual_logo = False
                        if isinstance(image_info, dict):
                            has_manual_logo = bool(image_info.get('path'))
                        elif isinstance(image_info, str):
                            has_manual_logo = bool(image_info)
                        
                        if has_manual_logo:
                            self.logger.info(f"✅ Manual logo provided for {logical_name}; skipping automatic generation.")
                            continue
                        
                        self.logger.info(f"⏭️ Skipping automatic company logo generation for {logical_name}. Provide a custom logo via overrides to replace this placeholder.")
                        final_image_map.pop(placeholder_name, None)
                        continue

                    themed_image_path, themed_crop, _ = self.content_generator.generate_image(
                        placeholder_type=logical_name,
                        context=context,
                        company_name=company_name or context,
                        project_name=project_name or f"{context} Project",
                        project_description=project_description,
                        image_requirements=None,
                        theme=theme,
                        placeholder_dimensions=placeholder_dimensions
                    )
                    if themed_image_path:
                        # Store image path with dimensions for later use
                        final_image_map[placeholder_name] = {
                            'path': themed_image_path,
                            'dimensions': placeholder_dimensions
                        }
                except Exception as e:
                    self.logger.warning(f"Image generation failed for {logical_name}, using existing path. Error: {e}")

            for placeholder_name, image_info in final_image_map.items():
                # Handle both dict format (with dimensions) and string format (path only)
                if isinstance(image_info, dict):
                    image_path = image_info.get('path')
                    image_dimensions = image_info.get('dimensions')
                else:
                    image_path = image_info
                    # Try to get dimensions from MANUAL_CROP_DIMS as fallback
                    logical_name = placeholder_name.replace('IMAGE_', '')
                    image_dimensions = None
                    if MANUAL_CROP_DIMS.get(logical_name):
                        image_dimensions = _normalize_dims(MANUAL_CROP_DIMS.get(logical_name))
                
                if image_path and os.path.exists(image_path):
                    # Remove IMAGE_ prefix for placeholder text
                    placeholder_text = placeholder_name.replace('IMAGE_', '')
                    success = self.slides_client.replace_image_placeholder(
                        target_id, 
                        f"{{{{{placeholder_text}}}}}", 
                        image_path,
                        target_dimensions=image_dimensions
                    )
                    if success:
                        self.logger.info(f"Successfully replaced image placeholder: {placeholder_text}")
                    else:
                        self.logger.warning(f"Failed to replace image placeholder: {placeholder_text}")
        
        # Also handle any image placeholders that weren't in the content_map but exist in the template
        # Skip image_1 and backgroundImage since they're already handled above
        # companyLogo follows standard placeholder replacement policy
        for ph in placeholders:
            placeholder_name = ph['placeholder']
            # Check if it's an image placeholder (scope_img placeholders are excluded)
            is_company_logo_variant = placeholder_name.lower() == 'companylogo' or placeholder_name.lower().startswith('companylogo_')
            is_image = (placeholder_name in ['image_2', 'image_3', 'logo', 'companyLogo', 'chart_1'] or 
                       is_company_logo_variant or
                       placeholder_name.startswith('d_i_image'))
            
            # Skip scope_img placeholders - they are not generated
            if placeholder_name.startswith('scope_img'):
                continue
            
            if is_image and placeholder_name not in [k.replace('IMAGE_', '') for k in final_image_map.keys()]:
                try:
                    if placeholder_name.lower() == 'companylogo' or is_company_logo_variant:
                        self.logger.info(f"⏭️ Skipping automatic company logo generation for {placeholder_name}. Provide a custom logo via overrides to replace this placeholder.")
                        continue
                    
                    # Find dimensions for this placeholder
                    placeholder_dimensions = None
                    element = ph.get('element_properties', {})
                    size = element.get('size')
                    if size:
                        placeholder_dimensions = {
                            'width': size.get('width', {}).get('magnitude'),
                            'height': size.get('height', {}).get('magnitude'),
                            'unit': size.get('width', {}).get('unit', 'PT')
                        }
                    # Prefer manual override by placeholder name
                    if MANUAL_CROP_DIMS.get(placeholder_name):
                        placeholder_dimensions = _normalize_dims(MANUAL_CROP_DIMS.get(placeholder_name))
                        self.logger.info(f"Using MANUAL_CROP_DIMS for {placeholder_name}: {placeholder_dimensions}")
                    
                    is_company_logo_variant = placeholder_name.lower() == 'companylogo' or placeholder_name.lower().startswith('companylogo_')
                    if is_company_logo_variant:
                        self.logger.info(f"⏭️ Skipping automatic company logo generation for {placeholder_name}. Provide a custom logo via overrides to replace this placeholder.")
                        continue
                    
                    image_path, image_crop, _ = self.content_generator.generate_image(
                        placeholder_type=placeholder_name,
                        context=context,
                        company_name=company_name or context,
                        project_name=project_name or f"{context} Project",
                        project_description=project_description,
                        image_requirements=None,
                        theme=theme,
                        placeholder_dimensions=placeholder_dimensions
                    )
                    
                    if image_path and os.path.exists(image_path):
                        # Replace - exact handling for companyLogo is done automatically in replace_image_placeholder
                        success = self.slides_client.replace_image_placeholder(
                            target_id, 
                            f"{{{{{placeholder_name}}}}}", 
                            image_path,
                            crop_properties=None,  # No crop needed - exact replacement handles sizing for companyLogo
                            target_dimensions=placeholder_dimensions  # Pass for reference (companyLogo uses exact method)
                        )
                        if success:
                            if placeholder_name in ['logo']:
                                dims_info = f" (dimensions: {placeholder_dimensions.get('width') if placeholder_dimensions else 'auto'}x{placeholder_dimensions.get('height') if placeholder_dimensions else 'auto'} PT)" if placeholder_dimensions else ""
                                self.logger.info(f"✅ Successfully replaced {placeholder_name} placeholder{dims_info}")
                            else:
                                self.logger.info(f"Successfully replaced image placeholder: {placeholder_name}")
                        else:
                            self.logger.warning(f"Failed to replace image placeholder: {placeholder_name}")
                except Exception as e:
                    self.logger.warning(f"Image generation failed for {placeholder_name}: {e}")
        
        # Handle color placeholders
        for ph in placeholders:
            placeholder_name = ph['placeholder']
            if placeholder_name in ['color1', 'color2', 'circle_1', 'circle_2']:
                try:
                    # Priority: 1. Theme colors (for color1/circle1 and color2/circle2), 2. AI-detected color, 3. Default colors
                    
                    # Always use theme colors for primary/secondary color placeholders
                    if theme and placeholder_name == 'color1':
                        color = theme.get('primary_color', '#2563eb')
                        self.logger.info(f"Using primary theme color {color} for {placeholder_name}")
                    elif theme and placeholder_name == 'color2':
                        color = theme.get('secondary_color', '#1e40af')
                        self.logger.info(f"Using secondary theme color {color} for {placeholder_name}")
                    elif theme and placeholder_name == 'circle_1':
                        color = theme.get('primary_color', '#2563eb')
                        self.logger.info(f"Using primary theme color {color} for {placeholder_name}")
                    elif theme and placeholder_name == 'circle_2':
                        color = theme.get('secondary_color', '#1e40af')
                        self.logger.info(f"Using secondary theme color {color} for {placeholder_name}")
                    else:
                        # No theme available, try AI-detected color
                        ai_detected_color = self.content_generator.get_placeholder_color(placeholder_name)
                        if ai_detected_color:
                            color = ai_detected_color
                            self.logger.info(f"Using AI-detected color {color} for {placeholder_name}")
                        else:
                            # Fallback to default colors
                            if placeholder_name in ['color1', 'circle_1']:
                                color = '#2563eb'  # Default primary blue
                            elif placeholder_name in ['color2', 'circle_2']:
                                color = '#1e40af'  # Default secondary blue
                            else:
                                color = '#3b82f6'  # Generic blue
                    
                    # Replace color placeholder by filling the shape
                    success = self.slides_client.replace_color_placeholder(
                        target_id,
                        f"{{{{{placeholder_name}}}}}",
                        color,
                        slide_id=ph.get('slide_id')
                    )
                    if success:
                        self.logger.info(f"Successfully filled {placeholder_name} placeholder with color {color}")
                    else:
                        self.logger.warning(f"Failed to fill {placeholder_name} placeholder")
                except Exception as e:
                    self.logger.warning(f"Color placeholder processing failed for {placeholder_name}: {e}")

        # Handle emoji placeholders - DETERMINISTIC SELECTION
        for ph in placeholders:
            placeholder_name = ph['placeholder']
            if (placeholder_name.startswith('logo') and placeholder_name not in ['logo', 'companyLogo']) or placeholder_name in ['logo_2', 'logo_3', 'logo_4', 'logo_5', 'logo_6']:
                try:
                    # Extract corresponding heading text if available (logo_1 uses Heading_1, etc.)
                    heading_text = None
                    if placeholder_name.startswith('logo_') or placeholder_name.startswith('logo'):
                        # Extract number from logo_1, logo_2, etc. or logo2, logo3, etc.
                        import re
                        match = re.search(r'logo[_\s]?(\d+)', placeholder_name, re.IGNORECASE)
                        if match:
                            heading_num = match.group(1)
                            heading_key = f'Heading_{heading_num}'
                            heading_text = content_map.get(heading_key)
                            if heading_text:
                                self.logger.debug(f"Found corresponding {heading_key}: {heading_text} for {placeholder_name}")
                    
                    # Call deterministic selection function
                    emoji_content = self.content_generator.select_emoji_deterministic(
                        project_name=project_name or f"{context} Project",
                        project_description=project_description or "",
                        placeholder_name=placeholder_name,
                        heading_text=heading_text
                    )
                    
                    if emoji_content:
                        text_map[placeholder_name] = emoji_content
                        self.logger.info(f"Selected emoji for {placeholder_name}: {emoji_content} (heading: {heading_text or 'N/A'})")
                    else:
                        self.logger.warning(f"Failed to select emoji for {placeholder_name}")
                except Exception as e:
                    self.logger.warning(f"Emoji selection failed for {placeholder_name}: {e}")
                    # Use fallback
                    from backend.core.generator import FALLBACK_EMOJIS
                    fallback = FALLBACK_EMOJIS.get(placeholder_name, '🚀')
                    text_map[placeholder_name] = fallback

        # FIRST: Create the styling map BEFORE replacing text
        # Apply theme-based styling if available (skip elements that became images)
        text_styling_map = None
        if theme:
            self.logger.debug("Preparing theme styling map...")
            text_styling_map = self._create_text_styling_map(placeholders, theme)
            # Remove styling entries for any image placeholders we replaced
            if final_image_map and text_styling_map:
                replaced_keys = {k.replace('IMAGE_', '') for k in final_image_map.keys()}
                filtered_map = {}
                for ph in placeholders:
                    ph_name = ph['placeholder']
                    if ph_name in replaced_keys:
                        continue
                    elem_id = ph['element_id']
                    if elem_id in text_styling_map:
                        filtered_map[elem_id] = text_styling_map[elem_id]
                text_styling_map = filtered_map
                # Also skip styling for backgroundImage placeholders (deleted when set as background)
                if text_styling_map:
                    cleaned_map = {}
                    for ph in placeholders:
                        ph_name = ph['placeholder']
                        if ph_name == 'backgroundImage':
                            continue
                        elem_id = ph['element_id']
                        if elem_id in text_styling_map:
                            cleaned_map[elem_id] = text_styling_map[elem_id]
                    text_styling_map = cleaned_map
        
        # Replace text placeholders
        if final_image_map:
            result = self.slides_client.replace_mixed_placeholders(target_id, text_map, final_image_map)
        else:
            result = self.slides_client.replace_placeholders(target_id, text_map)
        
        # Format bullets for conclusion_para if it contains bullet markers
        # Using dedicated function to avoid affecting other components
        if 'conclusion_para' in text_map:
            conclusion_content = text_map['conclusion_para']
            # Check if content contains bullet markers
            if '* ' in conclusion_content:
                self.logger.info("🔍 conclusion_para contains bullet markers, formatting bullets...")
                # Find the element containing conclusion_para content using dedicated function
                element_info = self.slides_client.find_conclusion_para_element(target_id, conclusion_content)
                
                if element_info:
                    # Format bullets
                    success = self.slides_client.format_bullets_for_element(
                        target_id,
                        element_info['element_id'],
                        element_info['slide_id'],
                        bullet_marker='* '
                    )
                    if success:
                        self.logger.info("✅ Successfully formatted bullets for conclusion_para")
                    else:
                        self.logger.warning("⚠️ Failed to format bullets for conclusion_para")
                else:
                    self.logger.warning("⚠️ Could not find element containing conclusion_para content")
        
        if result:
            presentation_url = self.slides_client.get_presentation_url(target_id)
            self.logger.info("Presentation generated successfully")
            self.logger.info(f"URL: {presentation_url}")

            token_usage_summary = None
            if hasattr(self, 'content_generator'):
                token_usage_summary = self.content_generator.get_token_usage_summary()
                self.logger.info(
                    f"🧮 Token usage this run → prompt: {token_usage_summary['prompt_tokens']}, "
                    f"candidates: {token_usage_summary['candidates_tokens']}, "
                    f"total: {token_usage_summary['total_tokens']}"
                )

            # Apply the styling map AFTER text has been replaced
            if theme and text_styling_map and text_styling_map:
                self.logger.info(f"Applying text styling to {len(text_styling_map)} elements...")
                self.slides_client.apply_text_styling(target_id, text_styling_map, theme)
                
                # Apply special styling for "Project" and "Overview" text elements
                self._apply_special_text_styling(target_id, theme)

            # BackgroundImage now uses the same image replacement as images (no overlay)
            
            return {
                'success': True,
                'presentation_id': target_id,
                'presentation_url': presentation_url,
                'placeholders_replaced': len(content_map),
                'content_map': content_map,
                'token_usage': token_usage_summary
            }
        else:
            self.logger.error("Failed to replace placeholders")
            return None

    def _create_text_styling_map(self, placeholders, theme):
        """Create comprehensive styling map for text elements using color manager"""
        self.logger.info(f"🎨 Creating styling map for {len(placeholders)} placeholders...")
        
        styling_map = color_manager.create_text_styling_map(placeholders, theme)
        
        # Log styling map entries for scope placeholders including quote
        scope_placeholders = ['scope_desc', 'comprehensive_design_job', 'scope_of_project', '"', 'project_goals']
        for ph in placeholders:
            ph_name = ph.get('placeholder')
            clean_name = ph_name.replace('{{', '').replace('}}', '') if ph_name else ''
            elem_id = ph.get('element_id')
            
            if clean_name in scope_placeholders:
                if elem_id in styling_map:
                    self.logger.info(f"📋 Styling for {ph_name}: {styling_map[elem_id]}")
                else:
                    self.logger.warning(f"⚠️ No styling found for {ph_name} (element_id: {elem_id})")
        
        # Ensure u0022 (double quote) matches the color of project_goals
        project_goals_color = None
        for ph in placeholders:
            name = (ph.get('placeholder') or '').replace('{{', '').replace('}}', '')
            elem_id = ph.get('element_id')
            if name == 'project_goals' and elem_id in styling_map:
                project_goals_color = styling_map[elem_id].get('color')
                break
        if project_goals_color:
            for ph in placeholders:
                name = (ph.get('placeholder') or '').replace('{{', '').replace('}}', '')
                elem_id = ph.get('element_id')
                if name == 'u0022' and elem_id in styling_map:
                    old = styling_map[elem_id].get('color')
                    styling_map[elem_id]['color'] = project_goals_color
                    self.logger.info(f"🔄 Set u0022 color from {old} to match project_goals: {project_goals_color}")
        
        # Return styling map as-is from color_manager - no overrides
        # All colors should come from config files: colors_theme_based.json, colors_custom.json, colors_auto_contrast.json
        return styling_map

    def _apply_special_text_styling(self, presentation_id, theme):
        """Apply special styling for specific text elements using color manager"""
        try:
            # Get presentation to find text elements
            presentation = self.slides_client.get_presentation(presentation_id)
            if not presentation:
                return
            
            requests = []
            
            for slide in presentation.get('slides', []):
                for element in slide.get('pageElements', []):
                    if 'shape' in element and element['shape'].get('text'):
                        text_elements = element['shape']['text'].get('textElements', [])
                        element_id = element.get('objectId')
                        
                        # Check if this element contains special text
                        full_text = ''
                        for te in text_elements:
                            if 'textRun' in te and te['textRun'].get('content'):
                                full_text += te['textRun']['content']
                            elif 'autoText' in te and te['autoText'].get('content'):
                                full_text += te['autoText']['content']
                        
                        # Get special text color configuration
                        color_config = color_manager.get_special_text_color(full_text, theme)
                        if color_config:
                            style_request = {
                                'updateTextStyle': {
                                    'objectId': element_id,
                                    'style': {
                                        'foregroundColor': {
                                            'opaqueColor': {
                                                'rgbColor': self.slides_client._hex_to_rgb(color_config['color'])
                                            }
                                        },
                                        'bold': color_config['bold']
                                    },
                                    'fields': 'foregroundColor,bold'
                                }
                            }
                            if color_config.get('italic'):
                                style_request['updateTextStyle']['style']['italic'] = True
                                style_request['updateTextStyle']['fields'] += ',italic'
                            
                            requests.append(style_request)
            
            # Apply all styling requests
            if requests:
                self.slides_client.batch_update_requests(presentation_id, requests)
                self.logger.info(f"Applied special text styling to {len(requests)} elements")
                
        except Exception as e:
            self.logger.warning(f"Failed to apply special text styling: {e}")


