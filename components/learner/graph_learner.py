import os
import json
from keybert import KeyBERT

class GraphLearner:
    def __init__(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.ontology_path = os.path.join(base_dir, 'workspace_folder', 'artifacts', 'ontology.json')
        self.kw_model = KeyBERT()

    def learn_from_results(self, user_query: str, db_results: dict):
        text_corpus = ""
        for source, data in db_results.items():
            if isinstance(data, list):
                for row in data:
                    text_corpus += f"{row.get('title', '')} {row.get('skills', '')} "

        if len(text_corpus) < 20: return

        try:
            keywords = self.kw_model.extract_keywords(
                text_corpus, keyphrase_ngram_range=(1, 2), stop_words='english', top_n=5
            )
            new_skills = [kw[0] for kw in keywords]
            
            if new_skills:
                self._update_graph(user_query, new_skills)
        except Exception as e:
            print(f"[LEARNER] Error: {e}")

    def _update_graph(self, role, skills):
        if not os.path.exists(self.ontology_path): return
        try:
            with open(self.ontology_path, 'r') as f:
                data = json.load(f)
            
            graph = data.get("graph_neighbors", {})
            # Use Title Case for consistency
            role_key = role.title() 
            
            if role_key not in graph: graph[role_key] = []
            
            updated = False
            for skill in skills:
                skill_key = skill.title()
                if skill_key not in graph[role_key]:
                    graph[role_key].append(skill_key)
                    updated = True
            
            if updated:
                data["graph_neighbors"] = graph
                with open(self.ontology_path, 'w') as f:
                    json.dump(data, f, indent=2)
                print(f"[LEARNER] Learned: {role_key} -> {skills}")
        except:
            pass