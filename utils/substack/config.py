# utils/substack/config.py
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Get absolute path to project root (parent of utils directory)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(PROJECT_ROOT)

# Load environment variables
load_dotenv()

# Storage paths
STORAGE_ROOT = os.path.join(PROJECT_ROOT, "sample_drive")
BASE_MD_DIR = os.path.join(STORAGE_ROOT, "inbox/substacks")
BASE_HTML_DIR = os.path.join(STORAGE_ROOT, "inbox/substacks")
JSON_DATA_DIR = os.path.join(STORAGE_ROOT, "metadata/substacks")
METADATA_FILE = os.path.join(JSON_DATA_DIR, "tracked_substacks.json")
ESSAYS_METADATA_FILE = os.path.join(JSON_DATA_DIR, "essays_metadata.json")

# Credentials
EMAIL = os.getenv('SUBSTACK_EMAIL')
PASSWORD = os.getenv('SUBSTACK_PASSWORD')

# Scraping settings
USE_PREMIUM = False
NUM_POSTS_TO_SCRAPE = 0
DEFAULT_CHROMIUM_PATH = "/Applications/Chromium.app/Contents/MacOS/Chromium"

# Batch processing settings
BATCH_SIZE = 5
MIN_BATCH_DELAY = 7
MAX_BATCH_DELAY = 10
RETRY_ATTEMPTS = 3
RETRY_DELAY = 60
REQUEST_DELAY = 2