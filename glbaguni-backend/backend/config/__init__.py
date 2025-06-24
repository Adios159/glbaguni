"""
설정 관리 패키지
"""

# Import from the main config.py file to maintain backward compatibility
import sys
import os

# Add parent directory to path to import from config.py
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

try:
    from config import settings
except ImportError:
    # Fallback to the new settings structure
    from .settings import Settings, get_settings
    settings = get_settings()

# Also make the new structure available
from .settings import Settings, get_settings

__all__ = ["Settings", "get_settings", "settings"]
