# utils/markdown/formatter.py
from typing import List
import pandas as pd

def format_entity_table(df: pd.DataFrame, 
                       columns: List[str] = None) -> str:
    """
    Format a DataFrame as a markdown table.
    
    Args:
        df: DataFrame containing entity data
        columns: List of columns to include (defaults to all)
        
    Returns:
        Formatted markdown table as string
    """
    if df.empty:
        return "No entities found."
    
    # Use specified columns or all columns
    columns = columns or df.columns.tolist()
    
    # Create header
    header = " | ".join(columns)
    markdown = f"| {header} |\n"
    
    # Create separator
    separator = "|" + "|".join(["---" for _ in columns]) + "|\n"
    markdown += separator
    
    # Add rows
    for _, row in df.iterrows():
        # Handle special formatting for Documents column
        row_data = []
        for col in columns:
            value = row[col]
            if col == 'Documents' and isinstance(value, list):
                value = ", ".join(value)
            row_data.append(str(value))
            
        markdown += f"| {' | '.join(row_data)} |\n"
    
    return markdown

def save_markdown_table(df: pd.DataFrame, 
                       output_file: str,
                       columns: List[str] = None) -> None:
    """
    Save DataFrame as a markdown table file.
    
    Args:
        df: DataFrame containing entity data
        output_file: Path to save markdown file
        columns: List of columns to include (defaults to all)
    """
    markdown = format_entity_table(df, columns)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(markdown)
