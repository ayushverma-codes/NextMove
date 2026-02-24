import sys
import os
import json
import faiss # Required: pip install faiss-cpu

# --- SETUP PATHS ---
# We dynamically find the project root to locate artifacts safely
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARTIFACTS_DIR = os.path.join(BASE_DIR, 'workspace_folder', 'artifacts')
ONTOLOGY_PATH = os.path.join(ARTIFACTS_DIR, 'ontology.json')
INDEX_PATH = os.path.join(ARTIFACTS_DIR, 'skills.index')

def inspect_knowledge_base():
    print(f"=== 🧠 Evaluating Knowledge Base (Graph & Index) ===")
    print(f"[INFO] Looking for artifacts in: {ARTIFACTS_DIR}\n")

    # 1. CHECK ONTOLOGY (The Graph)
    if not os.path.exists(ONTOLOGY_PATH):
        print(f"❌ CRITICAL ERROR: ontology.json not found at {ONTOLOGY_PATH}")
        print("   -> Run 'python scripts/build_knowledge_base.py' first.")
        return

    try:
        with open(ONTOLOGY_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        terms = data.get("terms", [])
        term_types = data.get("term_types", {})
        synonyms = data.get("synonyms", {})
        graph_neighbors = data.get("graph_neighbors", {})
        
        # Calculate Graph Density (Research Metric)
        total_nodes = len(terms)
        # Edges are stored as adjacency lists; we sum lengths and divide by 2 (undirected)
        total_edges = sum(len(neighbors) for neighbors in graph_neighbors.values()) // 2
        
        print(f"📊 [Graph Statistics for Paper]")
        print(f"   - Total Terms (Nodes): {total_nodes}")
        print(f"   - Semantic Relations (Edges): {total_edges}")
        print(f"   - Synonym Mappings: {len(synonyms)}")
        
        # Breakdown by Type (Role vs Skill vs Location)
        counts = {"role": 0, "skill": 0, "location": 0, "company": 0, "other": 0}
        for t_type in term_types.values():
            counts[t_type if t_type in counts else "other"] += 1
            
        print(f"   - Term Distribution: {counts}")

    except Exception as e:
        print(f"❌ Error reading ontology: {e}")

    # 2. CHECK FAISS INDEX (The Vector Space)
    print(f"\n🧩 [Vector Index Statistics]")
    if not os.path.exists(INDEX_PATH):
        print(f"❌ CRITICAL ERROR: skills.index not found at {INDEX_PATH}")
        return

    try:
        index = faiss.read_index(INDEX_PATH)
        print(f"   - Total Indexed Vectors: {index.ntotal}")
        print(f"   - Vector Dimensions: {index.d}")
        print(f"   - Index Type: FlatL2 (Euclidean Distance)")
        
        if index.ntotal == total_nodes:
            print("✅ CONSISTENCY CHECK: PASS (Vector count matches Graph nodes)")
        else:
            print(f"⚠️ CONSISTENCY WARNING: Graph has {total_nodes} nodes but Index has {index.ntotal} vectors.")

    except Exception as e:
        print(f"❌ Error reading FAISS index: {e}")

if __name__ == "__main__":
    inspect_knowledge_base()