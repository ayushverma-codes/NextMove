import json
import os
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

class TermNormalizer:
    def __init__(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.ontology_path = os.path.join(base_dir, 'workspace_folder', 'artifacts', 'ontology.json')
        self.index_path = os.path.join(base_dir, 'workspace_folder', 'artifacts', 'skills.index')
        
        self.graph_neighbors = {}
        self.synonyms = {}
        self.term_list = []
        self.index = None
        self.model = None
        
        self._load_resources()

    def _load_resources(self):
        if os.path.exists(self.ontology_path):
            try:
                with open(self.ontology_path, 'r') as f:
                    data = json.load(f)
                    self.graph_neighbors = data.get("graph_neighbors", {})
                    self.synonyms = data.get("synonyms", {})
                    self.term_list = data.get("terms", [])
            except Exception as e:
                print(f"[WARN] Ontology load failed: {e}")

        if os.path.exists(self.index_path):
            try:
                self.index = faiss.read_index(self.index_path)
                self.model = SentenceTransformer('all-MiniLM-L6-v2')
            except Exception as e:
                print(f"[WARN] FAISS load failed: {e}")

    def _semantic_search(self, query_term, threshold=0.7):
        if not self.index or not self.model: return None
        vec = self.model.encode([query_term])
        distances, ids = self.index.search(vec, 1)
        if ids[0][0] != -1 and distances[0][0] < threshold:
            return self.term_list[ids[0][0]]
        return None

    def expand_query(self, natural_query: str) -> str:
        words = natural_query.split()
        hints = []
        
        for word in words:
            clean_word = word.strip("?,.!").lower()
            
            # 1. Explicit Synonyms (e.g., "ml" -> "Machine Learning")
            matched_term = None
            if clean_word in self.synonyms:
                matched_term = self.synonyms[clean_word]
                hints.append(f"Synonym: '{word}' implies '{matched_term}'")
            
            # 2. Vector Search (Fuzzy match)
            if not matched_term:
                matched_term = self._semantic_search(word)
            
            # 3. Graph Context (The Robustness Layer)
            # If matched_term is "Machine Learning", we find "Data Scientist"
            if matched_term and matched_term in self.graph_neighbors:
                related = self.graph_neighbors[matched_term]
                # Top 5 related terms (roles or skills)
                top_related = related[:5] 
                hints.append(f"Graph Context: '{matched_term}' is associated with roles/skills: {top_related}")

        if not hints: return ""
        return "\n[SEMANTIC HINTS FROM KNOWLEDGE GRAPH]\n" + "\n".join(list(set(hints)))