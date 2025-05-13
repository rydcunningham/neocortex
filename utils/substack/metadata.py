import json
import logging
from .config import METADATA_FILE, ESSAYS_METADATA_FILE

def get_tracked_substacks():
    """Load list of Substacks to track from metadata"""
    try:
        with open(METADATA_FILE, 'r') as f:
            data = json.load(f)
            return data.get('substacks', [])
    except FileNotFoundError:
        logging.error(f"Tracked Substacks file not found: {METADATA_FILE}")
        return []
    except json.JSONDecodeError:
        logging.error(f"Invalid JSON in tracked Substacks file: {METADATA_FILE}")
        return []

# Add other metadata handling functions here
