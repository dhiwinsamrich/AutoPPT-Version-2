"""
AI Prompt Manager
Handles loading and formatting of AI prompts from configuration files
"""
import json
import os
from utils.logger import get_logger
from config import LOG_LEVEL, LOG_FILE


class PromptManager:
    def __init__(self):
        self.logger = get_logger(__name__, LOG_LEVEL, LOG_FILE)
        self.prompts = self._load_prompts()
    
    def _load_prompts(self):
        """Load prompts from the separated configuration files"""
        try:
            # Load image prompts
            image_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'prompts_image.json')
            with open(image_path, 'r', encoding='utf-8') as f:
                image_prompts = json.load(f)
            
            # Load text prompts
            text_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'prompts_text.json')
            with open(text_path, 'r', encoding='utf-8') as f:
                text_prompts = json.load(f)
            
            # Load theme prompts
            theme_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'prompts_theme.json')
            theme_prompts = {}
            if os.path.exists(theme_path):
                with open(theme_path, 'r', encoding='utf-8') as f:
                    theme_prompts = json.load(f)
            
            # Combine into old format for compatibility
            return {
                'image_prompts': image_prompts.get('prompts', {}),
                'text_prompts': text_prompts.get('prompts', {}),
                'theme_prompts': theme_prompts.get('prompts', {})
            }
        except Exception as e:
            self.logger.error(f"Failed to load AI prompts: {e}")
            raise e
    
    
    def get_image_prompt(self, placeholder_type, **kwargs):
        """Get formatted image prompt for a placeholder type"""
        prompt_template = self.prompts.get('image_prompts', {}).get(placeholder_type)
        if not prompt_template:
            raise ValueError(f"No image prompt found for {placeholder_type}")
        
        return self._format_prompt(prompt_template, **kwargs)
    
    def get_text_prompt(self, placeholder_type, **kwargs):
        """Get formatted text prompt for a placeholder type"""
        prompt_template = self.prompts.get('text_prompts', {}).get(placeholder_type)
        if not prompt_template:
            raise ValueError(f"No text prompt found for {placeholder_type}")
        
        return self._format_prompt(prompt_template, **kwargs)
    
    def get_theme_prompt(self, prompt_type, **kwargs):
        """Get formatted theme prompt"""
        prompt_template = self.prompts.get('theme_prompts', {}).get(prompt_type)
        if not prompt_template:
            raise ValueError(f"No theme prompt found for {prompt_type}")
        
        return self._format_prompt(prompt_template, **kwargs)
    
    def _format_prompt(self, template, **kwargs):
        """Format a prompt template with provided variables"""
        try:
            # Set default values for common variables
            defaults = {
                'company_name': kwargs.get('company_name', 'Company'),
                'project_name': kwargs.get('project_name', 'Project'),
                'context': kwargs.get('context', 'Business'),
                'proposal_type': kwargs.get('proposal_type', 'Proposal')
            }
            
            # Merge provided kwargs with defaults
            format_vars = {**defaults, **kwargs}
            
            # Format the template
            return template.format(**format_vars)
        except Exception as e:
            self.logger.warning(f"Failed to format prompt: {e}")
            return template
    
    def get_prompt_settings(self):
        """Get prompt generation settings"""
        return self.prompts.get('prompt_settings', {
            'max_retries': 3,
            'timeout_seconds': 30,
            'temperature': 0.7,
            'max_tokens': 500,
            'use_fallback_on_error': True
        })
    
    def list_available_prompts(self):
        """List all available prompt types"""
        return {
            'image_prompts': list(self.prompts.get('image_prompts', {}).keys()),
            'text_prompts': list(self.prompts.get('text_prompts', {}).keys()),
            'theme_prompts': list(self.prompts.get('theme_prompts', {}).keys())
        }


# Global instance for easy access
prompt_manager = PromptManager()
