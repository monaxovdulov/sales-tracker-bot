"""
Configuration module for Sales Tracker Bot
Loads environment variables and provides typed constants
"""

import os
from typing import List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot configuration
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is required in environment variables")

# Admin configuration
ADMIN_IDS_STR = os.getenv("ADMIN_IDS", "")
ADMIN_IDS: List[int] = []
if ADMIN_IDS_STR:
    try:
        ADMIN_IDS = [int(id.strip()) for id in ADMIN_IDS_STR.split(",")]
    except ValueError:
        raise RuntimeError("ADMIN_IDS must be comma-separated integers")

# Google Sheets configuration
SPREADSHEET_ID: str = os.getenv("SPREADSHEET_ID", "")
if not SPREADSHEET_ID:
    raise RuntimeError("SPREADSHEET_ID is required in environment variables")

GSPREAD_CREDENTIALS: str = os.getenv("GSPREAD_CREDENTIALS", "credentials.json")

# Bot settings
REPLY_TIMEOUT: int = int(os.getenv("REPLY_TIMEOUT", "10")) 