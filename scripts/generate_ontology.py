# scripts/generate_ontology.py
import json
import os
import networkx as nx
from sentence_transformers import SentenceTransformer, util

# --- CONFIG ---
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), '../entities/ontology.json')

# --- PROXY DATASET (Simulating the JobXMLC Job-Skill Data) ---
# In a real scenario, you would load this from a CSV of job descriptions.
raw_data = [
    {"role": "Data Scientist", "skills": ["Python", "SQL", "Machine Learning", "TensorFlow", "Pandas"]},
    {"role": "Software Engineer", "skills": ["Java", "System Design", "API", "Microservices", "SQL"]},
    {"role": "Frontend Developer", "skills": ["React", "JavaScript", "CSS", "HTML", "Redux"]},
    {"role": "Backend Developer", "skills": ["Node.js", "Python", "Django", "Database", "API"]},
    {"role": "AI Engineer", "skills": ["Deep Learning", "NLP", "Computer Vision", "PyTorch"]},
]

# Synonyms mapping (Explicit knowledge)
base_synonyms = {
    "AI": "Artificial Intelligence",
    "ML": "Machine Learning",
    "SDE": "Software Development Engineer",
    "JS": "JavaScript",
    "ReactJS": "React",
    "CV": "Computer Vision"
}

def build_ontology():
    print("Loading Embedding Model (this may take a moment)...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # 1. Build the Graph (NetworkX)
    G = nx.Graph()
    
    all_terms = set()
    
    print("Building Graph...")
    for entry in raw_data:
        role = entry['role']
        skills = entry['skills']
        all_terms.add(role)
        
        # Add nodes
        G.add_node(role, type='role')
        
        for skill in skills:
            all_terms.add(skill)
            G.add_node(skill, type='skill')
            # Edge: Role implies Skill
            G.add_edge(role, skill, weight=1.0)
            
            # Edge: Skill co-occurrence (clique expansion)
            for other_skill in skills:
                if skill != other_skill:
                    G.add_edge(skill, other_skill, weight=0.5)

    # 2. Semantic Synonym Discovery (SBERT)
    # We compare all terms to find hidden synonyms
    term_list = list(all_terms)
    embeddings = model.encode(term_list, convert_to_tensor=True)
    
    cosine_scores = util.cos_sim(embeddings, embeddings)
    
    learned_synonyms = {}
    
    # Threshold for "Same Meaning"
    THRESHOLD = 0.85 
    
    print("Mining Semantic Synonyms...")
    for i in range(len(term_list)):
        for j in range(i + 1, len(term_list)):
            score = cosine_scores[i][j]
            if score > THRESHOLD:
                term_a = term_list[i]
                term_b = term_list[j]
                # Store bidirectional
                learned_synonyms[term_a] = term_b
                learned_synonyms[term_b] = term_a
                
    # Merge explicit and learned synonyms
    final_synonyms = {**base_synonyms, **learned_synonyms}
    
    # 3. Export Structure
    # We export an adjacency list for fast runtime lookup
    export_data = {
        "graph_neighbors": {node: list(G.neighbors(node)) for node in G.nodes()},
        "synonyms": final_synonyms
    }
    
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, 'w') as f:
        json.dump(export_data, f, indent=2)
        
    print(f"Ontology successfully generated at: {OUTPUT_PATH}")

if __name__ == "__main__":
    build_ontology()