
import os
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

# Locate the backend directory
BACKEND_DIR = Path(__file__).resolve().parent.parent

# Load credentials
load_dotenv(BACKEND_DIR / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")

if not SUPABASE_URL or not SUPABASE_SECRET_KEY:
    raise RuntimeError(
        "Supabase credentials missing in .env"
    )

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_SECRET_KEY
)
