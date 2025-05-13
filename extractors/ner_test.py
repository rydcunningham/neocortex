import spacy
import os
import sys
import re
from typing import Dict, Set, Tuple

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def load_document(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except UnicodeDecodeError:
        with open(file_path, 'r', encoding='latin-1') as file:
            return file.read()

def clean_entity_text(text):
    text = ' '.join(text.split())
    text = re.sub(r'^(the|a|an)\s+', '', text, flags=re.IGNORECASE)
    text = text.strip('"“\'.,;\–|()\’[]{}®')
    text = text.strip()
    return text

def chunk_text(text: str, chunk_size: int = 900000, overlap: int = 10000) -> list:
    """
    Split text into chunks with overlap to avoid cutting entities
    """
    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + chunk_size
        
        # If this isn't the last chunk, try to find a good breaking point
        if end < text_length:
            # Look for the last period or newline in the overlap region
            search_region = text[end-overlap:end+overlap]
            break_chars = ['. ', '\n', '. \n']
            
            # Find the last occurrence of any break character
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

def process_chunk(nlp, text: str, existing_contexts: Dict) -> Tuple[Set, Dict]:
    """Process a single chunk of text"""
    entities = set()
    
    doc = nlp(text)
    target_types = {
        'PERSON', 'ORG', 'GPE', 'LOC', 'PRODUCT', 'EVENT', 
        'FAC'
    }
    
    for ent in doc.ents:
        if ent.label_ in target_types:
            entity_text = clean_entity_text(ent.text)
            
            if len(entity_text) <= 1 or entity_text.isdigit():
                continue
            
            entity_tuple = (ent.label_, entity_text)
            
            # Only store the first context we see for this entity
            if entity_tuple not in existing_contexts:
                context = get_context(doc, ent.start, ent.end)
                existing_contexts[entity_tuple] = context
            
            entities.add(entity_tuple)
    
    return entities, existing_contexts

def extract_entities(text: str):
    nlp = spacy.load("en_core_web_trf")
    
    # Initialize sets and dicts for collecting results
    all_entities = set()
    all_contexts = {}
    
    # Chunk the text if it's too long
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

def main():
    # Assuming 10k files are in a folder named '10k_files' in root directory
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Process a single file for testing
    # file_path = os.path.join(root_dir, 'sample_drive/inbox/sec_filings/AAPL/10-Q/aapl-20250502-10-q.txt')  # Replace with your actual filename
    file_path = os.path.join(root_dir, 'sample_drive/inbox/sec_filings/0002021728/S-1/0002021728-20240930-s-1.txt')  # Replace with your actual filename

    print("Loading document...")
    text = load_document(file_path)
    print(f"Document length: {len(text)} characters")
    
    print("Extracting entities...")
    entities, contexts = extract_entities(text)
    print(f"Found {len(entities)} unique entities")
    
    print("\nResults:")
    print(format_markdown_table(entities, contexts))

if __name__ == "__main__":
    main()