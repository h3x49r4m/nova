"""Pytest configuration for iflow skills tests."""

import sys
from pathlib import Path

# Add parent directory to Python path for imports
skills_dir = Path(__file__).parent.parent
sys.path.insert(0, str(skills_dir))