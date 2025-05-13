import spacy
import os
import sys
import re
from typing import Dict, Set, Tuple
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def load_document(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except UnicodeDecodeError:
        with open(file_path, 'r', encoding='latin-1') as file:
            return file.read()

def clean_entity_text(text: str) -> str:
    """Cleans entity text while preserving original capitalization"""
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
    
    # Final whitespace cleanup
    text = text.strip()
    
    return text

def chunk_text(text: str, chunk_size: int = 900000, overlap: int = 10000) -> list:
    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + chunk_size
        
        if end < text_length:
            search_region = text[end-overlap:end+overlap]
            break_chars = ['. ', '\n', '. \n']
            
            best_break = -1
            for char in break_chars:
                last_break = search_region.rfind(char)
                if last_break > best_break:
                    best_break = last_break
            
            if best_break != -1:
                end = end - overlap + best_break + 1
            
        chunks.append(text[start:end])
        start = end

    return chunks

def get_context(doc, start, end, window=5):
    start_idx = max(0, start - window)
    end_idx = min(len(doc), end + window)
    context = doc[start_idx:end_idx].text
    return ' '.join(context.split())

def normalize_entity(entity_text: str) -> str:
    """Normalization rules for comparing entities - returns lowercase normalized version"""
    # Convert to lowercase for comparison
    text = entity_text.lower()
    
    # Remove all possessive forms
    text = re.sub(r"'s?\b", '', text)
    
    # Remove common corporate suffixes
    text = re.sub(r'\b(inc|corp|corporation|ltd|limited|llc|llp|lp|plc)\b\.?$', '', text)
    
    # Remove multiple spaces and trim
    text = ' '.join(text.split())
    text = text.strip()
    
    return text

def entities_match(entity1: str, entity2: str) -> bool:
    """Compare two entities to see if they're effectively the same"""
    return normalize_entity(entity1) == normalize_entity(entity2)

def process_chunk(nlp, text: str, existing_contexts: Dict) -> Tuple[Set, Dict]:
    """Process a single chunk of text"""
    entities = set()
    normalized_to_original = {}  # Keep track of normalized -> original mapping
    
    doc = nlp(text)
    target_types = {'PERSON', 'ORG', 'GPE', 'LOC', 'PRODUCT', 'EVENT', 'FAC'}
    
    for ent in doc.ents:
        if ent.label_ in target_types:
            # Clean the entity text while preserving case
            original_text = clean_entity_text(ent.text)
            
            if len(original_text) <= 1 or original_text.isdigit():
                continue
            
            # Get normalized version for comparison
            normalized_text = normalize_entity(original_text)
            
            # Check if we already have this entity (using normalized form)
            existing_match = None
            for existing_entity in entities:
                if (existing_entity[0] == ent.label_ and 
                    normalize_entity(existing_entity[1]) == normalized_text):
                    existing_match = existing_entity
                    break
            
            if existing_match:
                entity_tuple = existing_match
            else:
                entity_tuple = (ent.label_, original_text)
            
            # Only store the first context we see for this entity
            if entity_tuple not in existing_contexts:
                context = get_context(doc, ent.start, ent.end)
                existing_contexts[entity_tuple] = context
            
            entities.add(entity_tuple)
    
    return entities, existing_contexts

def extract_entities(text: str):
    nlp = spacy.load("en_core_web_trf")
    
    all_entities = set()
    all_contexts = {}
    
    if len(text) > 900000:
        chunks = chunk_text(text)
        print(f"Processing {len(chunks)} chunks...")
        
        for i, chunk in enumerate(chunks, 1):
            print(f"Processing chunk {i}/{len(chunks)}...")
            chunk_entities, all_contexts = process_chunk(nlp, chunk, all_contexts)
            all_entities.update(chunk_entities)
    else:
        all_entities, all_contexts = process_chunk(nlp, text, all_contexts)
    
    return all_entities, all_contexts

def format_markdown_table(entities, contexts):
    if not entities:
        return "No entities found."
        
    markdown = "| Entity Type | Entity Name | First Context |\n"
    markdown += "|------------|-------------|---------------|\n"
    
    sorted_entities = sorted(entities)
    
    for entity in sorted_entities:
        context = contexts.get(entity, "")
        markdown += f"| {entity[0]} | {entity[1]} | {context} |\n"
    
    return markdown

def export_results(entities: Set, contexts: Dict, output_file: Path) -> None:
    """Export entities and contexts to a markdown file"""
    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(output_file)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(format_markdown_table(entities, contexts))

def get_entity_type_counts(entities: Set) -> Dict:
    """Get count of entities by type"""
    type_counts = {}
    for entity_type, _ in entities:
        type_counts[entity_type] = type_counts.get(entity_type, 0) + 1
    return type_counts

def should_process_file(output_file: str) -> bool:
    """Check if we need to process this file or if output already exists"""
    return not os.path.exists(output_file)

def main():
    # Example single file processing
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    file_path = os.path.join(root_dir, 'sample_drive/inbox/sec_filings/0002021728/S-1/0002021728-20240930-s-1.txt')
    output_path = os.path.join(root_dir, 'sample_drive/metadata/sec_filings/0002021728/S-1/0002021728-20240930-s-1_entities.md')

    if not os.path.exists(output_path):
        print("Loading document...")
        text = load_document(file_path)
        print(f"Document length: {len(text):,} characters")
    
        print("Extracting entities...")
        entities, contexts = extract_entities(text)
        
        # Print entity counts by type
        type_counts = get_entity_type_counts(entities)
        print("\nEntity counts by type:")
        for entity_type, count in sorted(type_counts.items()):
            print(f"{entity_type}: {count:,}")
        
        print(f"\nTotal unique entities found: {len(entities):,}")
        print(f"Exporting results to {output_path}")
        export_results(entities, contexts, output_path)
    else:
        print(f"Results already exist at {output_path}")

if __name__ == "__main__":
    main()