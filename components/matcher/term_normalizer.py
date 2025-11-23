import json
import os
import faiss
import re
from sentence_transformers import SentenceTransformer

class TermNormalizer:
    def __init__(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.ontology_path = os.path.join(base_dir, 'workspace_folder', 'artifacts', 'ontology.json')
        self.index_path = os.path.join(base_dir, 'workspace_folder', 'artifacts', 'skills.index')
        
        self.graph_neighbors = {}
        self.synonyms = {}
        self.term_list = []
        self.term_types = {} # New: mapping term -> type
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
                    self.term_types = data.get("term_types", {})
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

    def _get_experience_hint(self, word):
        """Rule-based matching for Experience (The 'How Much')"""
        word_lower = word.lower()
        rules = {
            "fresher": "0-1 years",
            "graduate": "0-1 years",
            "entry": "0-2 years",
            "junior": "1-3 years",
            "senior": "5+ years",
            "lead": "8+ years",
            "intern": "0 years"
        }
        for key, val in rules.items():
            if key in word_lower:
                return f"Experience Context: '{word}' implies '{val}'"
        return None

    def expand_query(self, natural_query: str) -> str:
        words = natural_query.split()
        hints = []
        
        for word in words:
            clean_word = word.strip("?,.!").lower()
            
            # 1. Check Experience Rules (Rule Based)
            exp_hint = self._get_experience_hint(clean_word)
            if exp_hint:
                hints.append(exp_hint)
                continue

            # 2. Check Synonyms (Exact Match)
            matched_term = None
            if clean_word in self.synonyms:
                matched_term = self.synonyms[clean_word]
                hints.append(f"Synonym: '{word}' implies '{matched_term}'")
            
            # 3. Vector Search (Fuzzy Match)
            if not matched_term:
                matched_term = self._semantic_search(word)
            
            # 4. Context Generation (Type Aware)
            if matched_term:
                # Identify Type (Location vs Role vs Company)
                t_type = self.term_types.get(matched_term, "entity")
                
                if t_type == "location":
                    hints.append(f"Location Context: '{word}' refers to city '{matched_term}'")
                elif t_type == "company":
                    hints.append(f"Company Context: '{word}' refers to '{matched_term}'")
                elif t_type in ["role", "skill"]:
                    # Look for graph neighbors (only for roles/skills)
                    if matched_term in self.graph_neighbors:
                        related = self.graph_neighbors[matched_term][:4]
                        hints.append(f"Graph Context: '{matched_term}' is associated with: {related}")

        if not hints: return ""
        return "\n[SEMANTIC HINTS FROM KNOWLEDGE GRAPH]\n" + "\n".join(list(set(hints)))