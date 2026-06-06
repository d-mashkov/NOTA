import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]
EXA_API_KEY = os.environ["EXA_API_KEY"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

EXA_API_URL = "https://api.exa.ai/search"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

EXA_NUM_RESULTS = 10
EXA_DAYS_BACK = 365
