"""
Google Sheets Project Analyzer with Gemini AI
Analyzes project data from Google Sheets and extracts structured information
"""
import json
import re
from typing import Dict, Optional, List
import google.generativeai as genai

from utils.logger import get_logger
from config import GEMINI_API_KEY, GEMINI_MODEL, LOG_LEVEL, LOG_FILE


class ProjectAnalyzer:
    """Analyze project data from Google Sheets using Gemini AI"""
    
    def __init__(self):
        """Initialize the analyzer"""
        self.logger = get_logger(__name__, LOG_LEVEL, LOG_FILE)
        self.gemini_model = None
        self.gemini_available = False
        self._setup_gemini()
    
    def _setup_gemini(self):
        """Setup Gemini AI"""
        try:
            self.logger.info("🔧 Initializing Gemini AI for project analysis...")
            
            if not GEMINI_API_KEY:
                self.logger.error("❌ GEMINI_API_KEY not configured - project analysis will be disabled")
                self.logger.error("   Please set GEMINI_API_KEY in your .env file or environment variables")
                self.gemini_available = False
                return False
            
            # self.logger.info(f"✓ GEMINI_API_KEY found: {GEMINI_API_KEY[:10]}...")
            
            genai.configure(api_key=GEMINI_API_KEY)
            model_name = GEMINI_MODEL or 'gemini-2.5-pro'
            self.logger.info(f"🔧 Creating Gemini model: {model_name}")
            self.gemini_model = genai.GenerativeModel(model_name)
            self.gemini_available = True
            self.logger.info(f"✅ Gemini AI configured successfully (model: {model_name})")
            return True
        except Exception as e:
            self.logger.error(f"❌ Error setting up Gemini: {e}")
            self.gemini_available = False
            import traceback
            traceback.print_exc()
            return False
    
    def format_data_for_gemini(self, sheet_data: List[List]) -> str:
        """
        Format sheet data into a readable format for Gemini
        
        Args:
            sheet_data: Raw data from Google Sheets (list of rows)
            
        Returns:
            Formatted string representation of the data
        """
        formatted = "PROJECT DATA FROM GOOGLE SHEETS\n"
        formatted += "=" * 60 + "\n\n"
        formatted += "COLUMN STRUCTURE:\n"
        formatted += "- Column A (index 0): Row number/ID\n"
        formatted += "- Column D (index 3): Phase name\n"
        formatted += "- Column I (index 8): Task Owner/Resource name\n"
        formatted += "- Columns J onwards (index 9+): Daily hour allocations\n"
        formatted += "\n" + "=" * 60 + "\n\n"
        
        # Include all rows for comprehensive analysis
        for idx, row in enumerate(sheet_data, 1):
            # Convert row to string, handling None values
            row_str = [str(cell) if cell is not None else '' for cell in row]
            
            # Add helpful annotations for key rows
            if idx == 9:
                formatted += f"Row {idx} (WEEK HEADERS): {row_str}\n"
            elif idx == 10:
                formatted += f"Row {idx} (DAY HEADERS): {row_str}\n"
            elif idx >= 11:
                # For data rows, highlight key columns
                phase = row[3] if len(row) > 3 and row[3] else ''
                task_owner = row[8] if len(row) > 8 and row[8] else ''
                hours_start = row[9:] if len(row) > 9 else []
                # Sum hours for this row (safely handle non-numeric values)
                try:
                    row_hours = sum([
                        float(val) if val is not None and (isinstance(val, (int, float)) or (isinstance(val, str) and val.replace('.', '').replace('-', '').isdigit())) else 0
                        for val in hours_start
                    ])
                    formatted += f"Row {idx}: Phase='{phase}', Owner='{task_owner}', RowHours={row_hours:.1f}, Data={row_str}\n"
                except (ValueError, TypeError):
                    formatted += f"Row {idx}: Phase='{phase}', Owner='{task_owner}', Data={row_str}\n"
            else:
                formatted += f"Row {idx}: {row_str}\n"
        
        formatted += f"\n(Total {len(sheet_data)} rows)\n"
        formatted += "\nNOTE: Row 9 contains week headers (W1, W2, W3, etc.) - count unique weeks for duration calculation.\n"
        formatted += "NOTE: Data rows start from row 11 - sum hours from column J (index 9) onwards for each row.\n"
        
        return formatted
    
    def analyze_with_gemini(self, sheet_data: List[List]) -> Optional[Dict[str, any]]:
        """
        Send data to Gemini for analysis and extract structured results
        
        Args:
            sheet_data: Extracted data from Google Sheets
            
        Returns:
            Dictionary with extracted data:
            {
                'top_resources': ['Resource1', 'Resource2', ...],  # Top 6
                'days': '45',  # Total project days
                'p_b': '15%',  # Planning phase budget
                'd_b': '25%',  # Design phase budget
                'd_v': '40%',  # Development phase budget
                'd_p': '20%'   # Deployment phase budget
            }
        """
        if not self.gemini_model:
            self.logger.warning("Gemini model not available - skipping analysis")
            return None
        
        try:
            prompt = f"""
You are a project data analyst. Analyze the following Google Sheets data and extract EXACT information in JSON format.

DATA STRUCTURE:
- Data typically starts from row 11 (skip header rows)
- Column D (index 3): Phase name (e.g., "Planning", "Design I", "Design II", "Development & Integration", "Graphics & Content", "Testing", "Launch")
- Column I (index 8): Task Owner/Resource name (e.g., "Project Manager", "Frontend Developer", "Backend Developer", etc.)
- Columns J onwards (index 9+): Daily hour allocations (W1D1, W1D2, W1D3, etc. representing weeks and days)
- Row 9: Week headers (W1, W2, W3, W4, etc.) - use this to count total weeks
- Each week has 5 working days (D1-D5)

CALCULATION PROCEDURES:

1. **TOP 6 TASK OWNERS/RESOURCES**:
   - For each row with a Task Owner (Column I), sum ALL hour values from Column J onwards
   - Group all rows by Task Owner and sum their total hours
   - Sort by total hours in descending order
   - Select the top 6 task owners
   - Return ONLY the names (no hours, no percentages)

2. **BUDGET SPLIT BY 4 PHASES**:
   - For each row, identify the Phase (Column D) and sum hours from Column J onwards
   - Group by Phase and sum total hours per phase
   - Map the 7 original phases to 4 main phases:
     * "Planning" → Planning (p_b)
     * "Design I" + "Design II" → Design (d_b)
     * "Development & Integration" + "Graphics & Content" → Development (d_v)
     * "Testing" + "Launch" → Deployment (d_p)
   - Calculate percentage for each main phase: (Phase Hours / Total Project Hours) × 100
   - Round to 2 decimal places and include % symbol (e.g., "10.14%")

3. **PROJECT DURATION**:
   - Find Row 9 (week headers row)
   - Count unique week identifiers (W1, W2, W3, W4, etc.)
   - Each week = 5 working days
   - Total Days = Number of Weeks × 5
   - Return as a number string (e.g., "20" for 20 days)

Here is the data:

{self.format_data_for_gemini(sheet_data)}

IMPORTANT: Return ONLY a valid JSON object with this exact structure:
{{
    "top_resources": ["Resource Name 1", "Resource Name 2", "Resource Name 3", "Resource Name 4", "Resource Name 5", "Resource Name 6"],
    "days": "20",
    "p_b": "10.14%",
    "d_b": "40.25%",
    "d_v": "43.37%",
    "d_p": "6.24%"
}}

CRITICAL RULES:
- Extract actual resource names ONLY (no hours, no percentages, no extra text)
- Calculate percentages accurately: (Phase Hours / Total Hours) × 100
- Verify percentages sum to approximately 100%
- For days: Count unique weeks from row 9, multiply by 5
- Return exactly 6 resources (pad with empty strings if fewer than 6 found)
- All percentages must include the % symbol
- Days must be a number string without "Days" suffix
"""
            
            self.logger.info("📊 Sending project data to Gemini AI for analysis...")
            
            response = self.gemini_model.generate_content(prompt)
            response_text = response.text.strip()
            
            self.logger.info("✓ Analysis completed by Gemini AI")
            self.logger.debug(f"Gemini response: {response_text[:500]}...")  # Log first 500 chars
            
            # Parse JSON from response (might be wrapped in markdown code blocks)
            json_text = self._extract_json_from_response(response_text)
            
            if json_text:
                try:
                    data = json.loads(json_text)
                    self.logger.info("✅ Successfully parsed Gemini analysis results")
                    return data
                except json.JSONDecodeError as e:
                    self.logger.error(f"❌ Failed to parse JSON from Gemini response: {e}")
                    self.logger.error(f"Response text: {response_text}")
                    return None
            else:
                self.logger.error("❌ Could not extract JSON from Gemini response")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Error analyzing with Gemini: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _extract_json_from_response(self, response_text: str) -> Optional[str]:
        """
        Extract JSON from Gemini response (might be wrapped in markdown code blocks)
        
        Args:
            response_text: Raw response from Gemini
            
        Returns:
            Extracted JSON string or None
        """
        # Try to find JSON in code blocks
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
        if json_match:
            return json_match.group(1)
        
        # Try to find JSON object directly
        json_match = re.search(r'\{.*"top_resources".*"d_p".*?\}', response_text, re.DOTALL)
        if json_match:
            return json_match.group(0)
        
        # Try to find any JSON object
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response_text, re.DOTALL)
        if json_match:
            return json_match.group(0)
        
        return None
    
    def analyze_project_data(self, sheet_data: List[List]) -> Dict[str, str]:
        """
        Analyze project data and return formatted placeholder values
        
        Args:
            sheet_data: Raw data from Google Sheets
            
        Returns:
            Dictionary mapping placeholders to values:
            {
                'p_r_1': 'Resource Name 1',
                'p_r_2': 'Resource Name 2',
                'p_r_3': 'Resource Name 3',
                's_r_1': 'Resource Name 4',
                's_r_2': 'Resource Name 5',
                's_r_3': 'Resource Name 6',
                'days': '45',
                'p_b': '15%',
                'd_b': '25%',
                'd_v': '40%',
                'd_p': '20%'
            }
        """
        if not self.gemini_model or not self.gemini_available:
            self.logger.error("❌ Gemini model not initialized - cannot analyze project data")
            self.logger.error(f"   gemini_model: {self.gemini_model is not None}")
            self.logger.error(f"   gemini_available: {self.gemini_available}")
            self.logger.error("   Please check GEMINI_API_KEY configuration")
            return {}
        
        if not sheet_data:
            self.logger.warning("⚠️ No sheet data provided for analysis")
            return {}
        
        self.logger.info(f"🔍 Analyzing {len(sheet_data)} rows of project data with Gemini AI...")
        self.logger.info(f"📊 Sheet data preview: {len(sheet_data)} rows, {len(sheet_data[0]) if sheet_data else 0} columns")
        
        analysis_result = self.analyze_with_gemini(sheet_data)
        
        if not analysis_result:
            self.logger.error("❌ Gemini analysis failed - returning empty results")
            self.logger.error("   Check Gemini API key and network connection")
            return {}
        
        # Map analysis results to placeholders
        placeholder_map = {}
        
        # Map top 6 resources to p_r_1-3 and s_r_1-3
        top_resources = analysis_result.get('top_resources', [])
        
        # p_r_1 to p_r_3 (first 3 resources)
        for i in range(1, 4):
            if i <= len(top_resources):
                placeholder_map[f'p_r_{i}'] = str(top_resources[i-1]).strip()
                self.logger.info(f"📊 Mapped p_r_{i} = {top_resources[i-1]}")
            else:
                placeholder_map[f'p_r_{i}'] = ''
                self.logger.warning(f"⚠️ Only {len(top_resources)} resources found, p_r_{i} will be empty")
        
        # s_r_1 to s_r_3 (next 3 resources, indices 3-5)
        for i in range(1, 4):
            resource_idx = i + 2  # s_r_1 = resource[3], s_r_2 = resource[4], s_r_3 = resource[5]
            if resource_idx <= len(top_resources):
                placeholder_map[f's_r_{i}'] = str(top_resources[resource_idx]).strip()
                self.logger.info(f"📊 Mapped s_r_{i} = {top_resources[resource_idx]}")
            else:
                placeholder_map[f's_r_{i}'] = ''
                self.logger.warning(f"⚠️ Only {len(top_resources)} resources found, s_r_{i} will be empty")
        
        # Map budget percentages
        days_value = str(analysis_result.get('days', '')).strip()
        # Append " Days" if not already present and value is not empty
        if days_value and 'day' not in days_value.lower():
            placeholder_map['days'] = f"{days_value} Days"
        else:
            placeholder_map['days'] = days_value
        placeholder_map['p_b'] = str(analysis_result.get('p_b', '')).strip()
        placeholder_map['d_b'] = str(analysis_result.get('d_b', '')).strip()
        placeholder_map['d_v'] = str(analysis_result.get('d_v', '')).strip()
        placeholder_map['d_p'] = str(analysis_result.get('d_p', '')).strip()
        
        self.logger.info(f"✅ Mapped analysis results: days={placeholder_map.get('days')}, p_b={placeholder_map.get('p_b')}, d_b={placeholder_map.get('d_b')}, d_v={placeholder_map.get('d_v')}, d_p={placeholder_map.get('d_p')}")
        
        return placeholder_map

