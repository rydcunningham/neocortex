# utils/sec_filings/company_mappings.py
import os
import json
import sys
import requests
import logging
from datetime import datetime, timedelta

# Get absolute path to project root (parent of scrapers directory)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
# Add project root to Python path
sys.path.append(PROJECT_ROOT)

class CompanyMappings:
    SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
    # Define paths relative to project root
    CACHE_FILE = os.path.join(PROJECT_ROOT, "sample_drive/utils/sec_filings/data/company_tickers.json")
    CACHE_MAX_AGE_DAYS = 7

    def __init__(self, user_agent):
        self.user_agent = user_agent
        self.ticker_to_cik = {}
        self.cik_to_ticker = {}
        self._load_mappings()

    def _load_mappings(self):
        """Load mappings from cache or SEC website"""
        should_refresh = True
        
        # Check if cache exists and is recent
        if os.path.exists(self.CACHE_FILE):
            file_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(self.CACHE_FILE))
            should_refresh = file_age > timedelta(days=self.CACHE_MAX_AGE_DAYS)

        if should_refresh:
            self._refresh_cache()
        
        # Load from cache
        with open(self.CACHE_FILE, 'r') as f:
            data = json.load(f)
            
        for entry in data.values():
            cik_str = str(entry['cik_str']).zfill(10)
            ticker = entry['ticker']
            self.ticker_to_cik[ticker] = cik_str
            self.cik_to_ticker[cik_str] = ticker

    def _refresh_cache(self):
        """Download fresh data from SEC"""
        try:
            os.makedirs(os.path.dirname(self.CACHE_FILE), exist_ok=True)
            headers = {'User-Agent': self.user_agent}
            response = requests.get(self.SEC_TICKERS_URL, headers=headers)
            response.raise_for_status()
            
            with open(self.CACHE_FILE, 'w') as f:
                json.dump(response.json(), f, indent=2)
                
        except Exception as e:
            logging.error(f"Error refreshing SEC mappings: {e}")
            # If refresh fails and cache exists, we'll use the old cache
            if not os.path.exists(self.CACHE_FILE):
                raise

    def normalize_identifier(self, identifier: str) -> str:
        """Convert any identifier (ticker or CIK) to normalized CIK"""
        if identifier.isdigit():
            identifier = identifier.zfill(10)
            if identifier in self.cik_to_ticker:
                return identifier
        elif identifier in self.ticker_to_cik:
            return self.ticker_to_cik[identifier]
        return identifier

    def get_display_id(self, cik: str) -> str:
        """Get display identifier (prefer ticker over CIK)"""
        return self.cik_to_ticker.get(cik, cik)
