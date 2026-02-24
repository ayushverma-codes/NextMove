import json
import networkx as nx
import matplotlib.pyplot as plt
import os
import time

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Adjust if your workspace is one level up
WORKSPACE_DIR = os.path.join(os.path.dirname(BASE_DIR), 'workspace_folder') 
ARTIFACTS_DIR = os.path.join(WORKSPACE_DIR, 'artifacts')
ONTOLOGY_PATH = os.path.join(ARTIFACTS_DIR, 'ontology.json')

# --- THE 4 DEMO SCENARIOS ---
DEMO_SCENARIOS = [
    {"term": "Ansible Operations Engineer", "file": "roles.csv", "desc": "Role ↔ Skills"},
    {"term": "Python",                      "file": "skills.csv", "desc": "Skill ↔ Roles (Reverse Lookup)"},
    {"term": "Google",                      "file": "companies.csv", "desc": "Company ↔ Industry"},
    {"term": "Bengaluru",                   "file": "locations.csv", "desc": "Location ↔ Country"},
]

def load_data():
    if not os.path.exists(ONTOLOGY_PATH):
        print("Ontology not found. Run build_knowledge_base.py first.")
        return None
    with open(ONTOLOGY_PATH, 'r') as f:
        return json.load(f)

def visualize_term(term, desc, data):
    print(f"\n--- Visualizing: {term} ({desc}) ---")
    
    G = nx.Graph()
    neighbors = data['graph_neighbors'].get(term, [])
    
    if not neighbors:
        print(f"⚠️ No connections found for {term}. Did you update the build script?")
        return

    # Add Central Node
    G.add_node(term, type='center')
    
    # Add Neighbors (Limit to 15 for cleanliness)
    for n in neighbors[:15]:
        G.add_edge(term, n)
    
    # --- PLOTTING ---
    plt.figure(figsize=(10, 6))
    pos = nx.spring_layout(G, k=0.6)
    
    # Draw Center
    nx.draw_networkx_nodes(G, pos, nodelist=[term], node_color='red', node_size=3000, label=term)
    
    # Draw Neighbors
    neighbor_nodes = [n for n in G.nodes() if n != term]
    nx.draw_networkx_nodes(G, pos, nodelist=neighbor_nodes, node_color='skyblue', node_size=1500)
    
    # Draw Edges & Labels
    nx.draw_networkx_edges(G, pos, edge_color='gray', alpha=0.5)
    nx.draw_networkx_labels(G, pos, font_size=9, font_weight='bold')
    
    plt.title(f"Knowledge Graph: {term}\n({desc})", fontsize=14)
    plt.axis('off')
    
    # Show plot (Blocking)
    print(f"Displaying graph for {term}...")
    plt.show()

if __name__ == "__main__":
    data = load_data()
    if data:
        for scenario in DEMO_SCENARIOS:
            visualize_term(scenario['term'], scenario['desc'], data)