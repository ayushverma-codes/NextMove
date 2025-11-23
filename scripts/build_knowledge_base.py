import json
import os
import networkx as nx
import pandas as pd
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKSPACE_DIR = os.path.join(BASE_DIR, 'workspace_folder')
INPUT_DIR = os.path.join(WORKSPACE_DIR, 'input')
ARTIFACTS_DIR = os.path.join(WORKSPACE_DIR, 'artifacts')

ONTOLOGY_PATH = os.path.join(ARTIFACTS_DIR, 'ontology.json')
INDEX_PATH = os.path.join(ARTIFACTS_DIR, 'skills.index')

# Input Files
FILE_ROLES = os.path.join(INPUT_DIR, 'roles.csv')
FILE_SKILLS = os.path.join(INPUT_DIR, 'skills.csv')
FILE_LOCATIONS = os.path.join(INPUT_DIR, 'locations.csv')
FILE_COMPANIES = os.path.join(INPUT_DIR, 'companies.csv')

def load_data_source():
    terms_metadata = {} # Maps term -> type (e.g. "Java": "skill")
    all_terms = []
    synonyms_map = {}
    graph_edges = []

    # --- HELPER: Generic CSV Loader ---
    def process_file(filepath, main_col, type_label, syn_col=None):
        if not os.path.exists(filepath):
            print(f"[WARN] Missing {filepath}")
            return
        
        try:
            df = pd.read_csv(filepath, on_bad_lines='skip')
            if main_col not in df.columns: return
            
            for _, row in df.iterrows():
                main_term = str(row[main_col]).strip()
                all_terms.append(main_term)
                terms_metadata[main_term] = type_label
                
                # Handle Synonyms
                if syn_col and syn_col in row and pd.notna(row[syn_col]):
                    for syn in str(row[syn_col]).split('|'):
                        clean_syn = syn.strip()
                        if clean_syn:
                            synonyms_map[clean_syn.lower()] = main_term
                            
                # Handle Roles <-> Skills Graph Edges (Specific to roles.csv)
                if type_label == 'role' and 'Skills' in row and pd.notna(row['Skills']):
                    for s in str(row['Skills']).split('|'):
                        s_clean = s.strip()
                        if s_clean:
                            graph_edges.append((main_term, s_clean))
                            
        except Exception as e:
            print(f"[ERROR] Failed to process {filepath}: {e}")

    # --- LOAD ALL DATA ---
    print(f"[INFO] Loading Data from {INPUT_DIR}...")
    process_file(FILE_ROLES, 'Role', 'role', 'Synonyms')
    process_file(FILE_SKILLS, 'Skill', 'skill', 'Synonyms')
    process_file(FILE_LOCATIONS, 'Location', 'location', 'Synonyms')
    process_file(FILE_COMPANIES, 'Company', 'company', 'Synonyms')

    # Fallback for Indian Context if empty
    if not all_terms:
        return generate_synthetic_data()

    return all_terms, terms_metadata, synonyms_map, graph_edges

def generate_synthetic_data():
    """Fallback with Indian Context + Locations"""
    print("[INFO] Generating Synthetic Data...")
    terms = ["Data Scientist", "Python", "Bengaluru", "Mumbai", "Google", "TCS", "Fresher", "SDE-1"]
    metadata = {
        "Data Scientist": "role", "Python": "skill", 
        "Bengaluru": "location", "Mumbai": "location",
        "Google": "company", "TCS": "company"
    }
    synonyms = {"blr": "Bengaluru", "bombay": "Mumbai", "ml": "Machine Learning"}
    edges = [("Data Scientist", "Python")]
    return terms, metadata, synonyms, edges

def build_knowledge_base():
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    
    all_terms, terms_metadata, synonyms, edges = load_data_source()
    
    if not all_terms:
        print("[ERROR] No terms found.")
        return

    print(f"[INFO] Indexing {len(all_terms)} terms...")

    # 1. Build Vector Index
    model = SentenceTransformer('all-MiniLM-L6-v2')
    embeddings = model.encode(all_terms, show_progress_bar=True)
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)
    faiss.write_index(index, INDEX_PATH)
    
    # 2. Build Graph
    G = nx.Graph()
    for u, v in edges:
        G.add_edge(u, v)
    
    # 3. Save Metadata
    metadata = {
        "terms": all_terms, 
        "term_types": terms_metadata, # Stores if "Python" is a skill or company
        "graph_neighbors": {n: list(G.neighbors(n)) for n in G.nodes()},
        "synonyms": synonyms
    }
    
    with open(ONTOLOGY_PATH, 'w') as f:
        json.dump(metadata, f, indent=2)
        
    print(f"[SUCCESS] Knowledge Base Built. Graph Nodes: {G.number_of_nodes()}")

if __name__ == "__main__":
    build_knowledge_base()