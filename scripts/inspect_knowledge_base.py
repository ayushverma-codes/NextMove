import json
import os
import time

# --- CONFIGURATION ---
# Get the directory where this script is located (e.g., .../NextMove/scripts)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Go up one level to the Project Root (e.g., .../NextMove)
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

# Define paths relative to the Project Root
WORKSPACE_DIR = os.path.join(PROJECT_ROOT, 'workspace_folder')
ARTIFACTS_DIR = os.path.join(WORKSPACE_DIR, 'artifacts')
ONTOLOGY_PATH = os.path.join(ARTIFACTS_DIR, 'ontology.json')

# --- HARDCODED DEMO TERMS (Updated for all 4 files) ---
DEMO_TERMS = [
    "Ansible Operations Engineer", # 1. ROLE (Complex Node)
    "Python",                      # 2. SKILL (Reverse Lookup)
    "Bengaluru",                   # 3. LOCATION (Location -> Country)
    "Tata Consultancy Services"    # 4. COMPANY (Company -> Industry)
]

def load_ontology():
    if not os.path.exists(ONTOLOGY_PATH):
        print(f"[ERROR] Ontology file not found at: {ONTOLOGY_PATH}")
        print(f"       (Checked Project Root: {PROJECT_ROOT})")
        return None
    with open(ONTOLOGY_PATH, 'r') as f:
        return json.load(f)

def inspect_node(term, ontology):
    print(f"\n{'='*60}")
    print(f" 🤖 SYSTEM INPUT: '{term}'")
    print(f"{'='*60}")
    
    # 1. Check for Synonyms (Normalization)
    if term.lower() in ontology['synonyms']:
        resolved_term = ontology['synonyms'][term.lower()]
        print(f"✅ \033[1mNORMALIZATION:\033[0m Detected Synonym '{term}' -> Resolving to '{resolved_term}'")
        term = resolved_term 
    
    # 2. Retrieve Metadata
    term_type = ontology['term_types'].get(term, "Unknown")
    neighbors = ontology['graph_neighbors'].get(term, [])
    
    # 3. Display Logic
    print(f"🔹 \033[1mENTITY TYPE:\033[0m {term_type.upper()}")
    
    if neighbors:
        print(f"🔹 \033[1mSEMANTIC EXPANSION (Graph Neighbors):\033[0m")
        print(f"   The Knowledge Graph suggests adding these constraints to the SQL Query:")
        # Format the output nicely
        preview = neighbors[:10]
        preview_str = ", ".join(preview)
        print(f"   [ {preview_str} ... ]")
        
        if len(neighbors) > 10:
            print(f"   (and {len(neighbors)-10} others)")
    else:
        print("🔹 \033[1mCONNECTIONS:\033[0m No outgoing edges (Leaf Node)")

    print("-" * 60)
    time.sleep(1.5) 

if __name__ == "__main__":
    print("\n🚀 STARTING KNOWLEDGE BASE DEMO (All 4 Types)...")
    print(f"   (Loading artifacts from: {ARTIFACTS_DIR})\n")
    
    data = load_ontology()
    
    if data:
        for term in DEMO_TERMS:
            inspect_node(term, data)
            
    print("\n✅ DEMO COMPLETE.")