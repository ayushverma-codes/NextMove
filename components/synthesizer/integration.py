import difflib
import re
import random
from datetime import datetime
from typing import List, Dict, Any
from components.matcher.term_normalizer import TermNormalizer
from entities.config import GAV_MAPPINGS

class ResultIntegrator:
    def __init__(self, threshold: float = 0.85):
        self.threshold = threshold
        self.normalizer = TermNormalizer()
        
        # --- SCORING WEIGHTS ---
        self.WEIGHT_COMPANY_MATCH = 4.0  
        self.WEIGHT_TITLE_MATCH = 3.0
        self.WEIGHT_SKILL_MATCH = 2.0
        self.WEIGHT_DESC_MATCH = 1.0
        self.WEIGHT_LOCATION_MATCH = 2.0
        self.WEIGHT_RECENCY = 2.5
        self.WEIGHT_SEMANTIC_BONUS = 0.5

        # Stopwords
        self.STOPWORDS = {
            "are", "there", "any", "jobs", "available", "at", "in", "for", 
            "opening", "role", "position", "work", "vacancy", "hiring", "job", 
            "give", "show", "me", "list", "find"
        }

    # ==========================================
    # 0. NORMALIZATION & CLEANING
    # ==========================================
    def _standardize_job(self, raw_job: Dict, source: str) -> Dict:
        """Maps source keys to Global Schema keys."""
        standardized_job = {}
        mapping = GAV_MAPPINGS.get(source, {})

        for global_key, local_key in mapping.items():
            # 1. Try mapped key
            if local_key and local_key in raw_job:
                standardized_job[global_key] = raw_job[local_key]
            # 2. Try direct key match (e.g., from SQL aliases)
            elif global_key in raw_job:
                standardized_job[global_key] = raw_job[global_key]
            else:
                standardized_job[global_key] = None

        standardized_job['_source'] = source
        return standardized_job

    def _prune_job(self, job: Dict) -> Dict:
        """
        Final cleanup: 
        - Removes keys with None/Empty values (Optimization).
        - [MODIFIED] KEEPS internal scoring keys for debugging.
        """
        pruned = {}
        for k, v in job.items():
            # --- DEBUG MODIFICATION START ---
            # We comment this out so we can see the ranking score in the UI
            # if k.startswith("_relevance"):
            #    continue
            # --- DEBUG MODIFICATION END ---
            
            # Remove empty data
            if v is None or v == "" or str(v).lower() == "null":
                continue
                
            pruned[k] = v
        return pruned

    # ==========================================
    # 1. DEDUPLICATION UTILS
    # ==========================================
    def _normalize_text(self, text: Any) -> str:
        if not text: return ""
        return str(text).lower().strip()

    def _normalize_company(self, text: Any) -> str:
        s = self._normalize_text(text)
        s = re.sub(r'\b(pvt|ltd|inc|corp|llc|private|limited)\b', '', s)
        return s.strip()

    def _is_synonym(self, term_a: str, term_b: str) -> bool:
        if self.normalizer.synonyms.get(term_a) == term_b: return True
        if self.normalizer.synonyms.get(term_b) == term_a: return True
        return False

    def _is_match(self, job_a: Dict, job_b: Dict) -> bool:
        """Determines if two jobs are the same entity."""
        title_a = self._normalize_text(job_a.get('title'))
        title_b = self._normalize_text(job_b.get('title'))
        comp_a = self._normalize_company(job_a.get('company_name'))
        comp_b = self._normalize_company(job_b.get('company_name'))

        if not comp_a or not comp_b: return False
        
        # Blocking on Company Name
        if comp_a == comp_b:
            comp_sim = 1.0
        else:
            comp_sim = difflib.SequenceMatcher(None, comp_a, comp_b).ratio()
        
        if comp_sim < 0.85: return False

        # Matching on Title
        if title_a == title_b: return True
        if self._is_synonym(title_a, title_b): return True

        title_sim = difflib.SequenceMatcher(None, title_a, title_b).ratio()
        return title_sim >= self.threshold

    def _merge_jobs(self, existing_job: Dict, new_job: Dict) -> Dict:
        """Merges attributes to create a Golden Record."""
        merged = existing_job.copy()
        
        # Merge strategy: Prefer existing non-empty values, else take new
        fields = [
            'salary_range', 'skills', 'description', 'location', 
            'job_posting_date', 'experience_required', 'work_type'
        ]

        for field in fields:
            val_exist = str(existing_job.get(field, '') or '')
            val_new = str(new_job.get(field, '') or '')

            if (not val_exist or val_exist.lower() == 'none') and (val_new and val_new.lower() != 'none'):
                merged[field] = new_job[field]
            elif len(val_new) > len(val_exist):
                merged[field] = new_job[field]

        # Merge Source Tag
        if '_source' in existing_job and '_source' in new_job:
            if new_job['_source'] not in existing_job['_source']:
                merged['_source'] = f"{existing_job['_source']}, {new_job['_source']}"
        
        return merged

    # ==========================================
    # 2. RANKING LOGIC
    # ==========================================
    def _calculate_date_score(self, date_val: Any) -> float:
        if not date_val or str(date_val).lower() == 'none': return 0.0
        try:
            date_obj = None
            if isinstance(date_val, datetime):
                date_obj = date_val
            elif isinstance(date_val, str):
                date_str = date_val.replace("Z", "").split(".")[0]
                if "T" in date_str: 
                    date_obj = datetime.fromisoformat(date_str)
                else: 
                    try:
                        date_obj = datetime.strptime(date_str[:10], "%Y-%m-%d")
                    except:
                        return 0.5 

            if date_obj:
                if date_obj.tzinfo: date_obj = date_obj.replace(tzinfo=None)
                days_old = (datetime.now() - date_obj).days
                if days_old < 0: days_old = 0
                return 1.0 / (days_old + 1)
                
            return 0.5
        except Exception:
            return 0.5

    def _calculate_context_score(self, text: Any, direct_keywords: List[str], semantic_neighbors: List[str]) -> float:
        if not text: return 0.0
        text_lower = str(text).lower()
        score = 0.0
        
        for kw in direct_keywords:
            matches = len(re.findall(r'\b' + re.escape(kw) + r'\b', text_lower))
            score += min(matches, 3) * 1.0 
        
        for neighbor in semantic_neighbors:
            if re.search(r'\b' + re.escape(neighbor) + r'\b', text_lower):
                score += self.WEIGHT_SEMANTIC_BONUS
        return score

    def _score_job(self, job: Dict, direct_keywords: List[str], semantic_neighbors: List[str]) -> float:
        # 1. Keyword Matching
        s_company = self._calculate_context_score(job.get('company_name'), direct_keywords, semantic_neighbors)
        s_title = self._calculate_context_score(job.get('title'), direct_keywords, semantic_neighbors)
        s_skills = self._calculate_context_score(job.get('skills'), direct_keywords, semantic_neighbors)
        s_desc = self._calculate_context_score(job.get('description'), direct_keywords, semantic_neighbors)
        s_loc = self._calculate_context_score(job.get('location'), direct_keywords, semantic_neighbors)

        semantic_score = (
            (s_company * self.WEIGHT_COMPANY_MATCH) +
            (s_title * self.WEIGHT_TITLE_MATCH) +
            (s_skills * self.WEIGHT_SKILL_MATCH) +
            (s_desc * self.WEIGHT_DESC_MATCH) +
            (s_loc * self.WEIGHT_LOCATION_MATCH)
        )

        # 2. Recency
        recency_score = self._calculate_date_score(job.get('job_posting_date'))
        
        # 3. Completeness
        completeness = 0.0
        if job.get('salary_range'): completeness += 0.2
        if job.get('work_type'): completeness += 0.1

        total = semantic_score + (recency_score * self.WEIGHT_RECENCY) + completeness
        return total + random.uniform(0, 0.01)

    def _get_semantic_expansion(self, user_intent: str) -> tuple[List[str], List[str]]:
        raw_words = re.findall(r'\w+', user_intent.lower())
        direct_keywords = []
        neighbors = set()

        for word in raw_words:
            if word in self.STOPWORDS or len(word) < 2: continue
            direct_keywords.append(word)
            if word in self.normalizer.synonyms:
                neighbors.add(self.normalizer.synonyms[word])
            
            word_cap = word.title()
            if word_cap in self.normalizer.graph_neighbors:
                related_terms = self.normalizer.graph_neighbors[word_cap]
                for term in related_terms[:3]:
                    neighbors.add(term.lower())

        return direct_keywords, list(neighbors)

    # ==========================================
    # MAIN ENTRY POINT
    # ==========================================
    def integrate_and_rank(self, results_dict: Dict[str, List[Dict]], user_intent: str, limit: int = 10) -> List[Dict]:
        direct_keywords, semantic_neighbors = self._get_semantic_expansion(user_intent)
        
        seen_jobs = [] 

        # Step 1: Standardize & Deduplicate
        for source, jobs in results_dict.items():
            if not isinstance(jobs, list): continue
            
            for raw_job in jobs:
                if not isinstance(raw_job, dict): continue
                
                # 1. Standardize Keys
                std_job = self._standardize_job(raw_job, source)
                
                # 2. Deduplicate
                is_duplicate = False
                for i, existing_job in enumerate(seen_jobs):
                    if self._is_match(std_job, existing_job):
                        seen_jobs[i] = self._merge_jobs(existing_job, std_job)
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    seen_jobs.append(std_job)

        # Step 2: Rank
        for job in seen_jobs:
            relevance = self._score_job(job, direct_keywords, semantic_neighbors)
            job['_relevance_score'] = round(relevance, 3)

        # Sort desc
        seen_jobs.sort(key=lambda x: x['_relevance_score'], reverse=True)

        # Step 3: Prune & Limit (Clean up for LLM)
        final_jobs = []
        for job in seen_jobs[:limit]:
            final_jobs.append(self._prune_job(job))

        return final_jobs