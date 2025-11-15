"""
Color Manager for PPT Automation
Handles placeholder color configuration and theme-based styling
"""
import json
import os
import re
from utils.logger import get_logger
from config import LOG_LEVEL, LOG_FILE


class ColorManager:
    def __init__(self):
        self.logger = get_logger(__name__, LOG_LEVEL, LOG_FILE)
        self.color_config = self._load_color_config()
        self.color_usage_log = []  # Track color usage for monitoring
        self.scope_config = self._load_scope_config()
        self.auto_contrast_config = self._load_auto_contrast_config()
    
    def _is_color_light(self, hex_color):
        """
        Determine if a color is light or dark
        Returns True if light (brightness > 0.5), False if dark
        """
        try:
            # Remove # if present
            hex_color = hex_color.lstrip('#')
            
            # Convert hex to RGB
            if len(hex_color) == 6:
                r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
            elif len(hex_color) == 3:
                r, g, b = int(hex_color[0]*2, 16), int(hex_color[1]*2, 16), int(hex_color[2]*2, 16)
            else:
                return False  # Invalid hex color
            
            # Calculate brightness using luminance formula
            # Using relative luminance formula: 0.299*R + 0.587*G + 0.114*B
            brightness = (0.299 * r + 0.587 * g + 0.114 * b) / 255
            
            return brightness > 0.5
            
        except Exception as e:
            self.logger.warning(f"Error calculating color brightness for {hex_color}: {e}")
            return False  # Assume dark if can't determine
    
    def _load_color_config(self):
        """Load color configuration from separated files"""
        try:
            # Load theme-based colors from separate file
            theme_based_rules = {}
            try:
                theme_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'colors_theme_based.json')
                if os.path.exists(theme_path):
                    with open(theme_path, 'r', encoding='utf-8') as f:
                        theme_data = json.load(f)
                        theme_based_rules = theme_data.get('placeholders', {})
                        self.logger.info(f"Loaded {len(theme_based_rules)} theme-based color rules")
            except Exception as e:
                self.logger.warning(f"Failed to load theme-based colors: {e}")
            
            # Create config structure compatible with existing code
            return {
                'placeholder_configurations': {},
                'color_schemes': {
                    'theme_based': {
                        'enabled': True,
                        'rules': theme_based_rules
                    },
                    'custom_colors': {
                        'enabled': False,
                        'colors': {}
                    },
                    'special_text_elements': {
                        'enabled': False,
                        'rules': {}
                    }
                },
                'color_settings': {
                    'default_theme': {
                        'primary_color': '#2563eb',
                        'secondary_color': '#1e40af',
                        'accent_color': '#3b82f6',
                        'text_color': '#1f2937',
                        'background_color': '#ffffff'
                    }
                }
            }
        except Exception as e:
            self.logger.error(f"Failed to load color config: {e}")
            raise e
    
    def _load_scope_config(self):
        """Load scope placeholder configuration from separate file"""
        try:
            config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'scope_placeholders_config.json')
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            self.logger.warning(f"Failed to load scope config: {e}")
            return {}

    def _load_auto_contrast_config(self):
        """Load auto-contrast placeholder configuration and logic"""
        try:
            config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'colors_auto_contrast.json')
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data or {}
            return {}
        except Exception as e:
            self.logger.warning(f"Failed to load auto-contrast config: {e}")
            return {}
    
    
    def _log_color_usage(self, placeholder_name, color, source, theme_color_key=None, element_id=None):
        """Log color usage for monitoring"""
        import time
        usage_entry = {
            'timestamp': time.time(),
            'placeholder': placeholder_name,
            'color': color,
            'source': source,
            'theme_color_key': theme_color_key,
            'element_id': element_id
        }
        self.color_usage_log.append(usage_entry)
        
        # Log to file with detailed information
        self.logger.info(f"🎨 COLOR USAGE: {placeholder_name} -> {color} (source: {source})")
        if theme_color_key:
            self.logger.debug(f"   Theme key: {theme_color_key}")
        if element_id:
            self.logger.debug(f"   Element ID: {element_id}")

    def get_placeholder_color(self, placeholder_name, theme=None, element_id=None):
        """Get color configuration for a specific placeholder
        
        Args:
            placeholder_name: Placeholder name (may include {{}} braces or not)
            theme: Theme dict with primary_color, secondary_color, etc.
            element_id: Element ID for logging purposes
            
        Returns:
            dict with 'color', 'bold', 'italic', 'source' keys
        """
        try:
            # Clean placeholder name (remove braces if present)
            # Placeholders come as "{{what_is_an}}" but config keys are "what_is_an"
            clean_name = placeholder_name.replace('{{', '').replace('}}', '').strip()
            if clean_name == 'effort_estimation_?':
                clean_name = 'effort_estimation_q'
            
            # PRIORITY 0: Apply explicit auto-contrast config if present
            try:
                ac = self.auto_contrast_config if isinstance(self.auto_contrast_config, dict) else {}
                ac_enabled = ac.get('enabled', False)
                ac_placeholders = (ac.get('placeholders') or {}) if isinstance(ac.get('placeholders'), dict) else {}
                ac_logic = (ac.get('logic') or {}) if isinstance(ac.get('logic'), dict) else {}
            except Exception:
                ac_enabled, ac_placeholders, ac_logic = False, {}, {}

            if ac_enabled and clean_name in ac_placeholders and theme:
                formatting = ac_placeholders.get(clean_name, {}) if isinstance(ac_placeholders.get(clean_name), dict) else {}
                # Use accent_color directly from user input instead of auto-calculating
                text_color = theme.get('accent_color', '#3b82f6')
                theme_color_key = 'accent_color'
                self._log_color_usage(placeholder_name, text_color, 'user_accent_color', theme_color_key, element_id)
                return {
                    'color': text_color,
                    'bold': formatting.get('bold', False),
                    'italic': formatting.get('italic', False),
                    'source': 'user_accent_color'
                }

            # Special handling for scope-related placeholders
            # These use accent color from user input
            # NOTE: budget and our are NOT scope placeholders - they use theme-based colors
            # NOTE: proposalName is NOT a scope placeholder - it uses white color like projectName and companyName
            scope_placeholders = ['scope_desc', 'comprehensive_design_job', 'scope_of_project', 
                                   'project_goals', 'design', 'inspiration', 'team', 'composition', 'u0022']
            
            # Log if this is a scope placeholder
            if clean_name in scope_placeholders:
                self.logger.info(f"🎯 Detected scope placeholder: {clean_name}")
                self.logger.info(f"🔍 Theme available: {theme is not None}")
                if theme:
                    self.logger.info(f"🔍 Theme keys: {list(theme.keys())}")
                    self.logger.info(f"🔍 Primary color in theme: {theme.get('primary_color', 'NOT FOUND')}")
            
            if clean_name in scope_placeholders and theme:
                # Use accent_color directly from user input instead of auto-calculating
                accent_color = theme.get('accent_color', '#3b82f6')
                self.logger.info(f"🎨 Using accent color for {clean_name}...")
                self.logger.info(f"   Accent color from user: {accent_color}")
                
                color = accent_color
                source = 'user_accent_color'
                self.logger.info(f"✅ Final color for {clean_name}: {color}")
                self._log_color_usage(placeholder_name, color, source, 'accent_color', element_id)
                
                # Get formatting settings from scope_placeholders_config.json
                formatting = self.scope_config.get(clean_name, {})
                self.logger.info(f"   Formatting: bold={formatting.get('bold', False)}, italic={formatting.get('italic', False)}")
                
                return {
                    'color': color,
                    'bold': formatting.get('bold', False),
                    'italic': formatting.get('italic', False),
                    'source': source
                }
            
            # Check for custom white color placeholders (projectName, companyName, proposalName)
            white_color_placeholders = ['projectName', 'companyName', 'proposalName']
            if clean_name in white_color_placeholders:
                self.logger.info(f"✅ Using white color for {clean_name}")
                return {
                    'color': '#FFFFFF',
                    'bold': True,  # All three (projectName, companyName, proposalName) should be bold
                    'italic': False,
                    'source': 'custom_white'
                }
            
            # PRIORITY 1: Check theme-based colors FIRST (highest priority for theme-based placeholders)
            # This ensures what_is_an, days, budget, our, project_timeline use their theme-based colors
            if self.color_config['color_schemes']['theme_based']['enabled']:
                theme_rules = self.color_config['color_schemes']['theme_based']['rules']
                rule = None
                
                # First try exact match
                if clean_name in theme_rules:
                    rule = theme_rules[clean_name]
                    self.logger.debug(f"Found exact match for {clean_name} in theme_rules")
                else:
                    # Build lowercase lookup map (rebuild it each time to catch config updates)
                    lower_key = clean_name.lower()
                    try:
                        # Rebuild cache to ensure we have latest config
                        self._theme_rules_lower = {k.lower(): v for k, v in theme_rules.items()}
                        rule = self._theme_rules_lower.get(lower_key)
                        if rule:
                            self.logger.debug(f"Found case-insensitive match for {clean_name} (as {lower_key}) in theme_rules")
                    except Exception as e:
                        self.logger.warning(f"Error building lowercase lookup for {clean_name}: {e}")
                        rule = None
                
                if rule is not None:
                    # Get color from theme or use fallback
                    theme_color_key = rule.get('theme_color')
                    self.logger.debug(f"Rule found for {clean_name}: theme_color_key={theme_color_key}, theme_available={theme is not None}")
                    
                    if theme and theme_color_key:
                        # Get color from theme using the specified key (e.g., 'primary_color', 'secondary_color')
                        color = theme.get(theme_color_key, rule['fallback_color'])
                        source = 'theme_based'
                        # Verify that we got the correct color for theme-based placeholders
                        if clean_name in ['what_is_an', 'days', 'budget', 'our'] and theme_color_key != 'primary_color':
                            self.logger.warning(f"⚠️ {clean_name} should use primary_color but got {theme_color_key} -> {color}")
                        elif clean_name in ['project_timeline', 'effort_estimation_q'] and theme_color_key != 'secondary_color':
                            self.logger.warning(f"⚠️ {clean_name} should use secondary_color but got {theme_color_key} -> {color}")
                        self.logger.info(f"✅ Using theme color for {clean_name}: {theme_color_key} -> {color}")
                    else:
                        # Use fallback color (which should be primary/secondary color fallback)
                        color = rule['fallback_color']
                        theme_color_key = None
                        source = 'fallback'
                        # For what_is_an, days, budget, our - verify fallback is primary_color fallback
                        if clean_name in ['what_is_an', 'days', 'budget', 'our']:
                            expected_fallback = '#2563eb'  # Default primary blue
                            if color != expected_fallback:
                                self.logger.warning(f"⚠️ {clean_name} fallback color {color} doesn't match expected primary fallback {expected_fallback}")
                        elif clean_name == 'project_timeline':
                            expected_fallback = '#1e40af'  # Default secondary blue
                            if color != expected_fallback:
                                self.logger.warning(f"⚠️ {clean_name} fallback color {color} doesn't match expected secondary fallback {expected_fallback}")
                        if not theme:
                            self.logger.warning(f"⚠️ No theme available for {clean_name}, using fallback color: {color}")
                        else:
                            self.logger.info(f"Using fallback color for {clean_name}: {color}")
                    
                    self._log_color_usage(placeholder_name, color, source, theme_color_key, element_id)
                    return {
                        'color': color,
                        'bold': rule.get('bold', False),
                        'italic': rule.get('italic', False),
                        'source': source
                    }
                else:
                    # self.logger.warning(f"⚠️ No theme rule found for {clean_name} in {list(theme_rules.keys())}")
                    pass
            
            # PRIORITY 2: Check if placeholder has individual configuration (case-insensitive)
            # IMPORTANT: Skip placeholder_configurations for theme-based placeholders to avoid overrides
            # Theme-based placeholders (what_is_an, days, budget, our, project_timeline, effort_estimation_q) 
            # should ONLY use theme-based colors from config files, never from placeholder_configurations
            theme_based_placeholders = ['what_is_an', 'days', 'budget', 'our', 'project_timeline', 'effort_estimation_q']
            skip_individual_config = clean_name in theme_based_placeholders
            
            if not skip_individual_config and 'placeholder_configurations' in self.color_config:
                placeholder_configs = self.color_config['placeholder_configurations']
                config = None
                if clean_name in placeholder_configs:
                    config = placeholder_configs[clean_name]
                else:
                    # Try lowercase key
                    lower_key = clean_name.lower()
                    if lower_key in placeholder_configs:
                        config = placeholder_configs[lower_key]
                if config is not None:
                    color_source = config.get('color_source', 'theme_based')
                    
                    # Get color based on source
                    if color_source == 'auto_contrast' and theme:
                        # Use accent_color directly from user input instead of auto-calculating
                        color = theme.get('accent_color', '#3b82f6')
                        source = 'user_accent_color'
                        theme_color_key = 'accent_color'
                        self.logger.info(f"🎨 Using accent color for {clean_name}: {color}")
                    elif color_source == 'custom':
                        color = config.get('custom_color', config.get('fallback_color', '#1f2937'))
                        source = 'custom'
                        theme_color_key = None
                    elif color_source == 'theme_based' and theme:
                        theme_color_key = config.get('theme_color', 'text_color')
                        color = theme.get(theme_color_key, config.get('fallback_color', '#1f2937'))
                        source = 'theme_based'
                    else:
                        color = config.get('fallback_color', '#1f2937')
                        source = 'fallback'
                        theme_color_key = None
                    
                    # Log color usage
                    self._log_color_usage(placeholder_name, color, source, theme_color_key if 'theme_color_key' in locals() else None, element_id)
                    
                    return {
                        'color': color,
                        'bold': config.get('bold', False),
                        'italic': config.get('italic', False),
                        'source': source
                    }
            
            # PRIORITY 3: Fallback to old system for backward compatibility
            # IMPORTANT: Skip for theme-based placeholders - they should never reach here if theme rule exists
            if not skip_individual_config:
                # Check custom colors first
                if self.color_config['color_schemes']['custom_colors']['enabled']:
                    custom_colors = self.color_config['color_schemes']['custom_colors']['colors']
                    if clean_name in custom_colors:
                        color = custom_colors[clean_name]
                        self._log_color_usage(placeholder_name, color, 'custom_legacy', None, element_id)
                        return {
                            'color': color,
                            'bold': False,
                            'italic': False,
                            'source': 'custom'
                        }
            
            # Default fallback - CRITICAL: Theme-based placeholders should NOT reach here
            # If they do, it means the theme rule wasn't found - log an error
            if clean_name in theme_based_placeholders:
                self.logger.error(f"🚨 CRITICAL: {clean_name} is a theme-based placeholder but no theme rule found! This should not happen. Check colors_theme_based.json")
                # Force primary color for what_is_an, days, budget, our as emergency fallback
                if clean_name in ['what_is_an', 'days', 'budget', 'our']:
                    emergency_color = theme.get('primary_color', '#2563eb') if theme else '#2563eb'
                    self.logger.warning(f"⚠️ Using emergency primary color fallback: {emergency_color}")
                    self._log_color_usage(placeholder_name, emergency_color, 'emergency_primary', 'primary_color', element_id)
                    return {
                        'color': emergency_color,
                        'bold': True,
                        'italic': False,
                        'source': 'emergency_primary'
                    }
                elif clean_name in ['project_timeline', 'effort_estimation_q']:
                    emergency_color = theme.get('secondary_color', '#1e40af') if theme else '#1e40af'
                    self.logger.warning(f"⚠️ Using emergency secondary color fallback: {emergency_color}")
                    self._log_color_usage(placeholder_name, emergency_color, 'emergency_secondary', 'secondary_color', element_id)
                    return {
                        'color': emergency_color,
                        'bold': True,
                        'italic': False,
                        'source': 'emergency_secondary'
                    }
            
            # Default fallback for non-theme placeholders
            color = '#1f2937'
            self._log_color_usage(placeholder_name, color, 'default', None, element_id)
            return {
                'color': color,
                'bold': False,
                'italic': False,
                'source': 'default'
            }
            
        except Exception as e:
            self.logger.warning(f"Error getting color for {placeholder_name}: {e}")
            # For theme-based placeholders, use emergency fallback even on error
            clean_name = placeholder_name.replace('{{', '').replace('}}', '').strip()
            if clean_name == 'effort_estimation_?':
                clean_name = 'effort_estimation_q'
            theme_based_placeholders = ['what_is_an', 'days', 'budget', 'our', 'project_timeline', 'effort_estimation_q']
            
            if clean_name in ['what_is_an', 'days', 'budget', 'our']:
                # Emergency primary color fallback even on error
                emergency_color = theme.get('primary_color', '#2563eb') if theme else '#2563eb'
                self.logger.warning(f"⚠️ Error occurred for {clean_name}, using emergency primary: {emergency_color}")
                return {
                    'color': emergency_color,
                    'bold': True,
                    'italic': False,
                    'source': 'error_emergency_primary'
                }
            elif clean_name in ['project_timeline', 'effort_estimation_q']:
                # Emergency secondary color fallback even on error
                emergency_color = theme.get('secondary_color', '#1e40af') if theme else '#1e40af'
                self.logger.warning(f"⚠️ Error occurred for {clean_name}, using emergency secondary: {emergency_color}")
                return {
                    'color': emergency_color,
                    'bold': True,
                    'italic': False,
                    'source': 'error_emergency_secondary'
                }
            
            # Default error fallback for non-theme placeholders
            return {
                'color': '#1f2937',
                'bold': False,
                'italic': False,
                'source': 'error'
            }
    
    def get_special_text_color(self, text_content, theme=None):
        """Determine if a special text color is required for given text content."""
        # If special coloring is required for this text, implement logic here; otherwise, return None.
        return None
    
    def create_text_styling_map(self, placeholders, theme=None):
        """Create comprehensive styling map for all placeholders"""
        styling_map = {}
        
        try:
            # Placeholders that must be bold regardless of theme color
            force_bold = {
                # Properties
                'property1', 'property2', 'property3',

                #breakup
                'breakup_1', 'breakup_2', 'breakup_3', 'breakup_4', 'breakup_5', 'breakup_6',

                #b1, b2, b3, b4, b5, b6
                'b1', 'b2', 'b3', 'b4', 'b5', 'b6',

                #our, process
                'our', 'process',

                #p_b, d_b, d_v, d_p
                'p_b', 'd_b', 'd_v', 'd_p',

                # Main headings
                'Heading_1', 'Heading_2', 'Heading_3', 'Heading_4', 'Heading_5', 'Heading_6',
                # Side headings (side_Heading_X uses primary color, side_Head_X uses secondary color)
                'side_Heading_1','side_Heading_2','side_Heading_3','side_Heading_4',
                'side_Heading_5','side_Heading_6','side_Heading_7','side_Heading_8',
                'side_Heading_9','side_Heading_10','side_Heading_11','side_Heading_12',
                'side_Heading_13','side_Heading_14','side_Heading_15',
                'side_Head_1','side_Head_2','side_Head_3','side_Head_4',
                'side_Head_5','side_Head_6','side_Head_7','side_Head_8',
                'side_Head_9','side_Head_10','side_Head_11','side_Head_12',
                'side_Head_13','side_Head_14','side_Head_15',
                # Common labels/titles requested to be bold
                'team','composition','design','inspiration',
                'what_is_an','effort_estimation_?','effort_estimation_q','days',
                'project_timeline', 'target_audience', 'diverse_range_of_users',
            }
            # Also support potential alternative casing/spelling
            force_bold_alt = {n.lower() for n in force_bold}

            for placeholder in placeholders:
                element_id = placeholder['element_id']
                placeholder_name = placeholder['placeholder']
                clean_name = (placeholder_name or '').replace('{{','').replace('}}','')
                
                # Get color configuration
                color_config = self.get_placeholder_color(placeholder_name, theme, element_id)
                
                # Respect existing bold in config but force bold for specific placeholders
                is_force_bold = clean_name in force_bold or clean_name.lower() in force_bold_alt or clean_name.startswith('side_Heading_') or clean_name.startswith('side_Head_')
                styling_map[element_id] = {
                    'color': color_config['color'],
                    'bold': True if (color_config['bold'] or is_force_bold) else False,
                    'italic': color_config.get('italic', False)
                }
                
                # Extra logging for what_is_an to verify color
                if clean_name == 'what_is_an':
                    self.logger.info(f"📋 STYLING MAP: what_is_an (element_id={element_id}) -> color={color_config['color']}, source={color_config.get('source', 'unknown')}")
                    # Verify it's using primary color from theme
                    if theme:
                        expected_primary = theme.get('primary_color', '#2563eb')
                        if color_config['color'] != expected_primary:
                            self.logger.warning(f"⚠️ what_is_an color mismatch! Expected primary {expected_primary}, got {color_config['color']}")
                
                # Log all styling for debugging
                self.logger.debug(f"Styled {placeholder_name} -> color={color_config['color']}, bold={styling_map[element_id]['bold']}, source={color_config['source']}")
            
            return styling_map
            
        except Exception as e:
            self.logger.error(f"Error creating styling map: {e}")
            return {}
    
    def update_color_scheme(self, scheme_name, enabled=True):
        """Enable or disable a specific color scheme"""
        try:
            if scheme_name in self.color_config['color_schemes']:
                self.color_config['color_schemes'][scheme_name]['enabled'] = enabled
                self.logger.info(f"Updated {scheme_name} scheme: enabled={enabled}")
                return True
            else:
                self.logger.warning(f"Color scheme '{scheme_name}' not found")
                return False
        except Exception as e:
            self.logger.error(f"Error updating color scheme: {e}")
            return False
    
    def set_custom_color(self, placeholder_name, color):
        """Set a custom color for a specific placeholder"""
        try:
            if not self.color_config['color_schemes']['custom_colors']['enabled']:
                self.color_config['color_schemes']['custom_colors']['enabled'] = True
            
            self.color_config['color_schemes']['custom_colors']['colors'][placeholder_name] = color
            self.logger.info(f"Set custom color for {placeholder_name}: {color}")
            return True
        except Exception as e:
            self.logger.error(f"Error setting custom color: {e}")
            return False
    
    def get_available_schemes(self):
        """Get list of available color schemes"""
        return list(self.color_config['color_schemes'].keys())
    
    def get_active_schemes(self):
        """Get list of currently enabled color schemes"""
        active = []
        for scheme_name, scheme_config in self.color_config['color_schemes'].items():
            if scheme_config.get('enabled', False):
                active.append(scheme_name)
        return active
    
    def reload_config(self):
        """Reload color configuration from file"""
        self.color_config = self._load_color_config()
        # Clear the cache so it rebuilds with new config
        if hasattr(self, '_theme_rules_lower'):
            delattr(self, '_theme_rules_lower')
        self.logger.info("Color configuration reloaded")
    
    def _save_config(self):
        """Save color configuration to file"""
        # Disabled: Using separated config files now
        self.logger.debug("Color configuration changes are managed in separated config files")
    
    def set_placeholder_color_source(self, placeholder_name, color_source, custom_color=None):
        """Set color source for a specific placeholder"""
        try:
            if 'placeholder_configurations' not in self.color_config:
                self.color_config['placeholder_configurations'] = {}
            
            if placeholder_name not in self.color_config['placeholder_configurations']:
                # Create default configuration
                self.color_config['placeholder_configurations'][placeholder_name] = {
                    'color_source': 'theme_based',
                    'theme_color': 'text_color',
                    'custom_color': '#1f2937',
                    'fallback_color': '#1f2937',
                    'bold': False,
                    'italic': False,
                    'description': f'Configuration for {placeholder_name}'
                }
            
            config = self.color_config['placeholder_configurations'][placeholder_name]
            config['color_source'] = color_source
            
            if color_source == 'custom' and custom_color:
                config['custom_color'] = custom_color
            
            self.logger.info(f"Set {placeholder_name} to use {color_source} colors")
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting color source for {placeholder_name}: {e}")
            return False
    
    def set_placeholder_custom_color(self, placeholder_name, color):
        """Set custom color for a specific placeholder"""
        try:
            if 'placeholder_configurations' not in self.color_config:
                self.color_config['placeholder_configurations'] = {}
            
            if placeholder_name not in self.color_config['placeholder_configurations']:
                # Create default configuration
                self.color_config['placeholder_configurations'][placeholder_name] = {
                    'color_source': 'custom',
                    'theme_color': 'text_color',
                    'custom_color': color,
                    'fallback_color': color,
                    'bold': False,
                    'italic': False,
                    'description': f'Configuration for {placeholder_name}'
                }
            else:
                self.color_config['placeholder_configurations'][placeholder_name]['custom_color'] = color
                self.color_config['placeholder_configurations'][placeholder_name]['color_source'] = 'custom'
            
            # Save to file
            self._save_config()
            
            self.logger.info(f"Set custom color for {placeholder_name}: {color}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting custom color for {placeholder_name}: {e}")
            return False
    
    def set_placeholder_theme_color(self, placeholder_name, theme_color):
        """Set theme color for a specific placeholder"""
        try:
            if 'placeholder_configurations' not in self.color_config:
                self.color_config['placeholder_configurations'] = {}
            
            if placeholder_name not in self.color_config['placeholder_configurations']:
                # Create default configuration
                self.color_config['placeholder_configurations'][placeholder_name] = {
                    'color_source': 'theme_based',
                    'theme_color': theme_color,
                    'custom_color': '#1f2937',
                    'fallback_color': '#1f2937',
                    'bold': False,
                    'italic': False,
                    'description': f'Configuration for {placeholder_name}'
                }
            else:
                self.color_config['placeholder_configurations'][placeholder_name]['theme_color'] = theme_color
                self.color_config['placeholder_configurations'][placeholder_name]['color_source'] = 'theme_based'
            
            # Save to file
            self._save_config()
            
            self.logger.info(f"Set {placeholder_name} to use theme color: {theme_color}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting theme color for {placeholder_name}: {e}")
            return False
    
    def get_placeholder_config(self, placeholder_name):
        """Get configuration for a specific placeholder"""
        try:
            if 'placeholder_configurations' in self.color_config:
                return self.color_config['placeholder_configurations'].get(placeholder_name, None)
            return None
        except Exception as e:
            self.logger.error(f"Error getting config for {placeholder_name}: {e}")
            return None
    
    def list_placeholder_configs(self):
        """List all placeholder configurations"""
        try:
            if 'placeholder_configurations' in self.color_config:
                return list(self.color_config['placeholder_configurations'].keys())
            return []
        except Exception as e:
            self.logger.error(f"Error listing placeholder configs: {e}")
            return []
    
    def get_color_usage_report(self):
        """Get a comprehensive report of color usage"""
        try:
            if not self.color_usage_log:
                return "No color usage recorded yet."
            
            # Group by placeholder
            placeholder_usage = {}
            for entry in self.color_usage_log:
                placeholder = entry['placeholder']
                if placeholder not in placeholder_usage:
                    placeholder_usage[placeholder] = []
                placeholder_usage[placeholder].append(entry)
            
            # Generate report
            report = ["🎨 COLOR USAGE REPORT", "=" * 50]
            
            for placeholder, entries in placeholder_usage.items():
                latest_entry = entries[-1]  # Get the most recent usage
                report.append(f"\n📋 {placeholder}:")
                report.append(f"   Color: {latest_entry['color']}")
                report.append(f"   Source: {latest_entry['source']}")
                if latest_entry.get('theme_color_key'):
                    report.append(f"   Theme Key: {latest_entry['theme_color_key']}")
                if latest_entry.get('element_id'):
                    report.append(f"   Element ID: {latest_entry['element_id']}")
                report.append(f"   Usage Count: {len(entries)}")
            
            # Summary statistics
            total_usage = len(self.color_usage_log)
            unique_placeholders = len(placeholder_usage)
            unique_colors = len(set(entry['color'] for entry in self.color_usage_log))
            
            report.append(f"\n📊 SUMMARY:")
            report.append(f"   Total Color Applications: {total_usage}")
            report.append(f"   Unique Placeholders: {unique_placeholders}")
            report.append(f"   Unique Colors Used: {unique_colors}")
            
            return "\n".join(report)
            
        except Exception as e:
            self.logger.error(f"Error generating color usage report: {e}")
            return f"Error generating report: {e}"
    
    def get_color_usage_by_source(self):
        """Get color usage grouped by source type"""
        try:
            source_usage = {}
            for entry in self.color_usage_log:
                source = entry['source']
                if source not in source_usage:
                    source_usage[source] = []
                source_usage[source].append(entry)
            
            report = ["🎨 COLOR USAGE BY SOURCE", "=" * 40]
            for source, entries in source_usage.items():
                report.append(f"\n📌 {source.upper()}:")
                for entry in entries:
                    report.append(f"   {entry['placeholder']} -> {entry['color']}")
            
            return "\n".join(report)
            
        except Exception as e:
            self.logger.error(f"Error generating source report: {e}")
            return f"Error generating source report: {e}"
    
    def clear_color_usage_log(self):
        """Clear the color usage log"""
        self.color_usage_log.clear()
        self.logger.info("Color usage log cleared")
    
    def export_color_usage_log(self, filename=None):
        """Export color usage log to JSON file"""
        try:
            import json
            from datetime import datetime
            
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"color_usage_log_{timestamp}.json"
            
            export_data = {
                'export_timestamp': datetime.now().isoformat(),
                'total_entries': len(self.color_usage_log),
                'color_usage': self.color_usage_log
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Color usage log exported to: {filename}")
            return filename
            
        except Exception as e:
            self.logger.error(f"Error exporting color usage log: {e}")
            return None


# Global instance for easy access
color_manager = ColorManager()
