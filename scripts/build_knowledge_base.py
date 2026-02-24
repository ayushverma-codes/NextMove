import json
import os
import networkx as nx
import pandas as pd
import faiss
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
    terms_metadata = {} 
    all_terms = []
    synonyms_map = {}
    graph_edges = []

    def process_file(filepath, main_col, type_label, syn_col=None, edge_col=None):
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
                
                # 1. Handle Synonyms
                if syn_col and syn_col in row and pd.notna(row[syn_col]):
                    for syn in str(row[syn_col]).split('|'):
                        clean_syn = syn.strip()
                        if clean_syn:
                            synonyms_map[clean_syn.lower()] = main_term
                            
                # 2. Handle Graph Edges (The Upgrade)
                if edge_col:
                    # Case A: Roles -> Skills (Split by pipe)
                    if type_label == 'role' and edge_col in row and pd.notna(row[edge_col]):
                        for s in str(row[edge_col]).split('|'):
                            s_clean = s.strip()
                            if s_clean:
                                graph_edges.append((main_term, s_clean))
                    
                    # Case B: Companies -> Industry (Single Value)
                    elif type_label == 'company' and edge_col in row and pd.notna(row[edge_col]):
                        target = str(row[edge_col]).strip()
                        if target:
                            graph_edges.append((main_term, target))
                            terms_metadata[target] = "industry" # Tag the target
                            
                    # Case C: Locations -> Country (Single Value)
                    elif type_label == 'location' and edge_col in row and pd.notna(row[edge_col]):
                        target = str(row[edge_col]).strip()
                        if target:
                            graph_edges.append((main_term, target))
                            terms_metadata[target] = "country" # Tag the target

        except Exception as e:
            print(f"[ERROR] Failed to process {filepath}: {e}")

    # --- LOAD ALL DATA ---
    print(f"[INFO] Loading Data from {INPUT_DIR}...")
    
    # We now pass the column name that creates relationships (edge_col)
    process_file(FILE_ROLES, 'Role', 'role', 'Synonyms', edge_col='Skills')
    process_file(FILE_SKILLS, 'Skill', 'skill', 'Synonyms', edge_col=None) # Skills are targets, not sources
    process_file(FILE_LOCATIONS, 'Location', 'location', 'Synonyms', edge_col='Country') # New Link!
    process_file(FILE_COMPANIES, 'Company', 'company', 'Synonyms', edge_col='Industry') # New Link!

    return all_terms, terms_metadata, synonyms_map, graph_edges

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
        "term_types": terms_metadata, 
        "graph_neighbors": {n: list(G.neighbors(n)) for n in G.nodes()},
        "synonyms": synonyms
    }
    
    with open(ONTOLOGY_PATH, 'w') as f:
        json.dump(metadata, f, indent=2)
        
    print(f"[SUCCESS] Knowledge Base Built. Nodes: {G.number_of_nodes()}, Edges: {G.number_of_edges()}")

if __name__ == "__main__":
    build_knowledge_base()