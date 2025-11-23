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

# NEW SIMPLIFIED FILENAMES
FILE_ROLES = os.path.join(INPUT_DIR, 'roles.csv')
FILE_SKILLS = os.path.join(INPUT_DIR, 'skills.csv')

def load_data_source():
    """
    Loads data from simplified CSVs.
    Returns: roles (list), skills (list), relationships (list), synonyms_map (dict)
    """
    roles = set()
    skills = set()
    relationships = [] 
    synonyms_map = {} 

    # 1. Load Real Data
    if os.path.exists(FILE_ROLES) and os.path.exists(FILE_SKILLS):
        print(f"[INFO] Loading Data from {INPUT_DIR}...")
        try:
            df_roles = pd.read_csv(FILE_ROLES, on_bad_lines='skip')
            df_skills = pd.read_csv(FILE_SKILLS, on_bad_lines='skip')
            
            # A. Process Skills (Capture Skill Synonyms like ML -> Machine Learning)
            if 'Skill' in df_skills.columns:
                for _, row in df_skills.iterrows():
                    skill = str(row['Skill']).strip()
                    skills.add(skill)
                    
                    if 'Synonyms' in row and pd.notna(row['Synonyms']):
                        for syn in str(row['Synonyms']).split('|'):
                            clean_syn = syn.strip()
                            if clean_syn:
                                # Map abbreviation "ML" to canonical "Machine Learning"
                                synonyms_map[clean_syn.lower()] = skill 

            # B. Process Roles
            if 'Role' in df_roles.columns:
                for _, row in df_roles.iterrows():
                    role = str(row['Role']).strip()
                    roles.add(role)
                    
                    # Role Synonyms (SDE -> Software Engineer)
                    if 'Synonyms' in row and pd.notna(row['Synonyms']):
                        for syn in str(row['Synonyms']).split('|'):
                            clean_syn = syn.strip()
                            if clean_syn:
                                synonyms_map[clean_syn.lower()] = role

                    # Relationships (Role <-> Skill)
                    if 'Skills' in row and pd.notna(row['Skills']):
                        for skill_name in str(row['Skills']).split('|'):
                            skill_name = skill_name.strip()
                            if skill_name:
                                skills.add(skill_name)
                                relationships.append((role, skill_name))
            
            print(f"[INFO] Loaded {len(roles)} roles, {len(skills)} skills, {len(synonyms_map)} synonyms.")
            
        except Exception as e:
            print(f"[WARN] CSV Load Failed: {e}. Falling back to Synthetic.")
            return generate_synthetic_data()
    else:
        print("[WARN] Files not found. Generating Synthetic Data...")
        return generate_synthetic_data()

    return list(roles), list(skills), relationships, synonyms_map

def generate_synthetic_data():
    """Fallback generator for Indian Market Context"""
    roles = set()
    skills = set()
    relationships = []
    synonyms = {
        "ml": "Machine Learning", 
        "ai": "Artificial Intelligence", 
        "sde": "Software Engineer",
        "mern": "MERN Stack Developer"
    }
    
    # Basic graph generation
    core_roles = {
        "Data Scientist": ["Python", "Machine Learning", "SQL"],
        "Software Engineer": ["Java", "System Design", "API"],
        "DevOps Engineer": ["AWS", "Docker", "Linux"],
        "MERN Stack Developer": ["React", "Node.js", "MongoDB"]
    }
    
    for role, role_skills in core_roles.items():
        roles.add(role)
        for s in role_skills:
            skills.add(s)
            relationships.append((role, s))
            
    return list(roles), list(skills), relationships, synonyms

def build_knowledge_base():
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    
    roles, skills, relationships, dynamic_synonyms = load_data_source()
    all_terms = list(set(roles + skills))
    
    if not all_terms:
        print("[ERROR] No terms found.")
        return

    print(f"[INFO] Indexing {len(all_terms)} terms...")

    # 1. Build Vector Index
    model = SentenceTransformer('all-MiniLM-L6-v2')
    embeddings = model.encode(all_terms, show_progress_bar=True)
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)
    
    # 2. Build Graph
    G = nx.Graph()
    # Add Nodes
    for r in roles: G.add_node(r, type='role')
    for s in skills: G.add_node(s, type='skill')
    # Add Edges
    for r, s in relationships:
        G.add_edge(r, s)
        
    # 3. Save
    faiss.write_index(index, INDEX_PATH)
    
    metadata = {
        "terms": all_terms, 
        "graph_neighbors": {n: list(G.neighbors(n)) for n in G.nodes()},
        "synonyms": dynamic_synonyms
    }
    
    with open(ONTOLOGY_PATH, 'w') as f:
        json.dump(metadata, f, indent=2)
        
    print(f"[SUCCESS] Knowledge Base Built. Graph Nodes: {G.number_of_nodes()}")

if __name__ == "__main__":
    build_knowledge_base()