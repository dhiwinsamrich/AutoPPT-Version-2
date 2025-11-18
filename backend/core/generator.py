"""
AI Content Generator for PPT Automation
Handles content generation using Google Gemini API
"""
import google.generativeai as genai
import json
import re
import os
import sys
from typing import Optional
from PIL import Image, ImageFilter, ImageEnhance, ImageOps
from io import BytesIO
import colorsys
import numpy as np
from collections import Counter
from config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_IMAGE_MODEL, LOG_LEVEL, LOG_FILE, IMAGE_CROP_SETTINGS
from utils.logger import get_logger
from utils.prompt_manager import prompt_manager

# ============================================================================
# DETERMINISTIC EMOJI SELECTION SYSTEM
# ============================================================================

# Master emoji database with associated keywords and weights
EMOJI_DATABASE = {
    # Technology & Innovation
    '🚀': {
        'keywords': ['rocket', 'launch', 'startup', 'technology', 'innovation', 'fast', 
                     'growth', 'space', 'future', 'tech', 'digital', 'advance', 'boost'],
        'weight': 1.0,
        'categories': ['main_theme', 'future']
    },
    '💻': {
        'keywords': ['computer', 'software', 'coding', 'programming', 'development', 
                     'dev', 'tech', 'digital', 'app', 'web', 'platform'],
        'weight': 1.0,
        'categories': ['main_theme']
    },
    '📱': {
        'keywords': ['mobile', 'phone', 'app', 'smartphone', 'ios', 'android', 
                     'application', 'device'],
        'weight': 1.0,
        'categories': ['main_theme']
    },
    '🌐': {
        'keywords': ['internet', 'web', 'global', 'worldwide', 'network', 'online', 
                     'digital', 'cloud', 'connectivity'],
        'weight': 1.0,
        'categories': ['main_theme']
    },
    '🤖': {
        'keywords': ['ai', 'artificial', 'intelligence', 'robot', 'automation', 'machine', 
                     'learning', 'bot', 'neural', 'algorithm'],
        'weight': 1.0,
        'categories': ['main_theme', 'innovation']
    },
    
    # Data & Analytics
    '📊': {
        'keywords': ['data', 'chart', 'graph', 'analytics', 'statistics', 'metrics', 
                     'dashboard', 'visualization', 'reporting', 'insights', 'bi'],
        'weight': 1.0,
        'categories': ['data_analytics']
    },
    '📈': {
        'keywords': ['growth', 'increase', 'trending', 'upward', 'improvement', 'rising', 
                     'progress', 'advancement', 'gains', 'performance'],
        'weight': 1.0,
        'categories': ['data_analytics', 'success']
    },
    '📉': {
        'keywords': ['decrease', 'decline', 'reduction', 'downward', 'analysis', 'trend'],
        'weight': 0.8,
        'categories': ['data_analytics']
    },
    '🎯': {
        'keywords': ['target', 'goal', 'objective', 'aim', 'focus', 'precision', 
                     'accuracy', 'bullseye', 'kpi', 'milestone'],
        'weight': 1.0,
        'categories': ['strategy', 'data_analytics']
    },
    
    # Strategy & Planning
    '📋': {
        'keywords': ['plan', 'planning', 'checklist', 'task', 'list', 'organize', 
                     'agenda', 'schedule', 'roadmap', 'blueprint'],
        'weight': 1.0,
        'categories': ['strategy']
    },
    '🗺️': {
        'keywords': ['roadmap', 'journey', 'path', 'navigation', 'direction', 'route', 'map'],
        'weight': 1.0,
        'categories': ['strategy']
    },
    '⚙️': {
        'keywords': ['process', 'system', 'mechanism', 'operation', 'workflow', 
                     'automation', 'efficiency', 'optimization', 'engine'],
        'weight': 1.0,
        'categories': ['strategy', 'energy_power']
    },
    '🔧': {
        'keywords': ['tool', 'implement', 'implementation', 'build', 'fix', 'maintenance', 
                     'setup', 'configuration', 'repair'],
        'weight': 1.0,
        'categories': ['strategy']
    },
    
    # Innovation & Ideas
    '💡': {
        'keywords': ['idea', 'innovation', 'lightbulb', 'creative', 'creativity', 'bright', 
                     'insight', 'solution', 'concept', 'inspiration', 'thinking'],
        'weight': 1.0,
        'categories': ['innovation']
    },
    '✨': {
        'keywords': ['sparkle', 'magic', 'special', 'excellence', 'quality', 'premium', 
                     'shine', 'brilliant', 'outstanding'],
        'weight': 1.0,
        'categories': ['innovation', 'success']
    },
    '🔬': {
        'keywords': ['research', 'science', 'lab', 'experiment', 'study', 'analysis', 
                     'investigation', 'testing', 'scientific'],
        'weight': 1.0,
        'categories': ['innovation']
    },
    '🎨': {
        'keywords': ['design', 'art', 'creative', 'visual', 'aesthetic', 'ui', 'ux', 
                     'graphics', 'branding'],
        'weight': 1.0,
        'categories': ['innovation']
    },
    
    # Energy & Performance
    '⚡': {
        'keywords': ['energy', 'power', 'electric', 'fast', 'speed', 'lightning', 
                     'quick', 'instant', 'rapid', 'performance', 'boost'],
        'weight': 1.0,
        'categories': ['energy_power']
    },
    '🔥': {
        'keywords': ['fire', 'hot', 'trending', 'popular', 'burning', 'passion', 
                     'intense', 'powerful', 'viral'],
        'weight': 1.0,
        'categories': ['energy_power', 'success']
    },
    '💪': {
        'keywords': ['strong', 'strength', 'power', 'muscle', 'robust', 'capable', 
                     'empowerment', 'fitness'],
        'weight': 1.0,
        'categories': ['energy_power']
    },
    '🔋': {
        'keywords': ['battery', 'energy', 'charge', 'power', 'fuel', 'sustainable', 
                     'renewable'],
        'weight': 1.0,
        'categories': ['energy_power']
    },
    
    # Success & Achievement
    '🏆': {
        'keywords': ['trophy', 'winner', 'success', 'achievement', 'victory', 'award', 
                     'champion', 'excellence', 'best', 'top', 'first'],
        'weight': 1.0,
        'categories': ['success']
    },
    '🌟': {
        'keywords': ['star', 'excellence', 'outstanding', 'superior', 'premier', 
                     'quality', 'exceptional', 'elite'],
        'weight': 1.0,
        'categories': ['success']
    },
    '🎖️': {
        'keywords': ['medal', 'achievement', 'accomplishment', 'recognition', 'honor'],
        'weight': 1.0,
        'categories': ['success']
    },
    '📜': {
        'keywords': ['certificate', 'diploma', 'credential', 'certification', 'qualification'],
        'weight': 0.9,
        'categories': ['success']
    },
    
    # Growth & Development
    '🌱': {
        'keywords': ['growth', 'growing', 'develop', 'seedling', 'startup', 'begin', 
                     'plant', 'organic', 'natural', 'green', 'sustainable'],
        'weight': 1.0,
        'categories': ['main_theme', 'success']
    },
    '🌳': {
        'keywords': ['tree', 'mature', 'established', 'rooted', 'stable', 'long-term'],
        'weight': 0.9,
        'categories': ['main_theme']
    },
    '📚': {
        'keywords': ['education', 'learning', 'knowledge', 'study', 'book', 'training', 
                     'course', 'teaching', 'academic'],
        'weight': 1.0,
        'categories': ['main_theme']
    },
    
    # Business & Finance
    '🏢': {
        'keywords': ['business', 'corporate', 'company', 'office', 'enterprise', 
                     'organization', 'building', 'headquarters'],
        'weight': 1.0,
        'categories': ['main_theme']
    },
    '💰': {
        'keywords': ['money', 'finance', 'financial', 'revenue', 'profit', 'income', 
                     'earnings', 'cash', 'wealth'],
        'weight': 1.0,
        'categories': ['main_theme']
    },
    '💵': {
        'keywords': ['dollar', 'currency', 'payment', 'transaction', 'monetary'],
        'weight': 0.9,
        'categories': ['main_theme']
    },
    '💸': {
        'keywords': ['investment', 'investing', 'funding', 'capital', 'venture'],
        'weight': 1.0,
        'categories': ['main_theme']
    },
    
    # Healthcare & Wellness
    '🏥': {
        'keywords': ['hospital', 'healthcare', 'medical', 'health', 'clinic', 
                     'patient', 'treatment'],
        'weight': 1.0,
        'categories': ['main_theme']
    },
    '⚕️': {
        'keywords': ['medicine', 'doctor', 'physician', 'care', 'healing'],
        'weight': 1.0,
        'categories': ['main_theme']
    },
    '💊': {
        'keywords': ['pill', 'medication', 'drug', 'pharmacy', 'pharmaceutical'],
        'weight': 1.0,
        'categories': ['main_theme']
    },
    '❤️': {
        'keywords': ['heart', 'cardiac', 'wellness', 'wellbeing', 'care', 'love'],
        'weight': 1.0,
        'categories': ['main_theme']
    },
    
    # Environment & Sustainability
    '🌍': {
        'keywords': ['world', 'global', 'earth', 'planet', 'environment', 'international'],
        'weight': 1.0,
        'categories': ['main_theme']
    },
    '♻️': {
        'keywords': ['recycle', 'sustainability', 'sustainable', 'eco', 'green', 
                     'environmental', 'circular', 'reuse'],
        'weight': 1.0,
        'categories': ['main_theme']
    },
    '🌿': {
        'keywords': ['nature', 'natural', 'organic', 'plant', 'leaf', 'green'],
        'weight': 1.0,
        'categories': ['main_theme']
    },
    '☀️': {
        'keywords': ['solar', 'sun', 'sunshine', 'bright', 'renewable', 'clean energy'],
        'weight': 1.0,
        'categories': ['main_theme', 'energy_power']
    },
    
    # Communication & Collaboration
    '💬': {
        'keywords': ['communication', 'chat', 'message', 'conversation', 'dialogue', 
                     'discussion', 'talk'],
        'weight': 1.0,
        'categories': ['main_theme']
    },
    '🤝': {
        'keywords': ['partnership', 'collaboration', 'cooperation', 'agreement', 
                     'handshake', 'team', 'together', 'alliance'],
        'weight': 1.0,
        'categories': ['main_theme']
    },
    '👥': {
        'keywords': ['team', 'people', 'group', 'community', 'users', 'members', 
                     'employees', 'staff'],
        'weight': 1.0,
        'categories': ['main_theme']
    },
    '📢': {
        'keywords': ['announcement', 'marketing', 'advertising', 'promotion', 
                     'broadcast', 'campaign'],
        'weight': 1.0,
        'categories': ['main_theme']
    },
    
    # Security & Protection
    '🔒': {
        'keywords': ['security', 'secure', 'lock', 'privacy', 'protected', 'safe', 
                     'encryption', 'safety'],
        'weight': 1.0,
        'categories': ['main_theme']
    },
    '🛡️': {
        'keywords': ['shield', 'protection', 'defense', 'safeguard', 'guard'],
        'weight': 1.0,
        'categories': ['main_theme']
    },
    '🔐': {
        'keywords': ['key', 'access', 'authentication', 'authorization', 'password'],
        'weight': 1.0,
        'categories': ['main_theme']
    },
    
    # Time & Productivity
    '⏰': {
        'keywords': ['time', 'clock', 'alarm', 'schedule', 'timing', 'punctual'],
        'weight': 1.0,
        'categories': ['strategy']
    },
    '📅': {
        'keywords': ['calendar', 'date', 'schedule', 'appointment', 'event', 'meeting'],
        'weight': 1.0,
        'categories': ['strategy']
    },
    '⏳': {
        'keywords': ['hourglass', 'deadline', 'countdown', 'waiting', 'duration'],
        'weight': 0.9,
        'categories': ['strategy']
    },
}

# Category-to-emoji priority mapping
LOGO_CATEGORY_MAPPING = {
    'logo_1': ['main_theme'],           # Primary theme
    'logo_2': ['data_analytics'],        # Data/Analytics focus
    'logo_3': ['strategy'],              # Strategy/Planning focus
    'logo_4': ['innovation'],            # Innovation/Ideas focus
    'logo_5': ['energy_power'],          # Energy/Performance focus
    'logo_6': ['success'],               # Success/Achievement focus
}

# Fallback emojis per category (guaranteed defaults)
FALLBACK_EMOJIS = {
    'logo_1': '🚀',
    'logo_2': '📊',
    'logo_3': '🎯',
    'logo_4': '💡',
    'logo_5': '⚡',
    'logo_6': '🌟',
    # Also support alternate naming
    'logo2': '📊',
    'logo3': '🎯',
    'logo4': '💡',
    'logo5': '⚡',
    'logo6': '🌟',
}


class ContentGenerator:
    def __init__(self):
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        genai.configure(api_key=GEMINI_API_KEY)
        self.model_name = GEMINI_MODEL
        self.image_model_name = GEMINI_IMAGE_MODEL
        self.gemini_model = genai.GenerativeModel(self.model_name)
        self.logger = get_logger(__name__, LOG_LEVEL, LOG_FILE)
        self.placeholder_colors = {}  # Store AI-detected colors for placeholders
        self.emoji_selection_log = []  # Track emoji selections for metrics
        self.emoji_cache = {}  # Cache emoji selections for performance
        self.reset_token_usage()

    # ============================================================================
    # TOKEN USAGE TRACKING
    # ============================================================================

    def reset_token_usage(self):
        """Reset per-run token usage statistics."""
        self._token_usage_summary = {
            'prompt_tokens': 0,
            'candidates_tokens': 0,
            'total_tokens': 0
        }
        self._token_usage_details = []

    def _record_token_usage(self, response, label=None):
        """Record token usage from a Gemini response, if available."""
        if not response:
            return

        if not hasattr(self, '_token_usage_summary'):
            self.reset_token_usage()

        usage = getattr(response, 'usage_metadata', None)
        if not usage:
            to_dict = getattr(response, 'to_dict', None)
            if callable(to_dict):
                try:
                    data = to_dict()
                    usage = data.get('usageMetadata') or data.get('usage_metadata')
                except Exception:
                    usage = None
        if not usage:
            return

        def _get_usage_value(source, key):
            if source is None:
                return 0
            if hasattr(source, key):
                value = getattr(source, key)
                if value is not None:
                    return value
            if isinstance(source, dict):
                value = source.get(key)
                if value is not None:
                    return value
            # Try mapping-style access
            getter = getattr(source, 'get', None)
            if callable(getter):
                value = getter(key)
                if value is not None:
                    return value
            return 0

        prompt_tokens = _get_usage_value(usage, 'prompt_token_count')
        candidates_tokens = _get_usage_value(usage, 'candidates_token_count')
        total_tokens = _get_usage_value(usage, 'total_token_count')

        # Fallback key names used in some responses
        if total_tokens == 0:
            total_tokens = _get_usage_value(usage, 'total_tokens')
        if prompt_tokens == 0:
            prompt_tokens = _get_usage_value(usage, 'prompt_tokens')
        if candidates_tokens == 0:
            candidates_tokens = _get_usage_value(usage, 'candidates_tokens')

        if not any([prompt_tokens, candidates_tokens, total_tokens]):
            return

        self._token_usage_summary['prompt_tokens'] += prompt_tokens
        self._token_usage_summary['candidates_tokens'] += candidates_tokens
        self._token_usage_summary['total_tokens'] += total_tokens

        self._token_usage_details.append({
            'label': label or 'unspecified',
            'prompt_tokens': prompt_tokens,
            'candidates_tokens': candidates_tokens,
            'total_tokens': total_tokens
        })

    def get_token_usage_summary(self):
        """Return the aggregated token usage for the current run."""
        return {
            'prompt_tokens': self._token_usage_summary['prompt_tokens'],
            'candidates_tokens': self._token_usage_summary['candidates_tokens'],
            'total_tokens': self._token_usage_summary['total_tokens'],
            'details': list(self._token_usage_details)
        }
    
    # ============================================================================
    # DETERMINISTIC EMOJI SELECTION METHODS
    # ============================================================================
    
    def preprocess_text(self, text):
        """
        Normalize and clean text for keyword matching
        
        Args:
            text: Raw project context string
            
        Returns:
            list: Cleaned, lowercase words
        """
        if not text:
            return []
        
        # 1. Convert to lowercase
        text = str(text).lower()
        
        # 2. Remove special characters but keep spaces and hyphens
        text = re.sub(r'[^a-z0-9\s-]', ' ', text)
        
        # 3. Replace hyphens with spaces for compound words
        text = text.replace('-', ' ')
        
        # 4. Split into words
        words = text.split()
        
        # 5. Remove common stop words (optional but recommended)
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 
                      'to', 'for', 'of', 'with', 'by', 'from', 'is', 'are', 
                      'was', 'were', 'been', 'be', 'have', 'has', 'had', 'this', 
                      'that', 'these', 'those'}
        words = [w for w in words if w not in stop_words and len(w) > 2]
        
        # 6. Return cleaned word list
        return words
    
    def calculate_emoji_score(self, context_words, emoji_data):
        """
        Calculate relevance score for an emoji based on keyword matches
        
        Args:
            context_words: list of preprocessed words from project context
            emoji_data: dict containing 'keywords', 'weight', 'categories'
            
        Returns:
            float: Relevance score (0.0 to 10.0+)
        """
        score = 0.0
        
        # 1. Exact keyword matches (highest score)
        for keyword in emoji_data['keywords']:
            if keyword in context_words:
                score += 2.0 * emoji_data['weight']
        
        # 2. Partial keyword matches (medium score)
        for keyword in emoji_data['keywords']:
            for word in context_words:
                if len(keyword) > 3 and len(word) > 3:  # Avoid false matches on short words
                    if keyword in word or word in keyword:
                        score += 1.0 * emoji_data['weight']
        
        # 3. Bonus for multiple matches (indicates strong relevance)
        match_count = sum(1 for kw in emoji_data['keywords'] if kw in context_words)
        if match_count > 2:
            score += match_count * 0.5
        
        # 4. Return final score
        return score
    
    def filter_emojis_by_category(self, placeholder_name):
        """
        Get emojis that match the category for a specific logo placeholder
        
        Args:
            placeholder_name: e.g., 'logo_1', 'logo_2', etc.
            
        Returns:
            dict: Filtered emoji database containing only relevant categories
        """
        # 1. Get allowed categories for this placeholder
        allowed_categories = LOGO_CATEGORY_MAPPING.get(
            placeholder_name, 
            ['main_theme']  # Default if placeholder not recognized
        )
        
        # Also handle alternate naming (logo2, logo3, etc.)
        if placeholder_name.startswith('logo') and not placeholder_name.startswith('logo_'):
            # Extract number from logo2, logo3, etc.
            match = re.search(r'logo(\d+)', placeholder_name)
            if match:
                num = match.group(1)
                placeholder_key = f'logo_{num}'
                allowed_categories = LOGO_CATEGORY_MAPPING.get(placeholder_key, ['main_theme'])
        
        # 2. Filter EMOJI_DATABASE to only include emojis with matching categories
        filtered_emojis = {}
        
        for emoji, data in EMOJI_DATABASE.items():
            # Check if ANY of the emoji's categories match allowed categories
            emoji_categories = data.get('categories', [])
            if any(cat in allowed_categories for cat in emoji_categories):
                filtered_emojis[emoji] = data
        
        # 3. Return filtered dictionary
        return filtered_emojis
    
    def validate_emoji_input(self, project_name, project_description):
        """
        Validate and clean input before processing
        
        Returns:
            tuple: (cleaned_name, cleaned_description, is_valid)
        """
        # Handle None or empty inputs
        if not project_name:
            project_name = "General Project"
        
        if not project_description:
            project_description = "No description provided"
        
        # Ensure strings
        project_name = str(project_name)
        project_description = str(project_description)
        
        # Check minimum length for meaningful analysis
        combined_length = len(project_name) + len(project_description)
        is_valid = combined_length >= 10  # At least 10 characters total
        
        return project_name, project_description, is_valid
    
    def select_emoji_deterministic(self, project_name, project_description, placeholder_name, heading_text=None):
        """
        Deterministically select the best emoji based on project context
        
        Args:
            project_name: str, name of the project
            project_description: str, description of the project
            placeholder_name: str, e.g., 'logo_1', 'logo_2', etc.
            heading_text: str, optional text from corresponding Heading (logo_1 uses Heading_1, etc.)
            
        Returns:
            str: Single emoji character
        """
        # Create cache key
        cache_key = f"{project_name}_{project_description}_{placeholder_name}_{heading_text or ''}"
        
        # Check cache first
        if cache_key in self.emoji_cache:
            self.logger.debug(f"Using cached emoji for {placeholder_name}")
            return self.emoji_cache[cache_key]
        
        # Validate input
        project_name, project_description, is_valid = self.validate_emoji_input(
            project_name, 
            project_description
        )
        
        if not is_valid:
            self.logger.warning(f"Insufficient context for {placeholder_name}, using fallback")
            fallback = FALLBACK_EMOJIS.get(placeholder_name, '🚀')
            self.emoji_cache[cache_key] = fallback
            return fallback
        
        # === STEP 1: Prepare Context ===
        # Combine project name, description, and heading text (if provided)
        # Priority: heading_text > project_description > project_name
        if heading_text:
            # Use heading text as primary context (logo_1 matches Heading_1 theme)
            context = f"{heading_text} {project_description} {project_name}"
            self.logger.debug(f"Using heading text for {placeholder_name}: {heading_text}")
        else:
            context = f"{project_name} {project_description}"
        
        # Preprocess text into clean word list
        context_words = self.preprocess_text(context)
        
        # Log for debugging
        self.logger.debug(f"Selecting emoji for {placeholder_name}")
        self.logger.debug(f"Context words: {context_words[:10]}...")  # First 10 words
        
        # === STEP 2: Filter Emojis by Category ===
        # Get only emojis relevant to this placeholder's category
        candidate_emojis = self.filter_emojis_by_category(placeholder_name)
        
        # If no candidates (shouldn't happen), use all emojis
        if not candidate_emojis:
            candidate_emojis = EMOJI_DATABASE
        
        # === STEP 3: Score All Candidate Emojis ===
        emoji_scores = {}
        
        for emoji, emoji_data in candidate_emojis.items():
            score = self.calculate_emoji_score(context_words, emoji_data)
            emoji_scores[emoji] = score
        
        # === STEP 4: Select Best Emoji ===
        # Sort by score (highest first)
        sorted_emojis = sorted(emoji_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Log top 3 candidates
        self.logger.debug(f"Top 3 candidates for {placeholder_name}:")
        for emoji, score in sorted_emojis[:3]:
            self.logger.debug(f"  {emoji}: {score:.2f}")
        
        # Get the best emoji
        if sorted_emojis and sorted_emojis[0][1] > 0:
            best_emoji = sorted_emojis[0][0]
            best_score = sorted_emojis[0][1]
            self.logger.info(f"{placeholder_name}: Selected {best_emoji} (score: {best_score:.2f})")
            
            # Log the decision
            from datetime import datetime
            self.emoji_selection_log.append({
                'placeholder': placeholder_name,
                'emoji': best_emoji,
                'score': best_score,
                'context_preview': ' '.join(context_words[:5]),
                'heading_text': heading_text,
                'timestamp': datetime.now().isoformat()
            })
            
            # Cache the result
            self.emoji_cache[cache_key] = best_emoji
            return best_emoji
        
        # === STEP 5: Fallback ===
        # If no emoji scored above 0, use category fallback
        fallback = FALLBACK_EMOJIS.get(placeholder_name, '🚀')
        self.logger.warning(f"{placeholder_name}: No matches found, using fallback {fallback}")
        
        # Cache fallback too
        self.emoji_cache[cache_key] = fallback
        return fallback
    
    def get_emoji_selection_summary(self):
        """
        Get summary of emoji selections for this session
        
        Returns:
            dict: Summary statistics
        """
        if not self.emoji_selection_log:
            return {"message": "No emoji selections recorded"}
        
        # Calculate statistics
        total_selections = len(self.emoji_selection_log)
        avg_score = sum(log['score'] for log in self.emoji_selection_log) / total_selections
        unique_emojis = len(set(log['emoji'] for log in self.emoji_selection_log))
        
        # Most used emoji
        emoji_counts = {}
        for log in self.emoji_selection_log:
            emoji = log['emoji']
            emoji_counts[emoji] = emoji_counts.get(emoji, 0) + 1
        most_used = max(emoji_counts.items(), key=lambda x: x[1]) if emoji_counts else ('N/A', 0)
        
        return {
            'total_selections': total_selections,
            'average_score': round(avg_score, 2),
            'unique_emojis_used': unique_emojis,
            'most_used_emoji': f"{most_used[0]} ({most_used[1]} times)",
            'recent_selections': self.emoji_selection_log[-5:]  # Last 5
        }
    
    def _to_snake_case(self, s: str) -> str:
        """Convert camelCase/PascalCase and separators to snake_case."""
        if not s:
            return s
        # Replace spaces and dashes with underscores first
        s = s.replace(' ', '_').replace('-', '_')
        # Insert underscores before capitals (camelCase -> snake_case)
        s = re.sub(r'(?<!^)(?=[A-Z])', '_', s)
        return s.lower()

    class _DefaultFormatterDict(dict):
        def __missing__(self, key):
            # Preserve unknown placeholders as-is (e.g., {Heading_1})
            return '{' + key + '}'

    def _safe_format_template(self, template: str, variables: dict) -> str:
        """Format a template with variables but keep unknown {placeholders} intact."""
        try:
            return template.format_map(self._DefaultFormatterDict(variables))
        except Exception as e:
            self.logger.warning(f"Safe format failed, returning template unformatted: {e}")
            return template
    
    def get_placeholder_color(self, placeholder_type):
        """Get the color code detected for a placeholder from AI response"""
        return self.placeholder_colors.get(placeholder_type)

    def generate_base_prompts(self, project_name: str, company_name: str, dimension_info: str = "") -> dict:
        """Generate context-aware base prompts for image creation using prompt manager."""
        prompts = {}
        for placeholder_type in ['image_1', 'image_2', 'logo', 'companyLogo', 'chart_1', 'backgroundImage']:
            prompts[placeholder_type] = prompt_manager.get_image_prompt(
                placeholder_type, 
                project_name=project_name, 
                company_name=company_name
            ) + f" {dimension_info}"
        return prompts
    
    def generate_content(self, placeholder_type, context="", profile=None, company_name="", project_name="", project_description="", **kwargs):
        """Generate content based on placeholder type and context using AI prompts
        
        Args:
            placeholder_type: The type of placeholder (e.g., 'Heading_1', 'Head1_para')
            context: General context
            profile: Profile type
            company_name: Company name
            project_name: Project name
            project_description: Project description
            **kwargs: Additional context (e.g., previous_headings, heading_content)
        """
        
        # Skip empty or quote-only placeholders
        if not placeholder_type or placeholder_type.strip() in ['"', "'", '']:
            self.logger.warning(f"Skipping invalid placeholder: '{placeholder_type}'")
            return f"[Invalid placeholder: {placeholder_type}]"
        
        # Load AI prompts from separated config file
        try:
            with open('config/prompts_text.json', 'r', encoding='utf-8') as f:
                text_prompts = json.load(f)
            
            # Try multiple variations to find the right prompt
            snake = self._to_snake_case(placeholder_type)
            variations = [
                placeholder_type,  # original
                placeholder_type.replace(' ', '_'),
                placeholder_type.replace('-', '_'),
                placeholder_type.lower(),
                snake,
                snake.title(),
                snake.capitalize(),
            ]
            
            prompt_key = None
            prompt_template = None
            for var in variations:
                prompt_template = text_prompts.get('prompts', {}).get(var)
                if prompt_template:
                    prompt_key = var
                    break
            
            if not prompt_template:
                raise ValueError(f"No AI prompt found for {placeholder_type}. Tried variations: {variations}")
            
            # Format the prompt with variables, preserving unknown placeholders
            variables = {
                'project_name': project_name or f"{context} Project",
                'company_name': company_name or context,
                'context': context,
                'project_description': project_description or ""
            }
            
            # Allow callers to pass additional placeholder values (e.g., resource titles)
            extra_variables = kwargs.get('extra_variables') or {}
            if isinstance(extra_variables, dict):
                for key, value in extra_variables.items():
                    if key not in variables and isinstance(key, str) and isinstance(value, str) and value:
                        variables[key] = value
            
            # Add heading content for para placeholders
            if 'heading_content' in kwargs and kwargs['heading_content']:
                heading_content = kwargs['heading_content']
                # Add a generic heading variable that can be used in prompts
                variables['heading'] = heading_content
                # Extract heading number from placeholder type (e.g., Head1_para -> 1)
                heading_match = re.search(r'Head(\d+)_para', placeholder_type)
                if heading_match:
                    heading_num = heading_match.group(1)
                    # Add specific heading variable (e.g., Heading_1, Heading_2)
                    variables[f'Heading_{heading_num}'] = heading_content
            
            # Add previous headings for sequential generation
            if 'previous_headings' in kwargs:
                for heading_name, heading_content in kwargs['previous_headings'].items():
                    variables[heading_name] = heading_content
            
            prompt = self._safe_format_template(prompt_template, variables)
            self.logger.debug(f"Prompt key: '{prompt_key}' for placeholder '{placeholder_type}'")
            self.logger.debug(f"Formatted prompt (first 200 chars): {prompt[:200]}")
        except Exception as e:
            self.logger.error(f"Error loading AI prompts: {e}")
            prompt = f"Generate appropriate content for {placeholder_type} related to {project_name} by {company_name}" \
                     f". Context: {project_description or context}. Output only the required text."
        
        # try:
        #     # Determine appropriate token limit based on placeholder type
        #     max_tokens = 180  # default
        #     if placeholder_type == 'conclusion_para':
        #         max_tokens = 300  # Allow more tokens for conclusion with bullets
        #     elif placeholder_type == 'our_process_desc':
        #         max_tokens = 300  # Also increase for process description

            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(
                prompt,
                generation_config={
                    'max_output_tokens': 180,
                    'temperature': 0.7,
                    'top_p': 0.9,
                    'top_k': 40,
                },
            )
            self._record_token_usage(response, label=f"text:{placeholder_type}")
            
            # Check safety ratings before accessing response.text
            if response.candidates and len(response.candidates) > 0:
                candidate = response.candidates[0]
                
                # Check if response was blocked by safety filters
                if hasattr(candidate, 'safety_ratings') and candidate.safety_ratings:
                    blocked = False
                    for rating in candidate.safety_ratings:
                        if rating.probability in ['HIGH', 'MEDIUM']:
                            self.logger.warning(f"Content blocked for {placeholder_type}: {rating.category} = {rating.probability}")
                            blocked = True
                    
                    if blocked:
                        self.logger.error(f"Content generation blocked by safety filters for {placeholder_type}. Using fallback content.")
                        return self._get_fallback_content(placeholder_type, project_name, company_name, project_description or context)
                
                # Check if response has valid parts
                if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts') and candidate.content.parts:
                    text = candidate.content.parts[0].text if hasattr(candidate.content.parts[0], 'text') else ""
                else:
                    self.logger.error(f"No valid content parts in response for {placeholder_type}. Using fallback content.")
                    return self._get_fallback_content(placeholder_type, project_name, company_name, project_description or context)
            else:
                self.logger.error(f"No candidates in response for {placeholder_type}. Using fallback content.")
                return self._get_fallback_content(placeholder_type, project_name, company_name, project_description or context)
            
            text = text.strip()
            self.logger.debug(f"Model raw response for '{placeholder_type}' (first 200 chars): {text[:200]}")

            # Special validation for conclusion_para
            if placeholder_type == 'conclusion_para':
                # Check for bullet duplicates
                bullet_lines = [line.strip() for line in text.split('\n') if line.strip().startswith('* ')]
                if len(bullet_lines) != len(set(bullet_lines)):
                    self.logger.warning(f"Duplicate bullets detected in conclusion_para. Bullets: {bullet_lines}")
                if len(bullet_lines) not in [4, 5]:
                    self.logger.warning(f"Expected 4 bullets, got {len(bullet_lines)} in conclusion_para")

            # Check if response contains a color code
            result = self._parse_text_and_color(text, placeholder_type)
            self.logger.debug(f"Parsed result for '{placeholder_type}': {result[:120] if isinstance(result, str) else result}")
            return result
        except Exception as e:
            self.logger.error(f"Error generating content for {placeholder_type}: {e}")
            return f"[Error generating content for {placeholder_type}]"
    
    def _parse_text_and_color(self, text, placeholder_type):
        """Parse text to extract content and color code if present"""
        # Look for color code pattern (e.g., #2563eb, #ABC123, #ff0000, #fff)
        color_pattern = r'(#[0-9A-Fa-f]{6}|#[0-9A-Fa-f]{3})'
        match = re.search(color_pattern, text)
        
        if match:
            # Extract color code
            color = match.group(1)
            
            # Normalize 3-digit hex to 6-digit if needed
            if len(color) == 4:  # #fff -> #ffffff
                color = '#' + color[1] + color[1] + color[2] + color[2] + color[3] + color[3]
            
            # Remove color code from text
            clean_text = re.sub(color_pattern, '', text).strip()
            # Remove any extra spaces or newlines
            clean_text = ' '.join(clean_text.split())
            
            # If only color code was provided (no text), return empty for color placeholders
            if not clean_text:
                # This is a color-only placeholder (like color1, color2)
                if 'color' in placeholder_type.lower() or 'circle' in placeholder_type.lower():
                    self.logger.info(f"Color-only placeholder {placeholder_type}: {color}")
                    # Store color but return empty text
                    if not hasattr(self, 'placeholder_colors'):
                        self.placeholder_colors = {}
                    self.placeholder_colors[placeholder_type] = color
                    return ""
                # For other placeholders, the color was in the text somewhere
                # But don't store for scope placeholders
                scope_placeholders = ['scope_desc', 'comprehensive_design_job', 'scope_of_project']
                if placeholder_type.lower() in [sp.lower() for sp in scope_placeholders]:
                    self.logger.warning(f"Color found for {placeholder_type} but not stored (uses auto-contrast)")
                else:
                    self.logger.warning(f"Only color found for {placeholder_type}: {color}")
            
            # Don't store color for scope placeholders - they use auto-contrast logic
            scope_placeholders = ['scope_desc', 'comprehensive_design_job', 'scope_of_project']
            if placeholder_type.lower() not in [sp.lower() for sp in scope_placeholders]:
                # Store the color for this placeholder
                if not hasattr(self, 'placeholder_colors'):
                    self.placeholder_colors = {}
                self.placeholder_colors[placeholder_type] = color
                self.logger.info(f"Detected color {color} for {placeholder_type}: '{clean_text}'")
            else:
                self.logger.info(f"Skipping color storage for {placeholder_type} (uses auto-contrast)")
            
            return clean_text if clean_text else ""
        else:
            # No color code found, return simplified text
            return self._simplify_text(placeholder_type, text)
    

    def generate_company_theme(self, company_name, project_name=None, logo_path=None):
        """Generate theme based on company name analysis (logo_path parameter kept for compatibility but not used)"""
        try:
            # Generate theme based on company name only
            self.logger.info(f"Generating theme based on company name: {company_name}")
            theme_data = self._generate_theme_from_company_name(company_name, project_name)
            return theme_data
            
        except Exception as e:
            self.logger.error(f"Error generating theme: {e}")
            raise e

    def generate_company_theme_name_only(self, company_name, project_name=None):
        """Generate theme based only on company name, skipping logo analysis entirely"""
        try:
            self.logger.info(f"Generating theme based on company name only: {company_name}")
            return self._generate_theme_from_company_name(company_name, project_name)
        except Exception as e:
            self.logger.error(f"Error generating name-based theme: {e}")
            raise e


    def _generate_theme_from_company_name(self, company_name, project_name=None):
        """Generate theme based on company name using prompt manager"""
        try:
            model = genai.GenerativeModel(self.model_name)
            
            # Get theme prompt from prompt manager
            prompt = prompt_manager.get_theme_prompt(
                'company_theme',
                company_name=company_name,
                project_name=project_name
            )
            
            # Add JSON format requirement with specific color guidance
            prompt += """
Return only valid JSON with these keys. Choose colors that match the company name's meaning and industry:
{
    "primary_color": "#hexcode (main brand color - should match company theme)",
    "secondary_color": "#hexcode (complementary color - should match company theme)", 
    "accent_color": "#hexcode (highlight color - should match company theme)",
    "text_color": "#1f2937",
    "background_color": "#ffffff",
    "theme_description": "Brief description of the theme and color choices",
    "industry": "Industry name based on company name",
    "brand_personality": "Brand personality based on company name",
    "target_audience": "Target audience",
    "source": "ai_generated"
}

Examples:
- Woodland: primary_color: "#228B22" (forest green), secondary_color: "#8B4513" (saddle brown), accent_color: "#32CD32" (lime green)
- Ocean: primary_color: "#0066CC" (ocean blue), secondary_color: "#87CEEB" (sky blue), accent_color: "#00CED1" (dark turquoise)
- Fire: primary_color: "#DC143C" (crimson), secondary_color: "#FF4500" (orange red), accent_color: "#FFD700" (gold)"""
            
            # Add timeout and retry logic for theme generation
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    self.logger.info(f"Theme generation API call attempt {attempt + 1}/{max_retries}")
                    response = model.generate_content(
                        prompt,
                        generation_config={
                            'max_output_tokens': 512,
                            'temperature': 0.3,
                            'top_p': 0.8,
                            'top_k': 20,
                        }
                    )
                    self._record_token_usage(response, label="theme_generation")
                    
                    # Check safety ratings before accessing response.text
                    if response.candidates and len(response.candidates) > 0:
                        candidate = response.candidates[0]
                        
                        # Check if response was blocked by safety filters
                        if hasattr(candidate, 'safety_ratings') and candidate.safety_ratings:
                            blocked = False
                            for rating in candidate.safety_ratings:
                                if rating.probability in ['HIGH', 'MEDIUM']:
                                    self.logger.warning(f"Theme generation blocked: {rating.category} = {rating.probability}")
                                    blocked = True
                            
                            if blocked:
                                self.logger.error(f"Theme generation blocked by safety filters. Attempt {attempt + 1}/{max_retries}")
                                if attempt == max_retries - 1:
                                    # Return default theme
                                    self.logger.warning("Using default theme due to repeated safety filter blocks")
                                    return {
                                        "primary_color": "#2563eb",
                                        "secondary_color": "#1e40af",
                                        "accent_color": "#3b82f6",
                                        "text_color": "#1f2937",
                                        "background_color": "#ffffff",
                                        "title_font_size": 28,
                                        "subtitle_font_size": 20,
                                        "body_font_size": 14,
                                        "font_family": "Arial",
                                        "title_style": "bold",
                                        "subtitle_style": "normal",
                                        "body_style": "normal",
                                        "theme_description": f"Professional theme for {company_name}",
                                        "industry": "General",
                                        "brand_personality": "professional",
                                        "target_audience": "B2B",
                                        "source": "default_fallback"
                                    }
                                continue  # Retry
                        
                        # Check if response has valid parts
                        if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts') and candidate.content.parts:
                            if hasattr(candidate.content.parts[0], 'text'):
                                response_text = candidate.content.parts[0].text
                                break  # Success, exit retry loop
                            else:
                                self.logger.warning(f"Theme response has no text part. Attempt {attempt + 1}/{max_retries}")
                                if attempt == max_retries - 1:
                                    raise ValueError("No text in theme response")
                                continue  # Retry
                        else:
                            self.logger.warning(f"Theme response has no valid content parts. Attempt {attempt + 1}/{max_retries}")
                            if attempt == max_retries - 1:
                                raise ValueError("No valid content in theme response")
                            continue  # Retry
                    else:
                        self.logger.warning(f"No candidates in theme response. Attempt {attempt + 1}/{max_retries}")
                        if attempt == max_retries - 1:
                            raise ValueError("No candidates in theme response")
                        continue  # Retry
                        
                except Exception as e:
                    self.logger.warning(f"Theme generation attempt {attempt + 1} failed: {e}")
                    if attempt == max_retries - 1:
                        raise e
                    # Wait before retry
                    import time
                    time.sleep(2 ** attempt)  # Exponential backoff
            
            # Clean the response text
            response_text = response_text.strip()
            
            # Remove any markdown formatting
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            # Try to parse JSON
            theme_data = json.loads(response_text)
            
            # Add missing keys with defaults if not present
            theme_data.setdefault("text_color", "#1f2937")
            theme_data.setdefault("background_color", "#ffffff")
            theme_data.setdefault("title_font_size", 28)
            theme_data.setdefault("subtitle_font_size", 20)
            theme_data.setdefault("body_font_size", 14)
            theme_data.setdefault("font_family", "Arial")
            theme_data.setdefault("title_style", "bold")
            theme_data.setdefault("subtitle_style", "normal")
            theme_data.setdefault("body_style", "normal")
            theme_data.setdefault("target_audience", "B2B")
            theme_data.setdefault("source", "company_name_analysis")
            
            # Log theme generation for monitoring
            self.logger.info(f"🎨 THEME GENERATED for {company_name}:")
            self.logger.info(f"   Primary: {theme_data.get('primary_color')}")
            self.logger.info(f"   Secondary: {theme_data.get('secondary_color')}")
            self.logger.info(f"   Accent: {theme_data.get('accent_color')}")
            self.logger.info(f"   Industry: {theme_data.get('industry')}")
            self.logger.info(f"   Description: {theme_data.get('theme_description')}")
            
            return theme_data
            
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON parsing error: {e}")
            self.logger.debug(f"Response text: {response_text if 'response_text' in locals() else 'No response'}")
        except Exception as e:
            self.logger.error(f"Error generating theme from company name: {e}")
            raise e


    def _get_fallback_content(self, placeholder_type, project_name, company_name, context):
        """Provide fallback content when AI generation is blocked by safety filters"""
        fallbacks = {
            'projectOverview': f"Comprehensive overview of {project_name} by {company_name}. This project addresses key business needs and delivers value through strategic implementation.",
            'property1': 'Innovative',
            'property2': 'Secure',
            'property3': 'Efficient',
            'Heading_1': 'Project Overview',
            'Heading_2': 'Key Features',
            'Heading_3': 'Implementation',
            'content_1': f"Overview of {project_name} demonstrating strategic value and implementation approach for {company_name}.",
            'bullet_1': f"Key features of {project_name}",
            'bullet_2': f"Strategic benefits for {company_name}",
            'bullet_3': f"Implementation approach and timeline",
            # Emoji fallbacks
            'logo_1': '🚀',
            'logo_2': '📊',
            'logo_3': '🎯',
            'logo_4': '💡',
            'logo_5': '⚡',
            'logo_6': '🌟',
            'logo2': '📊',
            'logo3': '🎯',
            'logo4': '💡',
            'logo5': '⚡',
            'logo6': '🌟',
        }
        
        fallback = fallbacks.get(placeholder_type)
        if fallback:
            self.logger.info(f"Using fallback content for {placeholder_type}: {fallback}")
            return fallback
        
        # Generic fallback
        self.logger.info(f"No specific fallback for {placeholder_type}, using generic fallback")
        return f"Content for {placeholder_type} related to {project_name} by {company_name}."
    
    def generate_comprehensive_content(self, project_name, company_name, project_description, context="", detected_placeholders=None, preset_values: Optional[dict] = None):
        """Generate comprehensive content for all placeholders in one Gemini call"""
        try:
            self.logger.info(f"Generating comprehensive content for {project_name} by {company_name}")
            
            # Find which side_Headings and side_Heads actually exist in the template
            available_side_headings = set()
            available_side_heads = set()
            if detected_placeholders:
                import re
                heading_pattern = re.compile(r'^side_Heading_(\d+)$', re.IGNORECASE)
                head_pattern = re.compile(r'^side_Head_(\d+)$', re.IGNORECASE)
                for ph in detected_placeholders:
                    name = ph.get('name') or ph.get('placeholder', '')
                    if name:
                        match = heading_pattern.match(name)
                        if match:
                            available_side_headings.add(int(match.group(1)))
                        match = head_pattern.match(name)
                        if match:
                            available_side_heads.add(int(match.group(1)))
            
            # Log detected side_Headings and side_Heads for debugging
            if available_side_headings:
                sorted_headings = sorted(available_side_headings)
                self.logger.info(f"📋 Comprehensive content: Detected side_Heading placeholders: {[f'side_Heading_{num}' for num in sorted_headings]}")
                self.logger.info(f"📋 Comprehensive content: Maximum side_Heading = {max(available_side_headings)}")
            else:
                self.logger.warning("⚠️ Comprehensive content: No side_Heading placeholders detected in template")
            
            if available_side_heads:
                sorted_heads = sorted(available_side_heads)
                self.logger.info(f"📋 Comprehensive content: Detected side_Head placeholders: {[f'side_Head_{num}' for num in sorted_heads]}")
            
            # Determine which side_Heading numbers need to be split (if side_Head exists for the same number)
            side_headings_to_split = available_side_headings & available_side_heads  # Intersection
            if side_headings_to_split:
                self.logger.info(f"✂️ Will split content for these side_Heading/side_Head pairs: {sorted(side_headings_to_split)}")
            
            # Build side_Heading prompts dynamically based on what exists
            # IMPORTANT: Skip side_Headings that already have preset values from project_description
            side_heading_prompts = ""
            if available_side_headings:
                # IMPORTANT: Only generate prompts for placeholders that actually exist
                # Don't use max to generate range - only use what's actually in the set
                max_side_heading = max(available_side_headings)
                
                # Filter out side_Headings that already have preset values
                side_headings_to_generate = []
                side_headings_skipped = []
                for i in sorted(available_side_headings):
                    heading_key = f'side_Heading_{i}'
                    if preset_values and heading_key in preset_values:
                        side_headings_skipped.append(i)
                        self.logger.info(f"⏭️ Skipping prompt for {heading_key} - using preset value: '{preset_values[heading_key]}'")
                    else:
                        side_headings_to_generate.append(i)
                
                if side_headings_skipped:
                    self.logger.info(f"📝 Using preset values for side_Headings: {side_headings_skipped}")
                
                if side_headings_to_generate:
                    self.logger.info(f"📝 Generating prompts for {len(side_headings_to_generate)} side_Heading placeholders (max: {max_side_heading})")
                    side_heading_templates = {
                        1: "Generate exactly 2-3 words (must include at least two separate words with spaces—no single hyphenated terms like 'Mobile-First') that describe a key feature of the project. Examples: 'Scalable Solution', 'Real-Time Platform', 'Secure Data Gateway'. Output only the words, no explanations.",
                        2: "Generate exactly 2-3 words (use spaces between words, no single hyphenated term) that describe another key feature of the project. Examples: 'Cloud Native Stack', 'AI Powered Automation', 'Data Driven Insights'. Output only the words, no explanations.",
                        3: "Generate exactly 2-3 words (multiple words required, no single hyphenated phrase) that describe a third key feature of the project. Examples: 'User Friendly Portal', 'Future Ready Architecture', 'Performance Optimized Core'. Output only the words, no explanations.",
                        4: "Generate exactly 2-3 words (must contain at least two words) that describe a fourth key feature of the project. Examples: 'Enterprise Grade Security', 'Innovation Driven Design', 'Scalable Customer Platform'. Output only the words, no explanations.",
                        5: "Generate exactly 2-3 words (multi-word phrase only, no single hyphenated tokens) that describe a fifth key feature of the project. Examples: 'Digital First Workflow', 'Automated Delivery Engine', 'Smart Analytics Layer'. Output only the words, no explanations.",
                        6: "Generate exactly 2-3 words (must include at least two separate words) that describe a sixth key feature of the project. Examples: 'Agile Delivery Model', 'Best Practice Toolkit', 'Modern Service Mesh'. Output only the words, no explanations.",
                        7: "Generate exactly 2-3 words (use spaces, no single hyphenated phrase) that describe a seventh key feature of the project. Output only the words, no explanations.",
                        8: "Generate exactly 2-3 words (use spaces, no single hyphenated phrase) that describe an eighth key feature of the project. Output only the words, no explanations.",
                        9: "Generate exactly 2-3 words (use spaces, no single hyphenated phrase) that describe a ninth key feature of the project. Output only the words, no explanations.",
                        10: "Generate exactly 2-3 words (use spaces, no single hyphenated phrase) that describe a tenth key feature of the project. Output only the words, no explanations.",
                        11: "Generate exactly 2-3 words (use spaces, no single hyphenated phrase) that describe an eleventh key feature of the project. Output only the words, no explanations.",
                        12: "Generate exactly 2-3 words (use spaces, no single hyphenated phrase) that describe a twelfth key feature of the project. Output only the words, no explanations.",
                        13: "Generate exactly 2-3 words (use spaces, no single hyphenated phrase) that describe a thirteenth key feature of the project. Output only the words, no explanations.",
                        14: "Generate exactly 2-3 words (use spaces, no single hyphenated phrase) that describe a fourteenth key feature of the project. Output only the words, no explanations.",
                        15: "Generate exactly 2-3 words (use spaces, no single hyphenated phrase) that describe a fifteenth key feature of the project. Output only the words, no explanations.",
                    }
                    
                    # CRITICAL: Only iterate through placeholders that need AI generation
                    for i in side_headings_to_generate:
                        if i <= 6:
                            prompt_text = side_heading_templates[i]
                        else:
                            ordinal = ["", "first", "second", "third", "fourth", "fifth", "sixth", 
                                      "seventh", "eighth", "ninth", "tenth", "eleventh", "twelfth",
                                      "thirteenth", "fourteenth", "fifteenth"][min(i, 15)]
                            prompt_text = f"Generate exactly 2-3 words that describe a {ordinal} key feature of the project. Use at least two separate words with spaces (no single hyphenated term). Output only the words, no explanations."
                        side_heading_prompts += f'    "side_Heading_{i}": "{prompt_text}",\n'
                    self.logger.info(f"✅ Generated prompts for side_Headings: {sorted(side_headings_to_generate)}")
                else:
                    self.logger.info(f"✅ All {len(available_side_headings)} side_Headings have preset values - no AI generation needed")
            else:
                # If no side_Headings detected, include all 15 (backward compatibility)
                self.logger.warning("No side_Headings detected, generating for all 15 (backward compatibility)")
                for i in range(1, 16):
                    if i <= 6:
                        ordinal = ["", "first", "second", "third", "fourth", "fifth", "sixth"][i]
                    else:
                        ordinal = ["", "", "", "", "", "", "", "seventh", "eighth", "ninth", "tenth", 
                                  "eleventh", "twelfth", "thirteenth", "fourteenth", "fifteenth"][i]
                    if i == 1:
                        prompt_text = "Generate exactly 2-3 words that describe a key feature of the project. Use at least two separate words with spaces (no single hyphenated term). Examples: 'Scalable Solution', 'Real-Time Platform', 'Secure Data Gateway'. Output only the words, no explanations."
                    elif i == 2:
                        prompt_text = "Generate exactly 2-3 words that describe another key feature of the project. Use multiple words separated by spaces (no single hyphenated term). Examples: 'Cloud Native Stack', 'AI Powered Automation', 'Data Driven Insights'. Output only the words, no explanations."
                    elif i == 3:
                        prompt_text = "Generate exactly 2-3 words that describe a third key feature of the project. Use multiple words separated by spaces (no single hyphenated term). Examples: 'User Friendly Portal', 'Future Ready Architecture', 'Performance Optimized Core'. Output only the words, no explanations."
                    elif i <= 6:
                        ordinal_map = {4: "fourth", 5: "fifth", 6: "sixth"}
                        prompt_text = f"Generate exactly 2-3 words that describe a {ordinal_map[i]} key feature of the project. Use at least two separate words with spaces (no single hyphenated term). Examples: 'Enterprise Grade Security', 'Innovation Driven Design', 'Scalable Customer Platform'. Output only the words, no explanations."
                    else:
                        prompt_text = f"Generate exactly 2-3 words that describe a {ordinal} key feature of the project. Use multiple words separated by spaces (no single hyphenated term). Output only the words, no explanations."
                    side_heading_prompts += f'    "side_Heading_{i}": "{prompt_text}",\n'
            
            # Build preset values section (ensure Gemini reuses provided placeholders)
            preset_section = ""
            preset_keys = set()
            if preset_values:
                important_keys = [
                    'p_r_1', 'p_r_2', 'p_r_3',
                    's_r_1', 's_r_2', 's_r_3',
                    'pr_desc_1', 'pr_desc_2', 'pr_desc_3',
                    'sr_desc_1', 'sr_desc_2', 'sr_desc_3'
                ]
                filtered = [
                    (key, value) for key, value in preset_values.items()
                    if isinstance(key, str) and isinstance(value, str) and value and key in important_keys
                ]
                if filtered:
                    preset_keys = {key for key, _ in filtered}
                    preset_section = "Existing placeholder values (use EXACTLY these for the matching placeholders):\n"
                    for key, value in filtered:
                        safe_value = value.replace('\n', ' ').strip()
                        preset_section += f"- {key}: {safe_value}\n"
                    preset_section += "\n"

            # Create comprehensive prompt for all content
            # Token accounting for comprehensive generation call
            token_usage = {
                'prompt_tokens': 0,
                'response_tokens': 0,
                'total_tokens': 0,
            }

            comprehensive_prompt = f"""
 You are preparing a professional presentation deck for a client. Generate comprehensive content for the following project:
 
 Project: {project_name}
 Company: {company_name}
 Project Description: {project_description}
 Context: {context}
 
 GLOBAL STYLE RULE: Whenever you need the possessive form of any company or project name, if the name already ends with the letter 's', do NOT add another 's'—use only an apostrophe (e.g., AIR 7 SEAS' journey). Apply this rule consistently across every piece of generated content.
 
{preset_section}Generate ALL the following content in a single JSON response. Be specific, professional, and engaging:

 {{
    "projectOverview": "Write a comprehensive project overview for '{project_name}' by {{company_name}}. Project Description: {{project_description}}. Structure: (1) One sentence defining what the project is and its core purpose, (2) One sentence on who it's built for and key functionality, (3) One sentence highlighting main benefits and value delivered. Use industry-specific terminology. Focus on streamlining, efficiency, real-time capabilities, and user-friendly aspects where relevant. Write 3-4 flowing sentences (50-65 words total) that showcase the platform's capabilities, target users, and cross-device/platform accessibility. Example style: 'A comprehensive [Type] designed to [purpose]. Built for [users], it ensures [benefits] across [platforms].'",
    "p_r_1": "Return a PRIMARY resource title (e.g., 'Project Manager', 'UX Designer', 'Frontend Developer') based on the project description. Output only the job title. If a preset value for p_r_1 is provided above, use it exactly.",
    "p_r_2": "Return a SECOND PRIMARY resource title, distinct from p_r_1. Output only the job title. If a preset value for p_r_2 is provided above, use it exactly.",
    "p_r_3": "Return a THIRD PRIMARY resource title, distinct from p_r_1 and p_r_2. Output only the job title. If a preset value for p_r_3 is provided above, use it exactly.",
    "pr_desc_1": "Write a clear responsibility description (8-12 words) for the {{p_r_1}} role in '{project_name}'. Based on '{{project_description}}', describe WHAT this role does and HOW they contribute. Do NOT repeat the exact role title. Use action phrases. Examples: 'Responsible for overall project planning, execution, and coordination' or 'Oversees strategy, timelines and ensures deliverables meet quality standards'. Output only the description.",
    "pr_desc_2": "Write a clear responsibility description (8-12 words) for the {{p_r_2}} role in '{project_name}'. Based on '{{project_description}}', describe WHAT this role does. Focus on design, user experience, or interface aspects if applicable. Example: 'Designs the intuitive and visually appealing user interface (UI) design that is user-friendly'. Output only the description.",
    "pr_desc_3": "Write a clear responsibility description (8-12 words) for the {{p_r_3}} role in '{project_name}'. Based on '{{project_description}}', describe WHAT this role does. Focus on implementation, development, or technical execution. Example: 'Implements responsive design and ensures seamless functionality across all elements of the website'. Output only the description.",
    "s_r_1": "Return a SECONDARY resource title typically needed for '{{project_description}}'. Common options: 'Backend Developer', 'Software Tester', 'Database Administrator', 'DevOps Engineer'. Choose based on project technical needs. Output only the job title.",
    "s_r_2": "Return a SECOND SECONDARY resource title, distinct from s_r_1. If s_r_1 was 'Backend Developer', choose 'Software Tester' or 'QA Engineer'. If technical project, choose testing/quality roles. Output only the job title.",
    "s_r_3": "Return a THIRD SECONDARY resource title based on '{{project_description}}' and {{project_category}}. Choose from support roles: 'Content Writer', 'SEO Specialist', 'Graphic Designer', 'Technical Writer', 'System Administrator'. Match project needs. Output only the job title.",
    "sr_desc_1": "Write a clear support description (8-12 words) for the {{s_r_1}} role in '{project_name}'. Based on '{{project_description}}', describe HOW this role supports the project technically. Focus on backend, infrastructure, or core systems work. Do NOT repeat the role name. Output only the description.",
    "sr_desc_2": "Write a clear support description (8-12 words) for the {{s_r_2}} role in '{project_name}'. Based on '{{project_description}}', describe HOW this role ensures quality, testing, or validation. Focus on QA, testing, or bug fixing work. Do NOT repeat the role name. Output only the description.",
    "sr_desc_3": "Write a clear support description (8-12 words) for the {{s_r_3}} role in '{project_name}'. Based on '{{project_description}}', describe HOW this role supports content, design, or auxiliary functions. Do NOT repeat the role name. Output only the description.",
     "content_1": "Write engaging content explaining the main concept and benefits. Use professional, clear language that highlights the project's value and impact.",
     "content_2": "Create additional supporting content elaborating on technical aspects and implementation details. Focus on how the project will be executed and delivered.",
     
    "bullet_1": "Create a concise, impactful bullet point (one sentence, 10-15 words) highlighting the MOST IMPORTANT feature or benefit of {project_name}. Based on '{project_description}', identify what delivers the highest value or addresses the most critical need. Focus on outcomes and results, not just features. Use action-oriented language. Start with a strong verb or noun.",
    "bullet_2": "Create a concise bullet point (one sentence, 10-15 words) highlighting a DIFFERENT key feature or benefit of {project_name} that complements bullet_1. From '{project_description}', identify a secondary value driver that addresses a different stakeholder need or business objective. Avoid overlap with bullet_1.",
    "bullet_3": "Create a concise bullet point (one sentence, 10-15 words) highlighting a THIRD key feature or benefit that completes the value proposition of {project_name}. From '{project_description}', identify an additional compelling aspect that addresses implementation, sustainability, scalability, or long-term value. Ensure it's distinct from bullets 1 and 2.",
    
    "Heading_1": "Based on '{{project_description}}', create a compelling project goal (2-5 words maximum) that captures a PRIMARY objective. Focus on impact-driven phrases. Examples: 'Celebrate Sporting Spirit', 'Enhance User Experience', 'Streamline Operations', 'Drive Digital Growth'. Use action words or outcome-focused language. Output only the goal phrase.",
    "Heading_2": "Based on '{{project_description}}', create a compelling project goal (2-5 words maximum) that captures a SECOND distinct objective, different from Heading_1. Focus on technical or experience aspects. Examples: 'Device-First Experience', 'Seamless Integration', 'Real-Time Insights'. Output only the goal phrase.",
    "Heading_3": "Based on '{{project_description}}', create a compelling project goal (2-5 words maximum) that captures a THIRD distinct objective. Focus on user/stakeholder onboarding, engagement, or workflow aspects. Examples: 'Player/Team Onboarding', 'Effortless Registration', 'Simplified Workflow'. Output only the goal phrase.",
    "Heading_4": "Based on '{{project_description}}', create a compelling project goal (2-5 words maximum) that captures a FOURTH distinct objective. Focus on performance, scalability, or reliability aspects. Examples: 'Scalable Infrastructure', 'Performance Excellence', 'Robust Architecture'. Output only the goal phrase.",
    "Heading_5": "Based on '{{project_description}}', create a compelling project goal (2-5 words maximum) that captures a FIFTH distinct objective. Focus on innovation, automation, or intelligence aspects. Examples: 'Smart Automation', 'Intelligent Analytics', 'Innovation-Driven Design'. Output only the goal phrase.",
    "Heading_6": "Based on '{{project_description}}', create a compelling project goal (2-5 words maximum) that captures a SIXTH distinct objective. Focus on growth, future-readiness, or sustainability aspects. Examples: 'Future-Ready Platform', 'Sustainable Growth', 'Long-term Viability'. Output only the goal phrase.",
    
    "Head1_para": "Based on '{{project_description}}' and 'Heading_1', write ONE clear sentence (10-15 words) explaining what we're trying to achieve with this goal. Focus on creating/building/showcasing specific aspects. Example: 'Create a platform that showcases teams, players and the energy of every match with storytelling'. Be concrete and action-oriented.",
    "Head2_para": "Based on '{{project_description}}' and 'Heading_2', write ONE clear sentence (10-15 words) explaining what we're trying to achieve with this goal. Focus on ensuring/enabling user experience across platforms/devices. Example: 'Ensure smooth navigation and real-time updates across mobile, tablet and desktop'. Be specific and user-focused.",
    "Head3_para": "Based on '{{project_description}}' and 'Heading_3', write ONE clear sentence (10-15 words) explaining what we're trying to achieve with this goal. Focus on allowing/enabling user actions, workflows, or processes. Example: 'Allow teams to register, create rosters and manage schedules without manual intervention'. Be process-oriented.",
    "Head4_para": "Based on '{{project_description}}' and 'Heading_4', write ONE clear sentence (10-15 words) explaining what we're trying to achieve with this goal. Focus on delivering/providing system capabilities, reliability, or performance. Be technical yet clear.",
    "Head5_para": "Based on '{{project_description}}' and 'Heading_5', write ONE clear sentence (10-15 words) explaining what we're trying to achieve with this goal. Focus on implementing/leveraging intelligent features, automation, or innovation. Be forward-thinking.",
    "Head6_para": "Based on '{{project_description}}' and 'Heading_6', write ONE clear sentence (10-15 words) explaining what we're trying to achieve with this goal. Focus on supporting/enabling growth, scalability, or long-term success. Be strategic.",
     
     "points_1": "Based on the project description and the feature 'side_Heading_1' (value provided above in preset section), write EXACTLY 2 bullet points about this feature. Format: First bullet: Describe what the feature is and how it works in the project context (10-15 words). Second bullet: Explain the business impact, benefits, or user experience improvements from a different angle (10-15 words). CRITICAL RULE: NEVER include 'side_Heading_1' or any individual words from 'side_Heading_1' in your response. Write descriptive content about the feature WITHOUT repeating its name. Example: If heading is 'Secure Payments', do NOT write 'secure' or 'payments' anywhere. Output format:Feature description and how it works\\n Business impact and benefits. Dont generate sentence: "Feature description and how it works" and "Business impact and benefits",
     "points_2": "Based on the project description and the feature 'side_Heading_2' (value provided above in preset section), write EXACTLY 2 bullet points about this feature. Format: First bullet: Describe what the feature is and how it works in the project context (10-15 words). Second bullet: Explain the business impact, benefits, or user experience improvements from a different angle (10-15 words). CRITICAL RULE: NEVER include 'side_Heading_2' or any individual words from 'side_Heading_2' in your response. Write descriptive content about the feature WITHOUT repeating its name. Example: If heading is 'Secure Payments', do NOT write 'secure' or 'payments' anywhere. Output format:Feature description and how it works\\n Business impact and benefits. Dont generate sentence: "Feature description and how it works" and "Business impact and benefits",
     "points_3": "Based on the project description and the feature 'side_Heading_3' (value provided above in preset section), write EXACTLY 2 bullet points about this feature. Format: First bullet: Describe what the feature is and how it works in the project context (10-15 words). Second bullet: Explain the business impact, benefits, or user experience improvements from a different angle (10-15 words). CRITICAL RULE: NEVER include 'side_Heading_3' or any individual words from 'side_Heading_3' in your response. Write descriptive content about the feature WITHOUT repeating its name. Example: If heading is 'Secure Payments', do NOT write 'secure' or 'payments' anywhere. Output format:Feature description and how it works\\n Business impact and benefits. Dont generate sentence: "Feature description and how it works" and "Business impact and benefits",
     "points_4": "Based on the project description and the feature 'side_Heading_4' (value provided above in preset section), write EXACTLY 2 bullet points about this feature. Format: First bullet: Describe what the feature is and how it works in the project context (10-15 words). Second bullet: Explain the business impact, benefits, or user experience improvements from a different angle (10-15 words). CRITICAL RULE: NEVER include 'side_Heading_4' or any individual words from 'side_Heading_4' in your response. Write descriptive content about the feature WITHOUT repeating its name. Example: If heading is 'Secure Payments', do NOT write 'secure' or 'payments' anywhere. Output format:Feature description and how it works\\n Business impact and benefits. Dont generate sentence: "Feature description and how it works" and "Business impact and benefits",
     "points_5": "Based on the project description and the feature 'side_Heading_5' (value provided above in preset section), write EXACTLY 2 bullet points about this feature. Format: First bullet: Describe what the feature is and how it works in the project context (10-15 words). Second bullet: Explain the business impact, benefits, or user experience improvements from a different angle (10-15 words). CRITICAL RULE: NEVER include 'side_Heading_5' or any individual words from 'side_Heading_5' in your response. Write descriptive content about the feature WITHOUT repeating its name. Example: If heading is 'Secure Payments', do NOT write 'secure' or 'payments' anywhere. Output format:Feature description and how it works\\n Business impact and benefits. Dont generate sentence: "Feature description and how it works" and "Business impact and benefits",
     "points_6": "Based on the project description and the feature 'side_Heading_6' (value provided above in preset section), write EXACTLY 2 bullet points about this feature. Format: First bullet: Describe what the feature is and how it works in the project context (10-15 words). Second bullet: Explain the business impact, benefits, or user experience improvements from a different angle (10-15 words). CRITICAL RULE: NEVER include 'side_Heading_6' or any individual words from 'side_Heading_6' in your response. Write descriptive content about the feature WITHOUT repeating its name. Example: If heading is 'Secure Payments', do NOT write 'secure' or 'payments' anywhere. Output format:Feature description and how it works\\n Business impact and benefits. Dont generate sentence: "Feature description and how it works" and "Business impact and benefits",
     "points_7": "Based on the project description and the feature 'side_Heading_7' (value provided above in preset section), write EXACTLY 2 bullet points about this feature. Format: First bullet: Describe what the feature is and how it works in the project context (10-15 words). Second bullet: Explain the business impact, benefits, or user experience improvements from a different angle (10-15 words). CRITICAL RULE: NEVER include 'side_Heading_7' or any individual words from 'side_Heading_7' in your response. Write descriptive content about the feature WITHOUT repeating its name. Example: If heading is 'Secure Payments', do NOT write 'secure' or 'payments' anywhere. Output format:Feature description and how it works\\n Business impact and benefits. Dont generate sentence: "Feature description and how it works" and "Business impact and benefits",
     "points_8": "Based on the project description and the feature 'side_Heading_8' (value provided above in preset section), write EXACTLY 2 bullet points about this feature. Format: First bullet: Describe what the feature is and how it works in the project context (10-15 words). Second bullet: Explain the business impact, benefits, or user experience improvements from a different angle (10-15 words). CRITICAL RULE: NEVER include 'side_Heading_8' or any individual words from 'side_Heading_8' in your response. Write descriptive content about the feature WITHOUT repeating its name. Example: If heading is 'Secure Payments', do NOT write 'secure' or 'payments' anywhere. Output format:Feature description and how it works\\n Business impact and benefits. Dont generate sentence: "Feature description and how it works" and "Business impact and benefits",
     "points_9": "Based on the project description and the feature 'side_Heading_9' (value provided above in preset section), write EXACTLY 2 bullet points about this feature. Format: First bullet: Describe what the feature is and how it works in the project context (10-15 words). Second bullet: Explain the business impact, benefits, or user experience improvements from a different angle (10-15 words). CRITICAL RULE: NEVER include 'side_Heading_9' or any individual words from 'side_Heading_9' in your response. Write descriptive content about the feature WITHOUT repeating its name. Example: If heading is 'Secure Payments', do NOT write 'secure' or 'payments' anywhere. Output format:Feature description and how it works\\n Business impact and benefits. Dont generate sentence: "Feature description and how it works" and "Business impact and benefits",
     "points_10": "Based on the project description and the feature 'side_Heading_10' (value provided above in preset section), write EXACTLY 2 bullet points about this feature. Format: First bullet: Describe what the feature is and how it works in the project context (10-15 words). Second bullet: Explain the business impact, benefits, or user experience improvements from a different angle (10-15 words). CRITICAL RULE: NEVER include 'side_Heading_10' or any individual words from 'side_Heading_10' in your response. Write descriptive content about the feature WITHOUT repeating its name. Example: If heading is 'Secure Payments', do NOT write 'secure' or 'payments' anywhere. Output format:Feature description and how it works\\n Business impact and benefits. Dont generate sentence: "Feature description and how it works" and "Business impact and benefits",
     "points_11": "Based on the project description and the feature 'side_Heading_11' (value provided above in preset section), write EXACTLY 2 bullet points about this feature. Format: First bullet: Describe what the feature is and how it works in the project context (10-15 words). Second bullet: Explain the business impact, benefits, or user experience improvements from a different angle (10-15 words). CRITICAL RULE: NEVER include 'side_Heading_11' or any individual words from 'side_Heading_11' in your response. Write descriptive content about the feature WITHOUT repeating its name. Example: If heading is 'Secure Payments', do NOT write 'secure' or 'payments' anywhere. Output format:Feature description and how it works\\n Business impact and benefits. Dont generate sentence: "Feature description and how it works" and "Business impact and benefits",
     "points_12": "Based on the project description and the feature 'side_Heading_12' (value provided above in preset section), write EXACTLY 2 bullet points about this feature. Format: First bullet: Describe what the feature is and how it works in the project context (10-15 words). Second bullet: Explain the business impact, benefits, or user experience improvements from a different angle (10-15 words). CRITICAL RULE: NEVER include 'side_Heading_12' or any individual words from 'side_Heading_12' in your response. Write descriptive content about the feature WITHOUT repeating its name. Example: If heading is 'Secure Payments', do NOT write 'secure' or 'payments' anywhere. Output format:Feature description and how it works\\n Business impact and benefits. Dont generate sentence: "Feature description and how it works" and "Business impact and benefits",
     "points_13": "Based on the project description and the feature 'side_Heading_13' (value provided above in preset section), write EXACTLY 2 bullet points about this feature. Format: First bullet: Describe what the feature is and how it works in the project context (10-15 words). Second bullet: Explain the business impact, benefits, or user experience improvements from a different angle (10-15 words). CRITICAL RULE: NEVER include 'side_Heading_13' or any individual words from 'side_Heading_13' in your response. Write descriptive content about the feature WITHOUT repeating its name. Example: If heading is 'Secure Payments', do NOT write 'secure' or 'payments' anywhere. Output format:Feature description and how it works\\n Business impact and benefits. Dont generate sentence: "Feature description and how it works" and "Business impact and benefits",
     "points_14": "Based on the project description and the feature 'side_Heading_14' (value provided above in preset section), write EXACTLY 2 bullet points about this feature. Format: First bullet: Describe what the feature is and how it works in the project context (10-15 words). Second bullet: Explain the business impact, benefits, or user experience improvements from a different angle (10-15 words). CRITICAL RULE: NEVER include 'side_Heading_14' or any individual words from 'side_Heading_14' in your response. Write descriptive content about the feature WITHOUT repeating its name. Example: If heading is 'Secure Payments', do NOT write 'secure' or 'payments' anywhere. Output format:Feature description and how it works\\n Business impact and benefits. Dont generate sentence: "Feature description and how it works" and "Business impact and benefits",
     "points_15": "Based on the project description and the feature 'side_Heading_15' (value provided above in preset section), write EXACTLY 2 bullet points about this feature. Format: First bullet: Describe what the feature is and how it works in the project context (10-15 words). Second bullet: Explain the business impact, benefits, or user experience improvements from a different angle (10-15 words). CRITICAL RULE: NEVER include 'side_Heading_15' or any individual words from 'side_Heading_15' in your response. Write descriptive content about the feature WITHOUT repeating its name. Example: If heading is 'Secure Payments', do NOT write 'secure' or 'payments' anywhere. Output format:Feature description and how it works\\n Business impact and benefits. Dont generate sentence: "Feature description and how it works" and "Business impact and benefits",
     
    "scope_desc": "Write a comprehensive scope description for '{project_name}' (30-40 words). Based on '{{project_description}}', outline: (1) What the project aims to build/deliver, (2) Key features and functionality elements (list 3-4 specific items), (3) Who it empowers/serves (target users), (4) Core benefits (real-time access, intuitive controls, scalability, etc.). Use professional PPT language. Example structure: 'This project aims to build a [type] that [streamlines/provides/enables] [key features]—empowering [users] with [benefits] and [capabilities].'",
    
    "footer": "Create professional footer text for {{company_name}}'s presentation about {project_name}. Include: company tagline or value statement, confidentiality notice if appropriate, contact information placeholder (e.g., 'For more information, contact [contact]'), and copyright year 2025. Adapt formality to industry standards. Keep to 2-3 lines.",
     
{side_heading_prompts.rstrip()}
     
     "p_b": "Return only a percentage (e.g., '25%') for Planning budget share based on effort estimation.",
     "d_b": "Return only a percentage (e.g., '35%') for Design budget share based on effort estimation.",
     "d_v": "Return only a percentage (e.g., '20%') for Development budget share based on effort estimation.",
     "d_p": "Return only a percentage (e.g., '20%') for Deployment/Production budget share based on effort estimation.",
     
    "conclusion": "Return only the word 'Conclusion'",
    "conclusion_para": "Write a powerful conclusion in professional PPT deck style for '{project_name}' and {{company_name}}. Based on '{{project_description}}', follow this structure: (1) Opening statement (40-50 words): 'As we embark on bdcode_'s journey to build [project], we're excited to unite strategy, technology and a deep understanding of the [domain/ecosystem]. This partnership represents the start of a [adjectives] digital platform built for excellence through its:' (2) Then list EXACTLY 4-5 major outcomes/takeaways as bullet points. Format: Start each with '* ' (asterisk + space), not '-'. Each bullet should be 2-4 words capturing key features/architecture/capabilities. Examples: '* Multi-Sport CMS Architecture' or '* Dynamic Homepage, Fixtures & Results'. Use industry-specific terminology. Total length: 60-70 words including bullets. Ensure bullets directly reflect core project features from description. CRITICAL: Provide exactly 4 or 5 bullets (no more, no less) and make every bullet unique—no repeated phrases or duplicate lines.",
    "our": "Return only the word 'Our'",
    "process": "Return only the word 'Process'",
    "our_process_desc": "Write a comprehensive process description (70-85 words) tailored to '{project_name}' and '{{project_description}}'. Structure: (1) Opening statement about your company's approach (e.g., 'At bdcode_, we follow a structured, collaborative process to bring [project] to life'), (2) List key phases: discovery/research, design, development, QA/testing, (3) Mention alignment with real-world workflows, (4) Closing statement about what the approach ensures (scalability, accuracy, performance), (5) End with final outcome: 'empowering [users] with a seamless [platform type] built for growth, engagement and long-term success.' Use professional PPT language with industry-specific terminology.",
     "budget": "Return only the word 'Budget'",
     "days": "Return the number of days along with the word 'days' (e.g., '28 days', '30 days', '45 days')",
     "project_timeline": "Return only the words 'Project Timeline'",
     "effort_estimation_?": "Return only the words 'Effort Estimation?'",
     "effort_estimation_q": "Return only the words 'Effort Estimation?'",
     "what_is_an": "Return only the words 'What is an'",
     "u2200": "Return only a double quote character '""'",
     "diverse_range_of_users": "Return only the words 'Diverse range of users'",
    "target_audience": "Return only the words 'Target Audience'",
    
    "breakup_1": "Using '{{project_description}}', {company_name}, and {{project_category}}, identify the PRIMARY audience/customer segment (2-4 words) most likely to request or benefit from this initiative. Labels must be presentation-ready persona titles (e.g., 'EV Fleet Leads', 'Players & Teams') and avoid vague buckets like 'Businesses' or 'Industry Partners'. Output only the segment label.",
    "breakup_2": "Identify a SECOND distinct segment (2-4 words) representing another high-value persona with a different motivation. Keep it concise and PPT friendly (e.g., 'Campus Mobility Heads', 'Fashion-Forward Buyers') and avoid generic phrases such as 'Transportation Partners'. Output only the segment label.",
    "breakup_3": "Identify a THIRD distinct segment (2-4 words) that broadens reach—secondary stakeholders, enthusiasts, or adjacent buyers (e.g., 'Sports Enthusiasts', 'Collectors Guild'). Make it specific, not a broad industry term. Output only the segment label.",
    "breakup_4": "Identify a FOURTH distinct segment (2-4 words) covering operational, partner, or channel audiences critical to delivery (e.g., 'Coaches & Staff', 'Retail Chain Leads'). Keep wording short and action-oriented. Output only the segment label.",
    "breakup_5": "Identify a FIFTH distinct segment (2-4 words) focusing on niche communities, premium buyers, or specialty groups relevant to the deck (e.g., 'Silk Connoisseurs', 'Luxury Craft Patrons'). Avoid generic multi-word business buckets. Output only the segment label.",
    "breakup_6": "Identify a SIXTH distinct segment (2-4 words) capturing broader consumers, sponsors, or ecosystem partners while staying specific (e.g., 'Regional Sponsors', 'Young Athletes'). No lengthy phrases or vague descriptors. Output only the segment label.",
    
    "b1": "Return a realistic percentage for PRIMARY audience segment (typically 25-35%). Consider importance and usage volume. Output format: '30%'",
    "b2": "Return a realistic percentage for SECOND audience segment (typically 15-25%). Should be lower than b1. Output format: '20%'",
    "b3": "Return a realistic percentage for THIRD audience segment (typically 10-20%). Should be lower than b2. Output format: '15%'",
    "b4": "Return a realistic percentage for FOURTH audience segment (typically 8-15%). Output format: '12%'",
    "b5": "Return a realistic percentage for FIFTH audience segment (typically 5-12%). Output format: '10%'",
    "b6": "Return a realistic percentage for SIXTH audience segment (typically 5-10%). Ensure all 6 percentages add up to approximately 100%. Output format: '8%'",
    
    "logo_1": "Based on 'Heading_1' concept and '{{project_description}}', select ONE emoji that MATCHES the goal's theme. Match the concept directly: If about celebration/achievement use 🏆 or 🎉; If about experience use 💻 or 📱; If about users/people use 👥 or ⛹🏻; If about growth use 📈 or 🚀; If about strategy use 🎯. Consider: Sports: 🏆⚽🏅⛹🏻; Tech: 💻📱⚡🔧; Business: 📊💼🎯; Achievement: 🏆🎖️🌟; Experience: 📱💻🎨. Choose what best represents the Heading_1 goal. Output only emoji.",
    "logo_2": "Based on 'Heading_2' concept and '{{project_description}}', select ONE emoji that MATCHES the goal's theme. If about device/mobile use 📱; If about data/analytics use 📊 or 📈; If about experience use 💻; If about connectivity use 🔗; If about real-time use ⚡. Match the specific concept in Heading_2. Output only emoji.",
    "logo_3": "Based on 'Heading_3' concept and '{{project_description}}', select ONE emoji that MATCHES the goal's theme. If about people/users use 👥 or ⛹🏻; If about onboarding use 📝 or 🎯; If about process use ⚙️ or 🔄; If about teams use 👥; If about registration use 📋. Match the specific concept in Heading_3. Output only emoji.",
    "logo_4": "Based on 'Heading_4' concept and '{{project_description}}', select ONE emoji that MATCHES the goal's theme. If about performance use 📈 or ⚡; If about architecture use 🏗️ or ⚙️; If about reliability use 🛡️ or ✅; If about quality use 🌟 or 💎; If about infrastructure use 🏗️. Match the specific concept in Heading_4. Output only emoji.",
    "logo_5": "Based on 'Heading_5' concept and '{{project_description}}', select ONE emoji that MATCHES the goal's theme. If about automation use 🤖 or ⚙️; If about intelligence use 🧠 or 💡; If about innovation use 🚀 or ✨; If about analytics use 📊; If about AI use 🤖. Match the specific concept in Heading_5. Output only emoji.",
    "logo_6": "Based on 'Heading_6' concept and '{{project_description}}', select ONE emoji that MATCHES the goal's theme. If about future use 🚀 or 🔮; If about growth use 📈 or 🌱; If about success use 🏆 or 🎯; If about sustainability use ♻️ or 🌱; If about scalability use 📈. Match the specific concept in Heading_6. Output only emoji.",
     
     "p_r_1": "Return a PRIMARY resource title (e.g., 'Project Manager', 'UX Designer', 'Frontend Developer') based on the project description. Output only the job title. If a preset value for p_r_1 is provided above, use it exactly.",
     "p_r_2": "Return a SECOND PRIMARY resource title, distinct from p_r_1. Output only the job title. Respect any preset values provided.",
     "p_r_3": "Return a THIRD PRIMARY resource title, distinct from p_r_1 and p_r_2. Output only the job title. Respect any preset values provided.",
     "pr_desc_1": "Write a concise description (8-10 words) of the primary resource's roles and responsibilities in relation to the nature of the project. Use the EXACT resource title already provided for pr_desc_1 (if any).",
     "pr_desc_2": "Write a concise description (8-10 words) of the second primary resource's roles and responsibilities. Use the EXACT resource title already provided for pr_desc_2 (if any).",
     "pr_desc_3": "Write a concise description (8-10 words) of the third primary resource's roles and responsibilities. Use the EXACT resource title already provided for pr_desc_3 (if any).",
     "s_r_1": "Return a SECONDARY resource title. Typically 'Backend Developer' or 'Software Tester'. Output only the job title. Respect any preset values provided.",
     "s_r_2": "Return a SECOND SECONDARY resource title. Output only the job title. Respect any preset values provided.",
     "s_r_3": "Return a THIRD SECONDARY resource title. Output only the job title. Respect any preset values provided.",
     "sr_desc_1": "Write a concise description (8-10 words) of the secondary resource's roles and responsibilities. Use the EXACT resource title already provided for sr_desc_1 (if any).",
     "sr_desc_2": "Write a concise description (8-10 words) of the second secondary resource's roles and responsibilities. Use the EXACT resource title already provided for sr_desc_2 (if any).",
     "sr_desc_3": "Write a concise description (8-10 words) of the third secondary resource's roles and responsibilities. Use the EXACT resource title already provided for sr_desc_3 (if any).",
 }}

Return ONLY valid JSON with all the above keys. No explanations, no markdown formatting, just the JSON object.
"""
            
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(
                comprehensive_prompt,
                generation_config={
                    'max_output_tokens': 2048,
                    'temperature': 0.7,
                    'top_p': 0.9,
                    'top_k': 40,
                }
            )
            
            usage_stats = self._record_token_usage(response, label="comprehensive_generation")
            if usage_stats:
                token_usage['prompt_tokens'] += usage_stats.get('prompt_tokens', 0)
                token_usage['response_tokens'] += usage_stats.get('response_tokens', 0)
                token_usage['total_tokens'] += usage_stats.get('total_tokens', 0)
            
            # Check safety ratings before accessing response
            if response.candidates and len(response.candidates) > 0:
                candidate = response.candidates[0]
                
                # Check if response was blocked by safety filters
                if hasattr(candidate, 'safety_ratings') and candidate.safety_ratings:
                    blocked = False
                    for rating in candidate.safety_ratings:
                        if rating.probability in ['HIGH', 'MEDIUM']:
                            self.logger.warning(f"Comprehensive content generation blocked: {rating.category} = {rating.probability}")
                            blocked = True
                    
                    if blocked:
                        self.logger.error("Comprehensive content generation blocked by safety filters. Using individual generation.")
                        return None
                
                # Check if response has valid parts
                if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts') and candidate.content.parts:
                    if hasattr(candidate.content.parts[0], 'text'):
                        response_text = candidate.content.parts[0].text.strip()
                    else:
                        self.logger.error("No text in comprehensive content response")
                        return None
                else:
                    self.logger.error("No valid content parts in comprehensive content response")
                    return None
            else:
                self.logger.error("No candidates in comprehensive content response")
                return None
            
            # Clean the response text
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            # Parse JSON
            try:
                comprehensive_content = json.loads(response_text)
                self.logger.info(f"Successfully generated comprehensive content with {len(comprehensive_content)} placeholders")
                
                # Add preset values for side_Headings that were skipped (user-provided values)
                if preset_values:
                    for key, value in preset_values.items():
                        if key.startswith('side_Heading_') and key not in comprehensive_content:
                            comprehensive_content[key] = value
                            self.logger.info(f"📝 Added preset side_Heading to comprehensive_content: {key} = '{value}'")
                
                # Split side_Heading content into side_Heading and side_Head if both exist
                self.logger.info(f"🔍 Checking for split: side_headings_to_split = {sorted(side_headings_to_split) if side_headings_to_split else 'empty set'}")
                if side_headings_to_split:
                    for num in side_headings_to_split:
                        heading_key = f'side_Heading_{num}'
                        head_key = f'side_Head_{num}'
                        
                        if heading_key in comprehensive_content:
                            full_text = comprehensive_content[heading_key].strip()
                            words = full_text.split()
                            
                            if len(words) == 1:
                                # 1 word: Put in side_Heading, leave side_Head empty
                                comprehensive_content[heading_key] = words[0]
                                comprehensive_content[head_key] = ""
                                self.logger.info(f"✂️ Split {heading_key}: '{words[0]}' | {head_key}: (empty)")
                            elif len(words) == 2:
                                # 2 words: First word in side_Heading, second in side_Head
                                comprehensive_content[heading_key] = words[0]
                                comprehensive_content[head_key] = words[1]
                                self.logger.info(f"✂️ Split {heading_key}: '{words[0]}' | {head_key}: '{words[1]}'")
                            elif len(words) >= 3:
                                # 3+ words: First 1-2 words in side_Heading, rest in side_Head
                                # Use 1 word if total is 3, use 2 words if total is 4+
                                split_at = 1 if len(words) == 3 else 2
                                comprehensive_content[heading_key] = ' '.join(words[:split_at])
                                comprehensive_content[head_key] = ' '.join(words[split_at:])
                                self.logger.info(f"✂️ Split {heading_key}: '{comprehensive_content[heading_key]}' | {head_key}: '{comprehensive_content[head_key]}'")
                        else:
                            self.logger.warning(f"⚠️ {heading_key} not found in comprehensive_content for splitting")
                else:
                    self.logger.info("ℹ️ No side_Heading/side_Head pairs to split")
                
                # Log resource titles/descriptions if present for debugging alignment issues
                for key in ['p_r_1', 'p_r_2', 'p_r_3', 's_r_1', 's_r_2', 's_r_3', 'pr_desc_1', 'pr_desc_2', 'pr_desc_3', 'sr_desc_1', 'sr_desc_2', 'sr_desc_3']:
                    if key in comprehensive_content:
                        value = comprehensive_content.get(key)
                        if isinstance(value, str):
                            preview = value.replace('\n', ' ').strip()
                            self.logger.info(f"📦 Comprehensive content: {key} = {preview}")
                self.logger.info(
                    "📊 Token usage for comprehensive generation - prompt: %s, response: %s, total: %s",
                    token_usage['prompt_tokens'],
                    token_usage['response_tokens'],
                    token_usage['total_tokens'],
                )
                return comprehensive_content
            except json.JSONDecodeError as e:
                self.logger.error(f"JSON parsing error in comprehensive content: {e}")
                self.logger.debug(f"Response text: {response_text[:500]}...")
                return None
                
        except Exception as e:
            self.logger.error(f"Error generating comprehensive content: {e}")
            return None

    def _map_comprehensive_to_placeholders(self, comprehensive_content, detected_placeholders):
        """Map comprehensive content keys to actual placeholder names in the template"""
        # Find which placeholders actually exist in the template
        available_placeholders = set()
        if detected_placeholders:
            for ph in detected_placeholders:
                name = ph.get('name') or ph.get('placeholder', '')
                if name:
                    available_placeholders.add(name)
        
        mapping = {
            # Direct mappings
            'projectOverview': 'projectOverview',
            'property1': 'property1',
            'property2': 'property2',
            'property3': 'property3',
            'content_1': 'content_1',
            'content_2': 'content_2',
            'bullet_1': 'bullet_1',
            'bullet_2': 'bullet_2',
            'bullet_3': 'bullet_3',
            'Heading_1': 'Heading_1',
            'Heading_2': 'Heading_2',
            'Heading_3': 'Heading_3',
            'Heading_4': 'Heading_4',
            'Heading_5': 'Heading_5',
            'Heading_6': 'Heading_6',
            'Head1_para': 'Head1_para',
            'Head2_para': 'Head2_para',
            'Head3_para': 'Head3_para',
            'Head4_para': 'Head4_para',
            'Head5_para': 'Head5_para',
            'Head6_para': 'Head6_para',
            'scope_desc': 'scope_desc',
            'footer': 'footer',
            'p_b': 'p_b',
            'd_b': 'd_b',
            'd_v': 'd_v',
            'd_p': 'd_p',
            'conclusion': 'conclusion',
            'conclusion_para': 'conclusion_para',
            'our': 'our',
            'process': 'process',
            'our_process_desc': 'our_process_desc',
            'out_process_desc': 'out_process_desc',
            'budget': 'budget',
            'days': 'days',
            'project_timeline': 'project_timeline',
            'effort_estimation_q': 'effort_estimation_q',
            'effort_estimation_?': 'effort_estimation_?',
            'what_is_an': 'what_is_an',
            'u2200': 'u2200',
            'diverse_range_of_users': 'diverse_range_of_users',
            'target_audience': 'target_audience',
            'breakup_1': 'breakup_1',
            'breakup_2': 'breakup_2',
            'breakup_3': 'breakup_3',
            'breakup_4': 'breakup_4',
            'breakup_5': 'breakup_5',
            'breakup_6': 'breakup_6',
            'b1': 'b1',
            'b2': 'b2',
            'b3': 'b3',
            'b4': 'b4',
            'b5': 'b5',
            'b6': 'b6',
            'logo_1': 'logo_1',
            'logo_2': 'logo_2',
            'logo_3': 'logo_3',
            'logo_4': 'logo_4',
            'logo_5': 'logo_5',
            'logo_6': 'logo_6',
            'points_1': 'points_1',
            'points_2': 'points_2',
            'points_3': 'points_3',
            'points_4': 'points_4',
            'points_5': 'points_5',
            'points_6': 'points_6',
            'points_7': 'points_7',
            'points_8': 'points_8',
            'points_9': 'points_9',
            'points_10': 'points_10',
            'points_11': 'points_11',
            'points_12': 'points_12',
            'points_13': 'points_13',
            'points_14': 'points_14',
            'points_15': 'points_15',
        }
        
        # Dynamically add side_Heading and side_Head mappings only for placeholders that exist in the template
        import re
        side_heading_pattern = re.compile(r'^side_Heading_(\d+)$', re.IGNORECASE)
        side_head_pattern = re.compile(r'^side_Head_(\d+)$', re.IGNORECASE)
        
        for placeholder_name in available_placeholders:
            # Add side_Heading_X mappings
            match = side_heading_pattern.match(placeholder_name)
            if match:
                mapping[placeholder_name] = placeholder_name
            
            # Add side_Head_X mappings
            match = side_head_pattern.match(placeholder_name)
            if match:
                mapping[placeholder_name] = placeholder_name
        
        # Static text placeholders that should be filled from prompts file
        static_placeholders = {
            'comprehensive_design_job': 'Comprehensive design job',
            'scope_of_project': 'Scope of the project',
            'project': 'Project',
            'overview': 'Overview',
            'project_goals': 'Project Goals',
            'projectGoal': 'Project Goal',
            'Project Goal': 'Project Goal',
            'design': 'Design',
            'inspiration': 'Inspiration',
            'team': 'Team',
            'composition': 'Composition',
            'conclusion': 'Conclusion',
            'our': 'Our',
            'process': 'Process',
            'out_process_desc': '',
            'budget': 'Budget',
            'project_timeline': 'Project Timeline',
            'effort_estimation_q': 'Effort Estimation?',
            'effort_estimation_?': 'Effort Estimation?',
            'what_is_an': 'What is an',
            'u0022': '\u201c',  # Left curly double quotation mark "
            'diverse_range_of_users': 'Diverse range of users',
            'target_audience': 'Target Audience'
        }
        
        # Get list of actual placeholder names from template
        # Use the same logic as available_placeholders to avoid mismatch
        actual_placeholders = []
        for ph in detected_placeholders:
            name = ph.get('name') or ph.get('placeholder', '')
            if name:
                actual_placeholders.append(name)
        
        mapped_content = {}
        
        # First, add static placeholder values
        for placeholder_name in actual_placeholders:
            if placeholder_name in static_placeholders:
                mapped_content[placeholder_name] = static_placeholders[placeholder_name]
                self.logger.info(f"Mapped static placeholder '{placeholder_name}' → '{static_placeholders[placeholder_name]}'")
        
        # Then, map comprehensive content
        for comp_key, comp_value in comprehensive_content.items():
            # First try direct mapping
            if comp_key in mapping:
                placeholder_name = mapping[comp_key]
                if placeholder_name in actual_placeholders:
                    mapped_content[placeholder_name] = comp_value
                else:
                    # Try with snake_case variations
                    snake_case_key = self._to_snake_case(comp_key)
                    if snake_case_key in actual_placeholders:
                        mapped_content[snake_case_key] = comp_value
                    else:
                        # Try camelCase
                        camel_case_key = comp_key.replace('_', '')
                        if camel_case_key in actual_placeholders:
                            mapped_content[camel_case_key] = comp_value
            else:
                # Check if the key itself is in actual placeholders
                if comp_key in actual_placeholders:
                    mapped_content[comp_key] = comp_value

        # Alias handling between similar placeholders present in different templates
        # Map our_process_desc content to out_process_desc if template uses that key
        if 'out_process_desc' in actual_placeholders and 'out_process_desc' not in mapped_content:
            if 'our_process_desc' in comprehensive_content:
                mapped_content['out_process_desc'] = comprehensive_content.get('our_process_desc')
        # Map to our_process if template uses this key
        if 'our_process' in actual_placeholders and 'our_process' not in mapped_content:
            alias_val = comprehensive_content.get('our_process') or comprehensive_content.get('our_process_desc') or comprehensive_content.get('out_process_desc')
            if alias_val:
                mapped_content['our_process'] = alias_val
        # Map effort_estimation variants
        if 'effort_estimation_?' in actual_placeholders and 'effort_estimation_?' not in mapped_content:
            alias_val = comprehensive_content.get('effort_estimation_?') or comprehensive_content.get('effort_estimation_q')
            if alias_val:
                mapped_content['effort_estimation_?'] = alias_val
        if 'effort_estimation_q' in actual_placeholders and 'effort_estimation_q' not in mapped_content:
            alias_val = comprehensive_content.get('effort_estimation_q') or comprehensive_content.get('effort_estimation_?')
            if alias_val:
                mapped_content['effort_estimation_q'] = alias_val

        # Support conclusion_desc alias to conclusion_para if content exists
        if 'conclusion_desc' in actual_placeholders and 'conclusion_desc' not in mapped_content:
            alias_val = comprehensive_content.get('conclusion_desc') or comprehensive_content.get('conclusion_para')
            if alias_val:
                mapped_content['conclusion_desc'] = alias_val
        
        return mapped_content

    def _simplify_text(self, placeholder_type, text):
        """Post-process to ensure clean, minimal output"""
        # Special handling for points placeholders - preserve bullet format
        if placeholder_type.startswith('points_'):
            # Convert escaped newlines to actual newlines
            text = text.replace('\\n', '\n')
            # Split by actual newlines or by bullet markers
            lines = text.split('\n')
            cleaned_lines = []
            for line in lines:
                line = line.strip()
                # Remove bullet markers if present (•, -, *)
                line = re.sub(r'^[•\-\*]\s*', '', line)
                line = re.sub(r'^\d+\.\s*', '', line)
                # Remove markdown but keep content
                line = re.sub(r'\*\*([^*]+)\*\*', r'\1', line)
                line = re.sub(r'\*([^*]+)\*', r'\1', line)
                if line and len(line) > 10:  # Only keep substantial lines
                    cleaned_lines.append(line)
            
            # If we have multiple lines, join with actual newlines
            if len(cleaned_lines) >= 2:
                return '\n'.join(cleaned_lines[:2])  # Keep max 2 bullet points
            elif len(cleaned_lines) == 1:
                # Single line - split by periods if it contains multiple sentences
                sentences = re.split(r'\.\s+', cleaned_lines[0])
                if len(sentences) >= 2:
                    return sentences[0] + '.\n' + sentences[1] + '.'
                else:
                    return cleaned_lines[0]
            else:
                # Fallback to original text processing
                text = text.replace('\n', ' ')
        
        # Special handling for conclusion_para - preserve * bullet markers for API formatting
        if placeholder_type == 'conclusion_para':
            # Convert escaped newlines to actual newlines
            text = text.replace('\\n', '\n')
            lines = text.split('\n')
            intro_lines = []
            bullet_lines = []
            seen_bullets = set()

            for raw_line in lines:
                line = raw_line.strip()
                if not line:
                    continue

                if line.startswith('* '):
                    # Preserve marker but strip markdown inside
                    cleaned_line = re.sub(r'\*\*([^*]+)\*\*', r'\1', line)
                    cleaned_line = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'\1', cleaned_line)
                    bullet_text = cleaned_line[2:].strip()
                    normalized = re.sub(r'\s+', ' ', bullet_text.lower())
                    if cleaned_line and len(bullet_text) > 2 and normalized not in seen_bullets:
                        seen_bullets.add(normalized)
                        bullet_lines.append(f"* {bullet_text}")
                else:
                    cleaned_line = re.sub(r'\*\*([^*]+)\*\*', r'\1', line)
                    cleaned_line = re.sub(r'\*([^*]+)\*', r'\1', cleaned_line)
                    if cleaned_line and len(cleaned_line) > 3:
                        intro_lines.append(cleaned_line)

            # Enforce a maximum of 5 bullets and keep order
            if len(bullet_lines) > 5:
                bullet_lines = bullet_lines[:5]

            if intro_lines or bullet_lines:
                result_lines = intro_lines + bullet_lines
                result = '\n'.join(result_lines)
                result = re.sub(r'[\[\](){}]', '', result)
                result = re.sub(r'["""]', '"', result)
                return result
            else:
                text = text.replace('\n', ' ')
        
        # Special handling for specific placeholders - return them directly
        if placeholder_type == '"':
            return '"'
        if placeholder_type == '\u201c':
            return '\u201c'
        if placeholder_type == 'Project Goal':
            return 'Project Goal'
        if placeholder_type == 'Project\nGoals':
            return 'Project Goals'
        
        # Remove markdown formatting and unwanted characters
        cleaned = re.sub(r'\*\*([^*]+)\*\*', r'\1', text or '')  # Remove **bold**
        cleaned = re.sub(r'\*([^*]+)\*', r'\1', cleaned)         # Remove *italic*
        cleaned = re.sub(r'`([^`]+)`', r'\1', cleaned)           # Remove `code`
        cleaned = re.sub(r'#+\s*', '', cleaned)                  # Remove # headers
        cleaned = re.sub(r'[\[\](){}]', '', cleaned)             # Remove brackets
        cleaned = re.sub(r'["""]', '"', cleaned)                 # Normalize quotes
        cleaned = re.sub(r'[^\w\s.,!?-]', '', cleaned)           # Keep only alphanumeric, spaces, basic punctuation
        
        # Remove repetitive words/phrases (common issue with AI generation)
        words = cleaned.split()
        if len(words) > 3:
            # Remove consecutive repeated words
            filtered_words = []
            prev_word = None
            for word in words:
                if word.lower() != prev_word:
                    filtered_words.append(word)
                    prev_word = word.lower()
            cleaned = ' '.join(filtered_words)
            
            # AGGRESSIVE handling for "content content content" pattern
            if 'content' in cleaned.lower():
                # Remove all repeated "content" words - keep only first occurrence
                words = cleaned.split()
                result_words = []
                content_seen = False
                for word in words:
                    if word.lower() == 'content':
                        if not content_seen:
                            result_words.append(word)
                            content_seen = True
                        # Skip subsequent "content" words
                    else:
                        result_words.append(word)
                        content_seen = False
                cleaned = ' '.join(result_words)
            
            # Additional check for repetitive patterns - but be less aggressive
            words = cleaned.split()
            if len(words) > 5:
                # Check for excessive repetition (same word appearing 3+ times in short succession)
                # Allow words to appear 2-3 times but not more
                word_counts_temp = {}
                final_words = []
                for i, word in enumerate(words):
                    word_lower = word.lower()
                    # Get previous few words
                    recent_words = [words[max(0, i-5):i]]
                    
                    # Count occurrences in last 5 words
                    recent_count = sum(1 for w in words[max(0, i-5):i] if w.lower() == word_lower)
                    
                    # Only skip if this word appeared multiple times recently
                    if recent_count < 2:
                        final_words.append(word)
                        word_counts_temp[word_lower] = word_counts_temp.get(word_lower, 0) + 1
                    # Skip if word appeared too many times recently
                cleaned = ' '.join(final_words)
        
        # Collapse whitespace
        cleaned = ' '.join(cleaned.split())
        
        # Word limits by type
        max_words_by_type = {
            'TITLE': 6,
            'SUBTITLE': 8,
            'CONTENT_1': 20,
            'CONTENT_2': 20,
            'BULLET_1': 40,
            'BULLET_2': 40,
            'BULLET_3': 40,
            'points_1': 30,
            'points_2': 30,
            'points_3': 30,
            'points_4': 30,
            'points_5': 30,
            'points_6': 30,
            'points_7': 30,
            'points_8': 30,
            'points_9': 30,
            'points_10': 30,
            'points_11': 30,
            'points_12': 30,
            'points_13': 30,
            'points_14': 30,
            'points_15': 30,
            'FOOTER': 10,
            'property1': 3,
            'property2': 3,
            'property3': 3,
            'projectOverview': 50,
            'scope_desc': 80,
            'project': 1,
            'overview': 1,
            'color1': 1,
            'color2': 1,
            'logo_1': 1,
            'Heading_1': 6 ,
            'Head1_para': 8,
            '"': 1,
            'u0022': 1,
            'Project Goal': 2,
            'logo2': 1,
            'logo3': 1,
            'logo4': 1,
            'logo5': 1,
            'logo6': 1,
            'Heading_2': 6,
            'Heading_3': 6,
            'Heading_4': 6,
            'Heading_6': 6,
            'Heading_6': 6,
            'Head2_para': 8,
            'Head3_para': 8,
            'Head4_para': 8,
            'Head5_para': 8,
            'Head6_para': 8,
            'Project\nGoals': 2,
            'logo_2': 1,
            'logo_3': 1,
            'logo_4': 1,
            'logo_5': 1,
            'logo_6': 1,
            'conclusion_para': 80,
            'our_process_desc': 80,
        }
        
        max_words = max_words_by_type.get(placeholder_type, 15)
        
        # Strip trailing punctuation for titles
        if placeholder_type == 'TITLE':
            cleaned = cleaned.rstrip('.!?,;:')
        
        # Enforce word cap - but only for non-emoji placeholders
        if placeholder_type not in ['logo_1', 'logo2', 'logo3', 'logo4', 'logo5', 'logo6', 'logo_2', 'logo_3', 'logo_4', 'logo_5', 'logo_6']:
            words = cleaned.split()
            if len(words) > max_words:
                # For paragraphs and scope_desc, try to end at a complete sentence
                if ('para' in placeholder_type or 'desc' in placeholder_type) and max_words >= 5:
                    # Find the last complete sentence within the word limit
                    truncated_words = words[:max_words]
                    truncated_text = ' '.join(truncated_words)
                    
                    # Try to end at a sentence boundary
                    last_period = truncated_text.rfind('.')
                    last_exclamation = truncated_text.rfind('!')
                    last_question = truncated_text.rfind('?')
                    
                    last_sentence_end = max(last_period, last_exclamation, last_question)
                    if last_sentence_end > 0:
                        cleaned = truncated_text[:last_sentence_end + 1]
                    else:
                        cleaned = truncated_text
                else:
                    cleaned = ' '.join(words[:max_words])
        
        return cleaned.strip()


    def generate_image(self, placeholder_type, context="", company_name="", project_name="", project_description="", image_requirements=None, theme=None, placeholder_dimensions=None, reference_image_path=None, company_website=None):
        """Generate image using Gemini's image generation capabilities
        
        Args:
            reference_image_path: Path to a reference image to use for generation (e.g., for zoomed-in background)
            company_website: (deprecated) retained for backward compatibility but unused
        """
        try:
            # Get image requirements from mapping or use defaults
            if not image_requirements:
                image_requirements = {
                    "aspect_ratio": "16:9",
                    "quality": "high",
                    "style": "professional, modern, corporate",
                    "lighting": "soft, balanced"
                }
            
            # Add placeholder dimensions to requirements if available
            if placeholder_dimensions:
                image_requirements['placeholder_width'] = placeholder_dimensions.get('width')
                image_requirements['placeholder_height'] = placeholder_dimensions.get('height')
                image_requirements['placeholder_unit'] = placeholder_dimensions.get('unit', 'PT')
            
            # Create detailed prompt for image generation with theme
            base_prompt = self._create_image_prompt(placeholder_type, context, company_name, project_name, project_description, image_requirements, theme, reference_image_path)
            
            self.logger.info(f"Generating image for {placeholder_type} with Gemini...")
            
            # Create output directory
            output_dir = "generated_images"
            os.makedirs(output_dir, exist_ok=True)
            
            # Use Gemini's image generation model
            try:
                model = genai.GenerativeModel(self.image_model_name)

                # Retry generation a few times – Gemini can occasionally return empty inline_data
                max_retries = 3
                image_parts = []
                last_error = None
                for attempt in range(max_retries):
                    try:
                        if reference_image_path and os.path.exists(reference_image_path):
                            self.logger.info(f"Using reference image: {reference_image_path} (attempt {attempt+1}/{max_retries})")
                            with open(reference_image_path, 'rb') as ref_file:
                                reference_image_data = ref_file.read()
                            response = model.generate_content([
                                {
                                    "mime_type": "image/jpeg",
                                    "data": reference_image_data
                                },
                                base_prompt
                            ])
                        else:
                            self.logger.info(f"Generating image (attempt {attempt+1}/{max_retries})")
                            response = model.generate_content(base_prompt)

                        self._record_token_usage(response, label=f"image:{placeholder_type}")

                        # Extract image data
                        image_parts = [
                            part.inline_data.data
                            for part in response.candidates[0].content.parts
                            if hasattr(part, "inline_data") and part.inline_data and hasattr(part.inline_data, "data")
                        ]
                        if image_parts:
                            break
                        else:
                            self.logger.warning("No image data in response – retrying...")
                    except Exception as e:
                        last_error = e
                        self.logger.warning(f"Gemini image generation attempt {attempt+1} failed: {e}")
                    # backoff
                    import time
                    time.sleep(1.5 * (attempt + 1))
                
                if image_parts:
                    image_data = image_parts[0]
                    
                    # Convert to PIL Image and ensure supported format/size
                    image = Image.open(BytesIO(image_data)).convert('RGB')
                    original_image = image.copy()  # Keep original uncropped copy for image_1
                    
                    # Generate filename
                    filename = f"{placeholder_type}_{company_name.replace(' ', '_')}_{hash(base_prompt) % 10000}.png"
                    filepath = os.path.join(output_dir, filename)
                    
                    # For image_1, save the original uncropped version first
                    original_filepath = None
                    if placeholder_type == 'image_1':
                        original_filename = filename.replace('.png', '_original.jpg')
                        original_filepath = os.path.join(output_dir, original_filename)
                        original_image.save(original_filepath, format='JPEG', quality=95, optimize=False)
                        self.logger.info(f"Saved original uncropped image_1: {original_filepath} (size: {original_image.width}x{original_image.height} px)")
                    
                    # Crop image to match placeholder aspect ratio (crop only, no resize to maintain quality)
                    crop_properties = None  # Not used - images are pre-cropped before upload
                    if placeholder_dimensions and placeholder_dimensions.get('width') and placeholder_dimensions.get('height'):
                        target_width = int(placeholder_dimensions['width'])
                        target_height = int(placeholder_dimensions['height'])
                        if placeholder_type in ['logo', 'companyLogo']:
                            # Use RGBA for logos to maintain transparency and quality
                            if image.mode != 'RGBA':
                                image = image.convert('RGBA')
                            # Resize to EXACT placeholder dimensions - logos must fit precisely
                            image = image.resize((target_width, target_height), Image.Resampling.LANCZOS)
                            # Verify exact dimensions match
                            if image.width != target_width or image.height != target_height:
                                self.logger.warning(f"Logo resize mismatch: got {image.width}x{image.height}, expected {target_width}x{target_height}")
                                # Force exact dimensions if mismatch
                                image = image.resize((target_width, target_height), Image.Resampling.LANCZOS)
                            self.logger.info(f"✅ Logo resized to EXACT placeholder dimensions: {image.width}x{image.height} px (target: {target_width}x{target_height} PT)")
                        else:
                            # Crop image to match exact placeholder dimensions (in PT/pixels)
                            # target_width and target_height are already in PT (converted from inches if needed)
                            original_size = (image.width, image.height)
                            image = self._crop_image_to_dimensions(image, target_width, target_height, placeholder_type)
                            final_size = (image.width, image.height)
                            self.logger.info(f"Cropped {placeholder_type}: {original_size[0]}x{original_size[1]} -> {final_size[0]}x{final_size[1]} (target: {target_width}x{target_height} PT)")
                            
                            # Only resize if image is too large for performance (maintain quality otherwise)
                            max_dimension = 2048  # Max width or height
                            if image.width > max_dimension or image.height > max_dimension:
                                scale = min(max_dimension / image.width, max_dimension / image.height)
                                new_w = int(image.width * scale)
                                new_h = int(image.height * scale)
                                image = image.resize((new_w, new_h), Image.Resampling.LANCZOS)
                                self.logger.info(f"Downsized {placeholder_type} for performance: {final_size[0]}x{final_size[1]} -> {new_w}x{new_h}")
                    else:
                        self.logger.warning(f"No placeholder dimensions provided for {placeholder_type}, skipping crop/resize")
                        # Resize if overly large (Slides fetch limits and performance)
                        max_width, max_height = 1920, 1080
                        if image.width > max_width or image.height > max_height:
                            image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

                    # Save with appropriate quality settings
                    is_logo = placeholder_type in ["logo", "companyLogo"]
                    if is_logo:
                        # Save logos with maximum quality (no compression)
                        image.save(filepath, format='PNG', optimize=False, compress_level=0)
                    else:
                        # Prefer JPEG for photographic content to reduce size
                        filepath = os.path.join(output_dir, filename.replace('.png', '.jpg'))
                        image.save(filepath, format='JPEG', quality=85, optimize=True, progressive=True)
                    
                    # Log final dimensions - verify logos match exactly
                    if placeholder_dimensions and placeholder_dimensions.get('width') and placeholder_dimensions.get('height'):
                        target_w = int(placeholder_dimensions['width'])
                        target_h = int(placeholder_dimensions['height'])
                        if placeholder_type in ['logo', 'companyLogo']:
                            # Verify logo dimensions match exactly
                            if image.width == target_w and image.height == target_h:
                                self.logger.info(f"✅ Logo saved: {filepath} (EXACT match: {image.width}x{image.height} px = {target_w}x{target_h} PT)")
                            else:
                                self.logger.error(f"❌ Logo dimension mismatch: {filepath} (got {image.width}x{image.height} px, expected {target_w}x{target_h} PT)")
                        else:
                            self.logger.info(f"Image saved: {filepath} (size: {image.width}x{image.height} px, target: {target_w}x{target_h} PT)")
                    else:
                        self.logger.info(f"Image generated successfully: {filepath} (size: {image.width}x{image.height})")
                    
                    # Return absolute path, crop properties, and original path (if image_1)
                    original_path = os.path.abspath(original_filepath) if original_filepath and os.path.exists(original_filepath) else None
                    return (os.path.abspath(filepath), crop_properties, original_path)
                else:
                    self.logger.warning("No image data in response after retries – creating fallback image")
                    fallback_path = self._create_fallback_image(
                        placeholder_type=placeholder_type,
                        company_name=company_name,
                        project_name=project_name,
                        theme=theme,
                        placeholder_dimensions=placeholder_dimensions
                    )
                    if fallback_path and os.path.exists(fallback_path):
                        return (os.path.abspath(fallback_path), None, None)
                    # If fallback also failed, bubble up the last error
                    raise ValueError("No image data received from Gemini")
                
            except Exception as e:
                self.logger.error(f"Gemini image generation error: {e}")
                raise e
            
        except Exception as e:
            # Last-resort fallback
            self.logger.error(f"Error generating image for {placeholder_type}: {e}")
            try:
                fallback_path = self._create_fallback_image(
                    placeholder_type=placeholder_type,
                    company_name=company_name,
                    project_name=project_name,
                    theme=theme,
                    placeholder_dimensions=placeholder_dimensions
                )
                if fallback_path and os.path.exists(fallback_path):
                    self.logger.info(f"Returned fallback image for {placeholder_type}: {fallback_path}")
                    return (os.path.abspath(fallback_path), None, None)
            except Exception as fe:
                self.logger.warning(f"Fallback image creation failed: {fe}")
            raise e

    def crop_existing_image(self, source_image_path, target_dimensions, output_filename=None, resize_to_exact=False):
        """
        Crop an existing image file to target dimensions using "cover" mode.
        Like CSS object-fit: cover - scales the image to fill the target area (maintaining aspect ratio),
        then crops any overflow. This ensures no stretching/distortion.
        
        Args:
            source_image_path: Path to the source image file
            target_dimensions: Dict with 'width', 'height', 'unit' (in PT, will be converted if needed)
            output_filename: Optional custom filename, otherwise auto-generated
            resize_to_exact: If True, force resize to exact dimensions (safety net, usually not needed with cover mode)
        
        Returns:
            Path to the cropped image file, or None if error
        """
        try:
            if not os.path.exists(source_image_path):
                self.logger.error(f"Source image not found: {source_image_path}")
                return None
            
            # Convert dimensions to PT if needed
            target_width = float(target_dimensions.get('width', 0))
            target_height = float(target_dimensions.get('height', 0))
            unit = target_dimensions.get('unit', 'PT').upper()
            
            if unit in ('IN', 'INCH', 'INCHES'):
                target_width = target_width * 72.0
                target_height = target_height * 72.0
            
            target_width = int(target_width)
            target_height = int(target_height)
            
            if target_width <= 0 or target_height <= 0:
                self.logger.error(f"Invalid target dimensions: {target_width}x{target_height}")
                return None
            
            # Load source image
            with Image.open(source_image_path) as image:
                original_size = (image.width, image.height)
                image = image.convert('RGB')  # Ensure RGB
                
                # Crop to target dimensions
                cropped_image = self._crop_image_to_dimensions(image, target_width, target_height, 'cropped_copy')
                
                # If resize_to_exact is True, resize the cropped image to exact target dimensions
                if resize_to_exact:
                    if cropped_image.width != target_width or cropped_image.height != target_height:
                        cropped_image = cropped_image.resize((target_width, target_height), Image.Resampling.LANCZOS)
                        self.logger.info(f"Resized cropped image to exact dimensions: {target_width}x{target_height} PT")
                
                final_size = (cropped_image.width, cropped_image.height)
                
                # Generate output filename
                if not output_filename:
                    base_name = os.path.basename(source_image_path)
                    name_part = os.path.splitext(base_name)[0]
                    ext = '.jpg'
                    output_filename = f"{name_part}_cropped_{target_width}x{target_height}{ext}"
                
                output_dir = "generated_images"
                os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, output_filename)
                
                # Save cropped image
                cropped_image.save(output_path, format='JPEG', quality=85, optimize=True, progressive=True)
                
                self.logger.info(f"Cropped copy: {source_image_path} ({original_size[0]}x{original_size[1]}) -> {output_path} ({final_size[0]}x{final_size[1]}, target: {target_width}x{target_height} PT)")
                
                return os.path.abspath(output_path)
                
        except Exception as e:
            self.logger.error(f"Failed to crop existing image: {e}")
            return None
    
    def _crop_image_to_dimensions(self, image, target_width_pt, target_height_pt, placeholder_type):
        """
        Crop image based on target dimensions (in PT/pixels) using "cover" mode.
        Like CSS object-fit: cover - scales image to fill the target area (maintaining aspect ratio),
        then crops any overflow. This ensures no stretching/distortion.
        Uses center crop to preserve the most important part of the image.
        """
        try:
            if not IMAGE_CROP_SETTINGS.get('enabled', True):
                return image

            img_width, img_height = image.size
            target_width = int(target_width_pt)
            target_height = int(target_height_pt)
            
            if target_width <= 0 or target_height <= 0:
                self.logger.warning(f"Invalid target dimensions: {target_width}x{target_height} PT")
                return image
            
            # Check if image already matches target dimensions closely
            width_diff = abs(img_width - target_width) / target_width if target_width > 0 else 1.0
            height_diff = abs(img_height - target_height) / target_height if target_height > 0 else 1.0
            epsilon = 0.01  # 1% tolerance
            
            if width_diff < epsilon and height_diff < epsilon:
                # Image already matches target dimensions, no crop needed
                self.logger.debug(f"Image dimensions match target ({img_width}x{img_height} vs {target_width}x{target_height} PT), no crop needed")
                return image

            # COVER MODE: Scale image to fill target area (like CSS object-fit: cover)
            # Calculate scale factor needed to cover the target area
            scale_x = target_width / img_width
            scale_y = target_height / img_height
            
            # Use the larger scale factor to ensure the image covers the entire area
            scale = max(scale_x, scale_y)
            
            # Calculate new dimensions after scaling
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            
            self.logger.info(f"🖼️ COVER MODE: Scaling image from {img_width}x{img_height} to {new_width}x{new_height} (scale: {scale:.3f})")
            
            # Resize image to new dimensions (this ensures it fills the target area)
            scaled_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Now crop the scaled image to exact target dimensions (center crop)
            left = (new_width - target_width) // 2
            top = (new_height - target_height) // 2
            right = left + target_width
            bottom = top + target_height
            
            # Ensure crop bounds are valid
            left = max(0, min(left, new_width - target_width))
            top = max(0, min(top, new_height - target_height))
            right = left + target_width
            bottom = top + target_height
            
            # Crop the scaled image
            cropped = scaled_image.crop((left, top, right, bottom))
            self.logger.info(f"✅ COVER MODE COMPLETE: {img_width}x{img_height} -> scaled to {new_width}x{new_height} -> cropped to {cropped.width}x{cropped.height} (target: {target_width}x{target_height} PT)")
            
            return cropped
            
        except Exception as e:
            self.logger.warning(f"Failed to crop image to dimensions: {e}, returning original")
            return image

    def _create_image_prompt(self, placeholder_type, context, company_name, project_name, project_description, requirements, theme=None, reference_image_path=None):
        """Create image generation prompt using AI prompts with exact dimensions"""
        # Load AI prompts from JSON file
        try:
            with open('config/prompts_image.json', 'r', encoding='utf-8') as f:
                image_prompts = json.load(f)
            
            # Get prompt for this placeholder type from prompts section
            prompt_template = image_prompts.get('prompts', {}).get(placeholder_type)
            if not prompt_template:
                raise ValueError(f"No AI image prompt found for {placeholder_type}")
            
            # Get exact dimensions
            width = requirements.get('placeholder_width', '800')
            height = requirements.get('placeholder_height', '600')
            unit = requirements.get('placeholder_unit', 'PT')
            
            # Format the prompt with variables including exact dimensions
            prompt = prompt_template.format(
                project_name=project_name or f"{context} Project",
                company_name=company_name or context,
                context=context,
                project_description=project_description or "",
                placeholder_width=width,
                placeholder_height=height,
                placeholder_unit=unit
            )
            
            # Special handling for backgroundImage with reference image
            # When reference_image_path is provided, instruct Gemini to use it as the basis
            if placeholder_type == 'backgroundImage' and reference_image_path and os.path.exists(reference_image_path):
                prompt += " IMPORTANT: Use the provided reference image (image_1) as the basis for this background. Create a background version that maintains the same visual style, colors, and theme as the reference image, but adapt it for use as a subtle background suitable for text overlay. Keep the same industry context and visual identity from the reference image."
            
            # Add theme color information if available
            if theme:
                primary_color = theme.get('primary_color', '#2563eb')
                secondary_color = theme.get('secondary_color', '#1e40af')
                accent_color = theme.get('accent_color', '#3b82f6')
                theme_colors = f" Use brand colors: primary {primary_color}, secondary {secondary_color}, accent {accent_color}."
                prompt += theme_colors
            
            return prompt
            
        except Exception as e:
            self.logger.error(f"Error loading AI image prompts: {e}")
            raise e

    def _create_fallback_image(self, placeholder_type, company_name, project_name, theme=None, placeholder_dimensions=None):
        """Create a simple on-disk fallback image when Gemini returns no data.

        The fallback is a dark background with a subtle gradient band using theme colors
        and a small centered label of the placeholder name for identification.
        """
        try:
            width = int((placeholder_dimensions or {}).get('width') or 1280)
            height = int((placeholder_dimensions or {}).get('height') or 720)

            # Colors
            primary = (31, 41, 55)  # #1f2937 base dark gray
            if theme and theme.get('primary_color'):
                # Convert hex to rgb
                hex_val = theme['primary_color'].lstrip('#')
                primary = (int(hex_val[0:2], 16), int(hex_val[2:4], 16), int(hex_val[4:6], 16))

            from PIL import Image, ImageDraw
            img = Image.new('RGB', (width, height), (0, 0, 0))
            draw = ImageDraw.Draw(img)

            # Gradient band
            import math
            for y in range(height):
                t = y / max(1, height-1)
                mix = 0.2 + 0.6 * (0.5 - abs(t - 0.5))  # strongest in middle
                r = int((1 - mix) * 16 + mix * primary[0])
                g = int((1 - mix) * 16 + mix * primary[1])
                b = int((1 - mix) * 16 + mix * primary[2])
                draw.line([(0, y), (width, y)], fill=(r, g, b))

            # Optional label
            label = f"{placeholder_type}".strip()
            if label:
                # Simple centered text using default font (no external deps)
                text_color = (240, 240, 240)
                # Approximate width/height for centering (default font has no measure in PIL without ImageFont)
                text_w = min(width - 40, max(120, len(label) * 10))
                text_h = 24
                # Draw a subtle pill background
                pad_x, pad_y = 20, 10
                rect_w = text_w + pad_x
                rect_h = text_h + pad_y
                x0 = (width - rect_w) // 2
                y0 = (height - rect_h) // 2
                draw.rounded_rectangle([x0, y0, x0 + rect_w, y0 + rect_h], radius=12, fill=(0, 0, 0,))
                # Place text (rough centering)
                tx = x0 + pad_x // 2
                ty = y0 + pad_y // 2
                draw.text((tx, ty), label, fill=text_color)

            # Save
            os.makedirs('generated_images', exist_ok=True)
            filename = f"fallback_{placeholder_type}_{company_name.replace(' ', '_')}_{project_name.replace(' ', '_')}.jpg"
            path = os.path.join('generated_images', filename)
            img.save(path, format='JPEG', quality=88)
            self.logger.info(f"Fallback image created for {placeholder_type}: {path}")
            return path
        except Exception as e:
            self.logger.error(f"Failed to create fallback image: {e}")
            return None



    def enhance_image_for_background(self, source_image_path, target_dimensions, context, company_name, project_name, theme=None):
        """Enhance an existing image for use as background with specific dimensions"""
        try:
            
            # Load the source image
            with Image.open(source_image_path) as source_img:
                # Convert to RGB if needed
                if source_img.mode != 'RGB':
                    source_img = source_img.convert('RGB')
                
                # Get target dimensions
                target_width = int(target_dimensions.get('width', 1920))
                target_height = int(target_dimensions.get('height', 1080))
                
                # Create enhanced prompt for background
                enhanced_prompt = f"Transform this into a professional presentation background for {project_name} by {company_name}. Maintain core elements, subtle for text overlay. {target_width}x{target_height}px."
                
                # Add theme colors if available
                if theme:
                    primary_color = theme.get('primary_color', '#2563eb')
                    secondary_color = theme.get('secondary_color', '#1e40af')
                    accent_color = theme.get('accent_color', '#3b82f6')
                    theme_colors = f" Brand colors: primary {primary_color}, secondary {secondary_color}, accent {accent_color}."
                    enhanced_prompt += theme_colors
                
                # Generate enhanced image using Gemini
                try:
                    enhanced_image_path = self._generate_enhanced_image_with_gemini(
                        source_image_path, enhanced_prompt, target_width, target_height
                    )
                    if enhanced_image_path and os.path.exists(enhanced_image_path):
                        return enhanced_image_path
                except Exception as e:
                    self.logger.error(f"Gemini enhancement failed: {e}")
                    raise e
                
        except Exception as e:
            self.logger.error(f"Error enhancing image for background: {e}")
            raise e

    def _generate_enhanced_image_with_gemini(self, source_image_path, prompt, target_width, target_height):
        """Generate enhanced image using Gemini with source image reference"""
        try:
            # Read the source image
            with open(source_image_path, 'rb') as f:
                source_image_data = f.read()
            
            # Create the request with source image
            request = {
                "contents": [{
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": source_image_data.hex()
                            }
                        }
                    ]
                }],
                "generationConfig": {
                    "temperature": 0.4,
                    "topK": 32,
                    "topP": 1,
                    "maxOutputTokens": 4096,
                }
            }
            
            # Call Gemini API
            response = self.gemini_model.generate_content(
                request['contents'][0]['parts'][0]['text'],
                request['contents'][0]['parts'][1]
            )
            self._record_token_usage(response, label="image_enhancement")
            
            if response and hasattr(response, 'parts') and response.parts:
                # Extract image data
                for part in response.parts:
                    if hasattr(part, 'inline_data') and part.inline_data:
                        image_data = bytes.fromhex(part.inline_data.data)
                        
                        # Process the enhanced image
                        image = Image.open(BytesIO(image_data)).convert('RGB')
                        
                        # Smart resize to target dimensions
                        image = self._smart_resize_image(image, target_width, target_height)
                        
                        # Save enhanced image
                        filename = f"enhanced_background_{hash(prompt) % 10000}.jpg"
                        filepath = os.path.join("generated_images", filename)
                        image.save(filepath, format='JPEG', quality=90, optimize=True)
                        
                        self.logger.info(f"Generated enhanced background image: {filepath}")
                        return os.path.abspath(filepath)
            
            return None
                
        except Exception as e:
            self.logger.error(f"Error generating enhanced image with Gemini: {e}")
            return None

    def _enhance_image_with_pil(self, source_img, target_width, target_height, context, company_name):
        """Enhance image using PIL for background use"""
        try:
            # Smart resize to target dimensions
            enhanced_img = self._smart_resize_image(source_img, target_width, target_height)
            
            # Apply background effects
            # 1. Slight blur for background effect
            enhanced_img = enhanced_img.filter(ImageFilter.GaussianBlur(radius=1))
            
            # 2. Reduce brightness slightly
            enhancer = ImageEnhance.Brightness(enhanced_img)
            enhanced_img = enhancer.enhance(0.8)
            
            # 3. Increase contrast for better text readability
            enhancer = ImageEnhance.Contrast(enhanced_img)
            enhanced_img = enhancer.enhance(1.1)
            
            # 4. Add subtle overlay for professional look
            overlay = Image.new('RGB', enhanced_img.size, (0, 0, 0))
            overlay.putalpha(20)  # 20% opacity
            
            # Create final background
            if enhanced_img.mode != 'RGBA':
                enhanced_img = enhanced_img.convert('RGBA')
            background = Image.alpha_composite(enhanced_img, overlay)
            background = background.convert('RGB')
            
            # Save enhanced image
            filename = f"enhanced_background_{company_name}_{hash(context) % 1000}.jpg"
            filepath = os.path.join("generated_images", filename)
            background.save(filepath, format='JPEG', quality=90, optimize=True)
            
            self.logger.info(f"Created enhanced background with PIL: {filepath}")
            return os.path.abspath(filepath)
            
        except Exception as e:
            self.logger.error(f"Error enhancing image with PIL: {e}")
            return None

    def _smart_resize_image(self, image, target_width, target_height):
        """Smart resize image to fit exact dimensions without padding, using crop and resize"""
        try:
            # Calculate aspect ratios
            image_ratio = image.width / image.height
            target_ratio = target_width / target_height
            
            # Determine if we need to crop width or height
            if image_ratio > target_ratio:
                # Image is wider than target - crop width
                new_width = int(image.height * target_ratio)
                left = (image.width - new_width) // 2
                right = left + new_width
                image = image.crop((left, 0, right, image.height))
            elif image_ratio < target_ratio:
                # Image is taller than target - crop height
                new_height = int(image.width / target_ratio)
                top = (image.height - new_height) // 2
                bottom = top + new_height
                image = image.crop((0, top, image.width, bottom))
            
            # Now resize to exact target dimensions
            image = image.resize((target_width, target_height), Image.Resampling.LANCZOS)
            
            return image
            
        except Exception as e:
            self.logger.error(f"Error in smart resize: {e}")
            raise e
