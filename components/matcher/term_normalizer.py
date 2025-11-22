# components/matcher/term_normalizer.py
import json
import os
import difflib

class TermNormalizer:
    def __init__(self):
        self.ontology_path = os.path.join(os.path.dirname(__file__), '../../entities/ontology.json')
        self.graph_neighbors = {}
        self.synonyms = {}
        self._load_ontology()

    def _load_ontology(self):
        if os.path.exists(self.ontology_path):
            try:
                with open(self.ontology_path, 'r') as f:
                    data = json.load(f)
                    self.graph_neighbors = data.get("graph_neighbors", {})
                    self.synonyms = data.get("synonyms", {})
            except Exception as e:
                print(f"[WARN] Ontology load failed: {e}")
        else:
            print("[WARN] Ontology file not found. Please run scripts/generate_ontology.py")

    def _fuzzy_match(self, term, corpus, threshold=0.8):
        """
        Week 5: String Matching. Uses SequenceMatcher (Ratcliff-Obershelp similar logic)
        to find the closest term in our known vocabulary if exact match fails.
        """
        matches = difflib.get_close_matches(term, corpus, n=1, cutoff=threshold)
        return matches[0] if matches else None

    def expand_query(self, natural_query: str) -> str:
        """
        Analyzes the user query and returns a 'Hint String' with 
        synonyms and implicit skills.
        """
        words = natural_query.split()
        hints = []
        
        # Combine all known keys for fuzzy matching
        all_known_terms = list(self.graph_neighbors.keys()) + list(self.synonyms.keys())
        
        for word in words:
            # 1. Normalization & Typo Correction
            clean_word = word.strip("?,.!").lower()
            
            # Try to match case-insensitive first
            matched_term = None
            for known in all_known_terms:
                if known.lower() == clean_word:
                    matched_term = known
                    break
            
            # If no exact match, try fuzzy
            if not matched_term:
                matched_term = self._fuzzy_match(clean_word, all_known_terms)

            if matched_term:
                # 2. Synonym Expansion (Vocabulary Mismatch Problem)
                if matched_term in self.synonyms:
                    syn = self.synonyms[matched_term]
                    hints.append(f"Synonym: '{word}' implies '{syn}'")
                
                # 3. Implicit Skill Inference (Graph Traversal)
                if matched_term in self.graph_neighbors:
                    related = self.graph_neighbors[matched_term]
                    # Limit to top 3 related skills to avoid prompt bloat
                    top_related = related[:3] 
                    hints.append(f"Implicit Context: '{matched_term}' relates to {top_related}")

        if not hints:
            return ""
            
        return "\n[SEMANTIC HINTS FROM KNOWLEDGE GRAPH]\n" + "\n".join(hints)