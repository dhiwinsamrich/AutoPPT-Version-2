"""
Placeholder Matcher
Matches template placeholders with predefined mappings and generates appropriate content
"""
import json
import os
from typing import Dict, List, Any, Optional
from utils.logger import get_logger
from config import LOG_LEVEL, LOG_FILE
from core.generator import ContentGenerator


class PlaceholderMatcher:
    def __init__(self, mapping_file: str = "templates/placeholder_mapping.json"):
        self.mapping_file = mapping_file
        self.mappings = {}
        self.content_generator = None
        self.logger = get_logger(__name__, LOG_LEVEL, LOG_FILE)
        self.load_mappings()
    
    def load_mappings(self) -> bool:
        """Load placeholder mappings from JSON file"""
        try:
            if not os.path.exists(self.mapping_file):
                self.logger.warning(f"Mapping file not found: {self.mapping_file}")
                return False
            
            with open(self.mapping_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.mappings = data.get('placeholder_mappings', {})
            
            self.logger.info(f"Loaded {len(self.mappings)} placeholder mappings")
            return True
        except Exception as e:
            self.logger.error(f"Error loading mappings: {e}")
            return False
    
    def set_content_generator(self, generator: ContentGenerator):
        """Set the content generator for AI content creation"""
        self.content_generator = generator
    
    def match_placeholders(self, found_placeholders: List[Dict]) -> Dict[str, Any]:
        """Match found placeholders with predefined mappings"""
        matched = {}
        unmatched = []
        
        for placeholder in found_placeholders:
            placeholder_name = placeholder['placeholder']
            
            if placeholder_name in self.mappings:
                mapping = self.mappings[placeholder_name]
                matched[placeholder_name] = {
                    'placeholder_info': placeholder,
                    'mapping': mapping,
                    'type': mapping.get('type', 'TEXT'),
                    'description': mapping.get('description', ''),
                    'ai_prompt': mapping.get('ai_prompt', ''),
                    'content_requirements': mapping.get('content_requirements', {}),
                    'auto_fill': mapping.get('auto_fill', {})
                }
            else:
                unmatched.append(placeholder_name)
        
        return {
            'matched': matched,
            'unmatched': unmatched,
            'total_found': len(found_placeholders),
            'total_matched': len(matched)
        }
    
    def generate_content_for_placeholders(self, matched_placeholders: Dict,
                                        context: str, company_name: str = None,
                                        project_name: str = None, project_description: str = None,
                                        existing_content: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        """Generate content for matched placeholders in batch for faster processing"""
        if not self.content_generator:
            self.logger.error("Content generator not set")
            return {}
        
        self.logger.info(f"📝 Starting batch content generation for {len(matched_placeholders)} placeholders...")
        
        # First pass: collect all text placeholders that need AI generation
        text_placeholders_to_generate = {}
        generated_content: Dict[str, str] = {}
        # Track existing values (e.g., pre-filled Google Sheets data) so we can reference them in prompts
        combined_values: Dict[str, Any] = dict(existing_content or {})
        
        for placeholder_name, placeholder_data in matched_placeholders.items():
            mapping = placeholder_data['mapping']
            placeholder_type = mapping.get('type', 'TEXT')
            
            # Skip IMAGE type placeholders - they are handled by automation.py
            if placeholder_type == 'IMAGE':
                self.logger.debug(f"Skipping IMAGE placeholder {placeholder_name} - handled by automation")
                continue
            
            # Skip background image placeholder - handled by automation.py
            if placeholder_name == 'backgroundImage':
                self.logger.debug("Skipping backgroundImage placeholder - handled by automation")
                continue
            
            # Skip proposalName - it should come from UI input (proposal_type), not AI generation
            if placeholder_name == 'proposalName':
                self.logger.debug("Skipping proposalName - should be provided from UI input, not AI generated")
                continue
            
            # Skip property1, property2, property3 - they have exact hardcoded values, not AI-generated
            if placeholder_name in ['property1', 'property2', 'property3', 'property_1', 'property_2', 'property_3']:
                self.logger.debug(f"Skipping {placeholder_name} - has exact hardcoded value, not AI generated")
                continue
            
            # Skip placeholders that are already provided in existing_content (e.g., from UI or preset values)
            if placeholder_name in combined_values and combined_values[placeholder_name]:
                self.logger.debug(f"Skipping {placeholder_name} - already provided in existing_content: '{combined_values[placeholder_name]}'")
                continue
            
            # Handle text placeholders
            auto_fill = mapping.get('auto_fill', {})
            
            # Check if this placeholder should be auto-filled
            if self._should_auto_fill(placeholder_name, auto_fill, company_name, project_name):
                content = self._auto_fill_content(placeholder_name, auto_fill, company_name, project_name)
                if content:
                    generated_content[placeholder_name] = content
                    combined_values[placeholder_name] = content
                    if placeholder_name.startswith(('p_r_', 's_r_', 'pr_desc_', 'sr_desc_')):
                        self.logger.info(f"🧩 Auto-filled {placeholder_name} = {content}")
                    continue
            
            # Collect for batch AI generation
            text_placeholders_to_generate[placeholder_name] = mapping
        
        # Second pass: Generate all text content in batch
        if text_placeholders_to_generate and self.content_generator:
            self.logger.info(f"🤖 Batch generating {len(text_placeholders_to_generate)} text contents...")

            ordered_items = sorted(
                text_placeholders_to_generate.items(),
                key=lambda item: self._placeholder_priority(item[0])
            )

            for placeholder_name, mapping in ordered_items:
                # Determine profile based on company mode
                profile = 'company' if company_name else None
                
                # For resource description placeholders, make sure the matching resource name exists
                if placeholder_name.startswith('pr_desc_'):
                    idx = placeholder_name.split('_')[-1]
                    corresponding = f'p_r_{idx}'
                    if corresponding not in combined_values or not combined_values[corresponding]:
                        self.logger.debug(f"Skipping {placeholder_name} because corresponding {corresponding} not available yet")
                        continue
                if placeholder_name.startswith('sr_desc_'):
                    idx = placeholder_name.split('_')[-1]
                    corresponding = f's_r_{idx}'
                    if corresponding not in combined_values or not combined_values[corresponding]:
                        self.logger.debug(f"Skipping {placeholder_name} because corresponding {corresponding} not available yet")
                        continue

                # Pass along any known placeholder values so prompts can align descriptions with titles
                extra_variables = {
                    key: value
                    for key, value in {**combined_values, **generated_content}.items()
                    if isinstance(key, str) and isinstance(value, str) and value
                }

                # Generate content using prompt manager
                content = self.content_generator.generate_content(
                    placeholder_name,
                    context,
                    profile=profile,
                    company_name=company_name or context,
                    project_name=project_name or f"{context} Project",
                    project_description=project_description,
                    extra_variables=extra_variables
                )
                
                # Apply content optimization
                content = self._optimize_content(content, mapping.get('content_requirements', {}))
                generated_content[placeholder_name] = content
                combined_values[placeholder_name] = content
                if placeholder_name.startswith(('p_r_', 's_r_', 'pr_desc_', 'sr_desc_')):
                    self.logger.info(f"🧩 Generated {placeholder_name} = {content}")
                
                self.logger.debug(f"✓ Generated content for {placeholder_name}")
        
        self.logger.info(f"✅ Batch generation complete: {len(generated_content)} contents generated")
        return generated_content

    def _should_auto_fill(self, placeholder_name: str, auto_fill: Dict, 
                         company_name: str, project_name: str) -> bool:
        """Check if placeholder should be auto-filled instead of AI generated"""
        if not auto_fill:
            return False
        
        # Check specific auto-fill conditions
        if placeholder_name == 'companyName' and company_name:
            return True
        elif placeholder_name == 'projectName' and project_name:
            return True
        elif placeholder_name == 'proposalName' and auto_fill.get('default_value'):
            return True
        
        return False
    
    def _auto_fill_content(self, placeholder_name: str, auto_fill: Dict, 
                          company_name: str, project_name: str) -> str:
        """Auto-fill content based on mapping rules"""
        if placeholder_name == 'companyName' and company_name:
            return company_name
        elif placeholder_name == 'projectName' and project_name:
            return project_name
        elif placeholder_name == 'proposalName' and auto_fill.get('default_value'):
            return auto_fill['default_value']
        
        return ""
    
    def _optimize_content(self, content: str, requirements: Dict) -> str:
        """Optimize content based on requirements"""
        if not content:
            return content
        
        # Get word limits
        min_words = requirements.get('min_words', 0)
        max_words = requirements.get('max_words', 1000)
        
        # Preserve intentional newlines (e.g., bullet splits) while normalizing spacing
        newline_token = "__PRESERVE_NEWLINE__"
        content_with_tokens = content.replace('\n', f' {newline_token} ')
        
        # Split into words/tokens
        words = content_with_tokens.split()
        
        # Enforce word limits
        # Do NOT pad with placeholder words like 'content' to avoid repetition
        if len(words) > max_words:
            # Truncate to max words
            words = words[:max_words]
        
        # Rejoin and clean
        optimized = ' '.join(words)
        optimized = optimized.replace(newline_token, '\n')
        if '\n' in optimized:
            optimized = '\n'.join(line.strip() for line in optimized.split('\n'))
        
        # Apply style requirements
        style = requirements.get('style', '')
        if 'concise' in style:
            # Remove unnecessary words
            optimized = self._make_concise(optimized)
        elif 'professional' in style:
            # Ensure professional tone but avoid adding punctuation for short labels
            optimized = self._make_professional(optimized, avoid_period_for_short_labels=True)
        
        return optimized.strip()
    
    
    def _make_concise(self, content: str) -> str:
        """Make content more concise"""
        # Remove common filler words
        filler_words = ['very', 'really', 'quite', 'rather', 'somewhat', 'fairly']
        words = content.split()
        words = [word for word in words if word.lower() not in filler_words]
        return ' '.join(words)
    
    def _make_professional(self, content: str, avoid_period_for_short_labels: bool = False) -> str:
        """Make content more professional"""
        # Capitalize first letter
        if content:
            content = content[0].upper() + content[1:]
        
        # Ensure proper punctuation for sentences only
        # If requested, avoid adding a trailing period for short label-like content
        if avoid_period_for_short_labels:
            word_count = len(content.split())
            if word_count < 5:
                # Treat as a short label/title; do not force punctuation
                return content
        
        if not content.endswith(('.', '!', '?')):
            content += '.'
        
        return content

    def _placeholder_priority(self, name: str) -> tuple:
        """Ensure related placeholders generate in logical order (titles before descriptions)."""
        if name.startswith('p_r_'):
            try:
                idx = int(name.split('_')[-1])
            except ValueError:
                idx = 99
            return (0, idx)
        if name.startswith('s_r_'):
            try:
                idx = int(name.split('_')[-1])
            except ValueError:
                idx = 99
            return (1, idx)
        if name.startswith('pr_desc_'):
            try:
                idx = int(name.split('_')[-1])
            except ValueError:
                idx = 99
            return (2, idx)
        if name.startswith('sr_desc_'):
            try:
                idx = int(name.split('_')[-1])
            except ValueError:
                idx = 99
            return (3, idx)
        return (4, name)
    
