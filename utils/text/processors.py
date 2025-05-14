# utils/text/processors.py
import re
from typing import Dict, Set, Tuple

def clean_entity_text(text: str) -> str:
    """
    Clean entity text while preserving original capitalization.
    
    Args:
        text: Raw entity text
        
    Returns:
        Cleaned entity text
    """
    # Convert to single space and strip
    text = ' '.join(text.split())
    
    # Remove leading articles (the, a, an)
    text = re.sub(r'^(the|a|an)\s+', '', text, flags=re.IGNORECASE)
    
    # Handle possessives
    text = re.sub(r"'s$", '', text)  # Remove 's at the end
    text = re.sub(r"s'$", 's', text)  # Handle plural possessives
    
    # Remove common suffixes that might appear in financial docs
    text = re.sub(r"'s\s+(own|part|share|portion|division|subsidiary|segment)$", '', text, flags=re.IGNORECASE)
    
    # Remove quotes and other common punctuation at ends
    text = text.strip('"\'.,;:()[]{}')
    
    return text.strip()

def normalize_entity(entity_text: str) -> str:
    """
    Normalize entity text for comparison purposes.
    
    Args:
        entity_text: Raw entity text
        
    Returns:
        Normalized (lowercase, stripped) entity text
    """
    # Convert to lowercase for comparison
    text = entity_text.lower()
    
    # Remove all possessive forms
    text = re.sub(r"'s?\b", '', text)
    
    # Remove common corporate suffixes
    text = re.sub(r'\b(inc|corp|corporation|ltd|limited|llc|llp|lp|plc)\b\.?$', '', text)
    
    # Remove multiple spaces and trim
    text = ' '.join(text.split())
    
    return text.strip()

def entities_match(entity1: str, entity2: str) -> bool:
    """
    Compare two entities to see if they're effectively the same.
    
    Args:
        entity1: First entity text
        entity2: Second entity text
        
    Returns:
        True if entities match after normalization
    """
    return normalize_entity(entity1) == normalize_entity(entity2)

def get_context(doc, start: int, end: int, window: int = 5) -> str:
    """
    Get context window around an entity mention.
    
    Args:
        doc: spaCy Doc object
        start: Entity start index
        end: Entity end index
        window: Number of tokens for context window
        
    Returns:
        Context string
    """
    start_idx = max(0, start - window)
    end_idx = min(len(doc), end + window)
    context = doc[start_idx:end_idx].text
    return ' '.join(context.split())
