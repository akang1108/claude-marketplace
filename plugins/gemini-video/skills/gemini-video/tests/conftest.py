import sys
from unittest.mock import MagicMock

# Mock google.genai before any tests try to import gemini_video
sys.modules['google'] = MagicMock()
sys.modules['google.genai'] = MagicMock()
