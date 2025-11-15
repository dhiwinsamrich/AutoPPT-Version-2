"""
PPT Automation Core Module
"""
from .generator import ContentGenerator
from .slides_client import SlidesClient
from .automation import PPTAutomation

__all__ = ['ContentGenerator', 'SlidesClient', 'PPTAutomation']
