import os
import sys
from collections import Counter
from typing import Dict, Set

# Import the functions we need from entity_extractor
from extractor import (
    extract_entities, 
    load_document, 
    export_results,
    get_entity_type_counts,
    should_process_file
)

def process_sec_filings():
    # Get root directory and construct path to sec_filings
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sec_filings_dir = os.path.join(root_dir, 'sample_drive', 'inbox', 'sec_filings')
    metadata_dir = os.path.join(root_dir, 'sample_drive', 'metadata', 'sec_filings')

    # Initialize counters
    total_files = 0
    processed_files = 0
    skipped_files = 0
    total_entities = Counter()
    
    # First count total files
    for company_dir in os.listdir(sec_filings_dir):
        company_path = os.path.join(sec_filings_dir, company_dir)
        if not os.path.isdir(company_path):
            continue
        for filing_type in os.listdir(company_path):
            filing_type_path = os.path.join(company_path, filing_type)
            if not os.path.isdir(filing_type_path):
                continue
            total_files += len([f for f in os.listdir(filing_type_path) if f.endswith('.txt')])
    
    print(f"Found {total_files} files to process")
    
    # Process each company directory
    for company_dir in os.listdir(sec_filings_dir):
        company_path = os.path.join(sec_filings_dir, company_dir)
        if not os.path.isdir(company_path):
            continue
            
        print(f"\nProcessing company: {company_dir}")
        
        # Process each filing type directory
        for filing_type in os.listdir(company_path):
            filing_type_path = os.path.join(company_path, filing_type)
            if not os.path.isdir(filing_type_path):
                continue
                
            print(f"Processing filing type: {filing_type}")
            
            # Process each .txt file
            for file_name in os.listdir(filing_type_path):
                if not file_name.endswith('.txt'):
                    continue
                    
                file_path = os.path.join(filing_type_path, file_name)
                
                # Create output path
                output_dir = os.path.join(metadata_dir, company_dir, filing_type)
                output_file = os.path.join(output_dir, f"{os.path.splitext(file_name)[0]}_entities.md")
                
                # Check if we should process this file
                if not should_process_file(output_file):
                    skipped_files += 1
                    processed_files += 1
                    print(f"\nSkipping {file_name} - output already exists")
                    print(f"Progress: {processed_files}/{total_files} files ({processed_files/total_files*100:.1f}%)")
                    continue
                
                print(f"\nProcessing file {processed_files + 1}/{total_files}: {file_name}")
                
                # Load and process the document
                text = load_document(file_path)
                print(f"Document length: {len(text):,} characters")
                
                entities, contexts = extract_entities(text)
                
                # Update entity type counts
                type_counts = get_entity_type_counts(entities)
                for entity_type, count in type_counts.items():
                    total_entities[entity_type] += count
                
                # Export results
                export_results(entities, contexts, output_file)
                
                processed_files += 1
                print(f"Found {len(entities):,} unique entities")
                print(f"Progress: {processed_files}/{total_files} files ({processed_files/total_files*100:.1f}%)")
    
    # Print final statistics
    print("\nProcessing complete!")
    print(f"Files skipped (already processed): {skipped_files:,}")
    print(f"Files processed this run: {processed_files - skipped_files:,}")
    print(f"Total files checked: {processed_files:,}")
    print("\nTotal entities found by type (new files only):")
    for entity_type, count in sorted(total_entities.items()):
        print(f"{entity_type}: {count:,}")

if __name__ == "__main__":
    print("Starting SEC filings processing...")
    process_sec_filings()