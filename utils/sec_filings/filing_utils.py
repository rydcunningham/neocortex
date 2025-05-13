# utils/sec_filings/filing_utils.py
import re
import os
import logging

# Exhibit patterns for different filing types
EXHIBIT_PATTERNS = {
    "8-K": [
        {"pattern": r"EX-99\.1", "name": "ex991_earnings"},
        {"pattern": r"EX-99\.2", "name": "ex992_slides"}
    ],
    "6-K": [
        {"pattern": r"EX-99\.1", "name": "ex991_earnings"},
        {"pattern": r"EX-99\.2", "name": "ex992_slides"}
    ],
    "20-F": [
        {"pattern": r"EX-8\.1", "name": "ex81_subsidiaries"}
    ],
    "10-K": [
        {"pattern": r"EX-22\.1", "name": "ex221_subsidiaries"}
    ]
}

def save_filing(html_content, text_content, base_dir, company_id, form, accession_number, filing_date, attachments=None):
    """
    Save filing HTML and text content to appropriate location, along with any attachments
    
    Args:
        html_content: HTML content of the main filing
        text_content: Text content of the main filing
        base_dir: Base directory for storage
        company_id: Company identifier (ticker or CIK)
        form: Form type (10-K, 8-K, etc)
        accession_number: SEC accession number
        filing_date: Filing date (datetime object)
        attachments: List of (exhibit_name, content) tuples for attachments
    """
    # Format date as YYYYMMDD
    date_str = filing_date.strftime('%Y%m%d')
    
    # Simple filename format: identifier-date-form
    base_filename = f"{company_id.lower()}-{date_str}-{form.lower()}"
    
    out_dir = os.path.join(base_dir, company_id.upper(), form)
    os.makedirs(out_dir, exist_ok=True)
    
    html_path = os.path.join(out_dir, f"{base_filename}.html")
    text_path = os.path.join(out_dir, f"{base_filename}.txt")
    
    # Check if files already exist
    if os.path.exists(html_path) and os.path.exists(text_path):
        logging.info(f"Files already exist for {form} ({accession_number}), skipping")
        return False
    
    # Save main filing
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    with open(text_path, 'w', encoding='utf-8') as f:
        f.write(text_content)
    
    # Save attachments if any
    if attachments:
        for exhibit_name, content in attachments:
            # Use same naming convention but append exhibit name
            attachment_path = os.path.join(out_dir, f"{base_filename}-{exhibit_name}.txt")
            with open(attachment_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logging.info(f"Saved {exhibit_name}")
    
    logging.info(f"Saved {form} ({accession_number}) as HTML and text: {base_filename}")
    return True
