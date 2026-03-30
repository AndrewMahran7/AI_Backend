import sys
sys.path.insert(0, r"c:\Users\andre\Desktop\100xDevs\ai_backend")

from app.core.config import get_settings

s = get_settings()
print("DATABASE_URL:", repr(s.DATABASE_URL))
print("GEMINI_KEY present:", bool(s.GEMINI_API_KEY))
