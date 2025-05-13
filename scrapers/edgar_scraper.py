# sec_filing_scraper.py
import os
import json
import logging
import re
import sys

# Get absolute path to project root (parent of scrapers directory)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
# Add project root to Python path
sys.path.append(PROJECT_ROOT)

from edgar import set_identity, Company
from utils.sec_filings.company_mappings import CompanyMappings
from utils.sec_filings.filing_utils import save_filing, EXHIBIT_PATTERNS

# ─── Configuration ────────────────────────────────────────────────────────────

# Define paths relative to project root
STORAGE_DIR = os.path.join(PROJECT_ROOT, "sample_drive/inbox/sec_filings")
METADATA_FILE = os.path.join(PROJECT_ROOT, "sample_drive/metadata/sec_filings/tracked_companies.json")
USER_AGENT = "CortexBot/1.0 (your_email@example.com)"
VALID_FORMS = ["10-K", "8-K", "10-Q", "S-1", "20-F", "6-K"]

logging.basicConfig(level=logging.INFO)

# Register your identity with the SEC
set_identity(USER_AGENT)

def get_tracked_companies():
    """Load list of companies to track from metadata"""
    try:
        with open(METADATA_FILE, 'r') as f:
            data = json.load(f)
            return data.get('companies', [])
    except FileNotFoundError:
        logging.error(f"Tracked companies file not found: {METADATA_FILE}")
        return []
    except json.JSONDecodeError:
        logging.error(f"Invalid JSON in tracked companies file: {METADATA_FILE}")
        return []

def fetch_latest_filings(identifiers: str | list = None, forms: list = None, count: int | str = 1):
    """
    Fetch the single most recent filing for each form type for given identifiers.
    
    Args:
        identifiers: Single identifier (str) or list of identifiers (tickers/CIKs).
                    If None, loads from tracked_companies.json
        forms: List of form types to fetch. If None, uses VALID_FORMS
    """
    # Handle input flexibility
    if identifiers is None:
        identifiers = get_tracked_companies()
    elif isinstance(identifiers, str):
        identifiers = [identifiers]
    
    # Use default forms if none specified
    forms = forms or VALID_FORMS
    
    # Initialize company mappings
    mappings = CompanyMappings(USER_AGENT)
    
    # Normalize and deduplicate identifiers
    normalized_ciks = set(
        mappings.normalize_identifier(id) 
        for id in identifiers
    )
    
    for cik in normalized_ciks:
        company = Company(cik)
        display_id = mappings.get_display_id(cik)
        
        for form in forms:
            try:
                filings = company.get_filings(form=form)
                if not filings:
                    logging.info(f"No {form} filings found for {display_id}")
                    continue
                
                # Get exhibit patterns for this form type
                form_patterns = EXHIBIT_PATTERNS.get(form, [])
                
                # Process the specified number of filings
                num_filings = len(filings) if count == 'all' else min(count, len(filings))
                
                for i in range(num_filings):
                    filing = filings[i]
                    
                    # Handle attachments
                    attachments = []
                    if form_patterns:
                        try:
                            all_attachments = filing.attachments
                            
                            # Check each attachment against patterns for this form
                            for att in all_attachments:
                                att_str = str(att)
                                for pattern in form_patterns:
                                    if re.search(pattern['pattern'], att_str):
                                        try:
                                            attachments.append((pattern['name'], att.text()))
                                            logging.info(f"Found {pattern['name']}")
                                        except Exception as e:
                                            logging.warning(f"Could not get text from {pattern['name']}: {e}")
                                            
                        except Exception as e:
                            logging.warning(f"Error getting attachments: {e}")
                    
                    save_filing(
                        html_content=filing.html(),
                        text_content=filing.text(),
                        base_dir=STORAGE_DIR,
                        company_id=display_id,
                        form=form,
                        accession_number=filing.accession_number,
                        filing_date=filing.filing_date,
                        attachments=attachments if attachments else None
                    )

            except Exception as e:
                logging.error(f"Error fetching {form} for {display_id}: {e}")

if __name__ == "__main__":
    # Examples of different ways to use the function:
    
    # Single company, most recent filing
    # fetch_latest_filings("TSMWF")
    
    # All tracked companies, all forms, 10 most recent filings of each form
    fetch_latest_filings(count=10)
    # Multiple companies, all forms
    # fetch_latest_filings(["AAPL", "MSFT"])
    
    # Single company, specific forms
    # fetch_latest_filings("AAPL", forms=["10-K", "10-Q"])
    
    # Use tracked companies list
    # fetch_latest_filings()
    
    # Multiple companies, specific forms
    # fetch_latest_filings(["AAPL", "MSFT"], forms=["8-K"])