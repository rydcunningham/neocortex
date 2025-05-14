# extractors/entity_aggregator.py
import os
import sys
import logging
from pathlib import Path
from typing import Optional, List, Dict
import pandas as pd

# Add project root to Python path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(PROJECT_ROOT)

from utils.markdown.parser import parse_entity_table
from utils.markdown.formatter import save_markdown_table
from utils.text.processors import normalize_entity

class EntityAggregator:
    def __init__(self, metadata_dir: str):
        """
        Initialize EntityAggregator.
        
        Args:
            metadata_dir: Directory containing entity markdown files
        """
        self.metadata_dir = Path(metadata_dir)
        self.aggregated_data: Optional[pd.DataFrame] = None
        
    # extractors/entity_aggregator.py
    def find_entity_files(self) -> List[Path]:
        """
        Find all entity markdown files recursively in metadata directory.
        Looks for files ending with '_entities.md' in any subfolder.
        """
        entity_files = []
        
        # Debug current working directory
        logging.info(f"Current working directory: {os.getcwd()}")
        logging.info(f"Searching in: {self.metadata_dir}")
        
        for root, dirs, files in os.walk(self.metadata_dir):
            logging.debug(f"Scanning directory: {root}")
            for file in files:
                if file.endswith('_entities.md'):
                    full_path = Path(root) / file
                    relative_path = full_path.relative_to(self.metadata_dir)
                    logging.info(f"Found entity file: {relative_path}")
                    entity_files.append(full_path)
        
        if not entity_files:
            logging.warning(f"No entity files found recursively in {self.metadata_dir}")
        else:
            logging.info(f"Found {len(entity_files)} entity files:")
            for f in entity_files:
                logging.info(f"  {f.relative_to(self.metadata_dir)}")
            
        return entity_files

    def process_entity_file(self, file_path: Path) -> Optional[pd.DataFrame]:
        """
        Process a single entity file.
        
        Args:
            file_path: Path to entity markdown file
            
        Returns:
            DataFrame with entities and document reference
        """
        logging.info(f"Processing {file_path}")
        try:
            df = parse_entity_table(str(file_path))
            if df is not None:
                logging.info(f"Found {len(df)} entities in {file_path.name}")
                # Add document reference and normalized entity name
                df['Documents'] = file_path.name
                df['Normalized Name'] = df['Entity Name'].apply(normalize_entity)
                return df
            else:
                logging.warning(f"No valid entity table found in {file_path}")
            
        except Exception as e:
            logging.error(f"Error processing {file_path}: {e}")
        
        return None

    def aggregate_entities(self) -> None:
        """
        Aggregate entities across all files.
        Stores result in self.aggregated_data.
        """
        logging.info(f"Searching for entity files in {self.metadata_dir}")
        entity_files = self.find_entity_files()
        if not entity_files:
            return
        
        logging.info(f"Processing {len(entity_files)} entity files...")
        
        # Process all files
        dfs = []
        for file_path in entity_files:
            df = self.process_entity_file(file_path)
            if df is not None:
                dfs.append(df)
        
        if not dfs:
            logging.warning("No valid data found in any entity files")
            return
            
        # Combine all dataframes
        combined_df = pd.concat(dfs, ignore_index=True)
        logging.info(f"Combined {len(dfs)} dataframes with total {len(combined_df)} rows")
        
        # Group by Entity Type and normalized name
        grouped = combined_df.groupby(['Entity Type', 'Normalized Name']).agg({
            'Entity Name': 'first',  # Keep original capitalization from first occurrence
            'First Context': 'first',  # Keep first context seen
            'Documents': lambda x: sorted(list(set(x)))  # Unique list of documents
        }).reset_index()
        
        # Drop the normalized name column used for grouping
        grouped = grouped.drop('Normalized Name', axis=1)
        
        # Reorder columns
        self.aggregated_data = grouped[['Entity Type', 'Entity Name', 'First Context', 'Documents']]
        
        logging.info(f"Found {len(self.aggregated_data)} unique entities across {len(entity_files)} files")
    
    def save_aggregated_table(self, output_file: str) -> None:
        """
        Save aggregated entities as markdown table.
        
        Args:
            output_file: Path to save markdown file
        """
        if self.aggregated_data is None:
            logging.error("No aggregated data available. Run aggregate_entities() first.")
            return
            
        # Create output directory if needed
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        save_markdown_table(self.aggregated_data, str(output_path))
        logging.info(f"Saved aggregated entities to {output_file}")
    
    def get_entity_type_counts(self) -> Dict[str, int]:
        """Get count of entities by type"""
        if self.aggregated_data is None:
            return {}
        return dict(self.aggregated_data['Entity Type'].value_counts())
    
    def get_entities_by_type(self, entity_type: str) -> pd.DataFrame:
        """
        Get all entities of a specific type.
        
        Args:
            entity_type: Entity type to filter for (e.g., 'ORG', 'PERSON')
            
        Returns:
            DataFrame containing only entities of specified type
        """
        if self.aggregated_data is None:
            return pd.DataFrame()
        return self.aggregated_data[self.aggregated_data['Entity Type'] == entity_type]

