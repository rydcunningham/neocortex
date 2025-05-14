# extractors/aggregator_test.py
import os
import sys
import logging
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(PROJECT_ROOT)

from extractors.entity_aggregator import EntityAggregator

def aggregate_entities():
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Get absolute path to metadata directory
    metadata_dir = os.path.join(PROJECT_ROOT, "sample_drive/metadata/sec_filings")
    output_file = os.path.join(metadata_dir, "aggregated_entities.md")
    
    logging.info(f"Project root: {PROJECT_ROOT}")
    logging.info(f"Looking for entity files in: {metadata_dir}")
    
    # Debug: List all files in the directory
    for root, dirs, files in os.walk(metadata_dir):
        logging.info(f"\nExploring directory: {root}")
        for d in dirs:
            logging.info(f"  Dir: {d}")
        for f in files:
            if f.endswith('_entities.md'):
                logging.info(f"  Entity file found: {f}")
    
    # Initialize and run aggregator
    aggregator = EntityAggregator(metadata_dir)
    aggregator.aggregate_entities()
    
    # Print some stats
    type_counts = aggregator.get_entity_type_counts()
    print("\nEntity counts by type:")
    for entity_type, count in sorted(type_counts.items()):
        print(f"{entity_type}: {count:,}")
    
    # Save results
    aggregator.save_aggregated_table(output_file)
    
    # Example: Get all organization entities
    orgs_df = aggregator.get_entities_by_type('ORG')
    print(f"\nFound {len(orgs_df)} unique organizations")

if __name__ == "__main__":
    aggregate_entities()
