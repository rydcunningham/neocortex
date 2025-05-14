# utils/markdown/parser.py
import pandas as pd
import logging
from typing import Optional

def parse_entity_table(file_path: str) -> Optional[pd.DataFrame]:
    """
    Parse a markdown table containing entity data into a pandas DataFrame.
    
    Args:
        file_path: Path to markdown file containing entity table
        
    Returns:
        DataFrame with columns: Entity Type, Entity Name, First Context
        Returns None if parsing fails
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split into lines and find table start
        lines = content.split('\n')
        try:
            table_start = next(i for i, line in enumerate(lines) if '| Entity Type |' in line)
        except StopIteration:
            logging.warning(f"No entity table found in {file_path}")
            return None
        
        # Parse header
        header = [col.strip() for col in lines[table_start].split('|')[1:-1]]
        
        # Parse data rows
        rows = []
        for line in lines[table_start+2:]:  # Skip header and separator
            if line.startswith('|'):
                cells = [cell.strip() for cell in line.split('|')[1:-1]]
                if len(cells) == len(header):
                    rows.append(cells)
            else:
                break  # End of table
                
        return pd.DataFrame(rows, columns=header)
        
    except Exception as e:
        logging.error(f"Error parsing {file_path}: {e}")
        return None
