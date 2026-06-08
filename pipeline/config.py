import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
EXA_API_KEY = os.environ.get("EXA_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# YouTube Data API v3 (console.cloud.google.com)
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")

# Telegram API (my.telegram.org → API development tools)
TELEGRAM_API_ID = os.environ.get("TELEGRAM_API_ID", "")
TELEGRAM_API_HASH = os.environ.get("TELEGRAM_API_HASH", "")

EXA_API_URL = "https://api.exa.ai/search"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

EXA_NUM_RESULTS = 15
EXA_DAYS_BACK = 365
