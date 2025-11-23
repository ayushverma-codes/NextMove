# D:\Projects\NextMove\components\synthesizer\integration.py

import difflib
import re
from datetime import datetime
from typing import List, Dict, Any, Set
from components.matcher.term_normalizer import TermNormalizer

class ResultIntegrator:
    def __init__(self, threshold: float = 0.85):
        self.threshold = threshold
        self.normalizer = TermNormalizer()
        
        # --- WEIGHTS (Tuned for better ranking) ---
        self.WEIGHT_COMPANY_MATCH = 4.0  # High priority: If user asks for "Google", show Google jobs first
        self.WEIGHT_TITLE_MATCH = 3.0
        self.WEIGHT_SKILL_MATCH = 2.0
        self.WEIGHT_DESC_MATCH = 1.0
        self.WEIGHT_RECENCY = 1.5
        self.WEIGHT_SEMANTIC_BONUS = 0.5

        # Stopwords to ignore in scoring (Noise reduction)
        self.STOPWORDS = {
            "are", "there", "any", "jobs", "available", "at", "in", "for", 
            "opening", "role", "position", "work", "vacancy", "hiring", "job"
        }

    # ==========================================
    # 1. DEDUPLICATION LOGIC (Entity Resolution)
    # ==========================================
    def _normalize_text(self, text: Any) -> str:
        """Safe normalization handling None types."""
        if not text: return ""
        return str(text).lower().strip()

    def _normalize_company(self, text: Any) -> str:
        """
        Week 5 Concept: Normalization.
        Removes legal suffixes to improve matching (e.g., 'Flipkart Pvt Ltd' -> 'flipkart')
        """
        s = self._normalize_text(text)
        # Remove common suffixes
        s = re.sub(r'\b(pvt|ltd|inc|corp|llc|private|limited)\b', '', s)
        return s.strip()

    def _is_synonym(self, term_a: str, term_b: str) -> bool:
        """Checks if two terms are synonyms using the Knowledge Graph."""
        if self.normalizer.synonyms.get(term_a) == term_b: return True
        if self.normalizer.synonyms.get(term_b) == term_a: return True
        return False

    def _is_match(self, job_a: Dict, job_b: Dict) -> bool:
        """
        Determines if two jobs are the same entity.
        """
        title_a = self._normalize_text(job_a.get('title'))
        title_b = self._normalize_text(job_b.get('title'))
        
        # Use specialized company normalization
        comp_a = self._normalize_company(job_a.get('company_name'))
        comp_b = self._normalize_company(job_b.get('company_name'))

        # 1. Blocking: Companies must match closely
        if not comp_a or not comp_b: return False # Cannot match if company missing
        
        if comp_a == comp_b:
            comp_sim = 1.0
        else:
            comp_sim = difflib.SequenceMatcher(None, comp_a, comp_b).ratio()
        
        if comp_sim < 0.85: 
            return False

        # 2. Title Matching
        if title_a == title_b: return True
        
        # KG Synonym Check
        if self._is_synonym(title_a, title_b):
            return True

        # String Fuzzy Match
        title_sim = difflib.SequenceMatcher(None, title_a, title_b).ratio()
        return title_sim >= self.threshold

    def _merge_jobs(self, existing_job: Dict, new_job: Dict) -> Dict:
        """Data Fusion: Merges attributes."""
        merged = existing_job.copy()
        
        # Prefer longer/more detailed fields
        for field in ['salary_range', 'skills', 'description', 'location']:
            val_exist = str(existing_job.get(field, ''))
            val_new = str(new_job.get(field, ''))
            
            if not val_exist and val_new:
                merged[field] = new_job[field]
            elif len(val_new) > len(val_exist):
                merged[field] = new_job[field]

        # Append source tag
        if '_source' in existing_job and '_source' in new_job:
            if new_job['_source'] not in existing_job['_source']:
                merged['_source'] = f"{existing_job['_source']}, {new_job['_source']}"
        
        return merged

    # ==========================================
    # 2. RANKING LOGIC (Context & Scoring)
    # ==========================================
    def _calculate_date_score(self, date_str: Any) -> float:
        """
        Week 11 Concept: Recency scoring.
        Returns 0.5 (neutral) if date is missing, rather than 0.0 (punishing).
        """
        if not date_str or str(date_str).lower() == 'none': 
            return 0.5 # Default score for missing dates
            
        try:
            if isinstance(date_str, str):
                # Attempt standard formats
                if "T" in date_str: 
                    date_obj = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                else: 
                    date_obj = datetime.strptime(str(date_str)[:10], "%Y-%m-%d")
            elif isinstance(date_str, (datetime, float, int)):
                # Already an object (pandas timestamp or python datetime)
                date_obj = date_str if isinstance(date_str, datetime) else datetime.fromtimestamp(date_str)
            else:
                return 0.5

            # Make naive to avoid timezone errors
            if date_obj.tzinfo:
                date_obj = date_obj.replace(tzinfo=None)
                
            days_old = (datetime.now() - date_obj).days
            if days_old < 0: days_old = 0
            
            # Decay: Today=1.0, 7 days=0.12
            return 1.0 / (days_old + 1)
        except Exception:
            return 0.5

    def _calculate_context_score(self, text: Any, direct_keywords: List[str], semantic_neighbors: List[str]) -> float:
        """Calculates overlap score."""
        if not text: return 0.0
        text_lower = str(text).lower()
        score = 0.0
        
        # 1. Direct Matches
        for kw in direct_keywords:
            # Use word boundary check
            if re.search(r'\b' + re.escape(kw) + r'\b', text_lower):
                score += 1.0
        
        # 2. Semantic Neighbor Matches
        for neighbor in semantic_neighbors:
            if re.search(r'\b' + re.escape(neighbor) + r'\b', text_lower):
                score += self.WEIGHT_SEMANTIC_BONUS
                
        return score

    def _score_job(self, job: Dict, direct_keywords: List[str], semantic_neighbors: List[str]) -> float:
        """
        Computes composite relevance score.
        FIX: Now includes Company Name in the scoring matrix.
        """
        # 1. Calculate Component Scores
        score_company = self._calculate_context_score(job.get('company_name'), direct_keywords, semantic_neighbors)
        score_title = self._calculate_context_score(job.get('title'), direct_keywords, semantic_neighbors)
        score_skills = self._calculate_context_score(job.get('skills') or job.get('skills_desc'), direct_keywords, semantic_neighbors)
        score_desc = self._calculate_context_score(job.get('description'), direct_keywords, semantic_neighbors)
        
        # 2. Weighted Sum
        semantic_score = (
            (score_company * self.WEIGHT_COMPANY_MATCH) +  # <--- ADDED
            (score_title * self.WEIGHT_TITLE_MATCH) +
            (score_skills * self.WEIGHT_SKILL_MATCH) +
            (score_desc * self.WEIGHT_DESC_MATCH)
        )

        # 3. Recency Score
        recency_score = self._calculate_date_score(job.get('job_posting_date'))
        
        return semantic_score + (recency_score * self.WEIGHT_RECENCY)

    def _get_semantic_expansion(self, user_intent: str) -> tuple[List[str], List[str]]:
        """
        Extracts keywords, removing stopwords, and finds KG neighbors.
        """
        # Clean and Tokenize
        raw_words = re.findall(r'\w+', user_intent.lower())
        
        direct_keywords = []
        neighbors = set()

        for word in raw_words:
            # Filter Stopwords and short tokens
            if word in self.STOPWORDS or len(word) < 2:
                continue
                
            direct_keywords.append(word)
            
            # KG Expansion
            if word in self.normalizer.synonyms:
                neighbors.add(self.normalizer.synonyms[word])
            
            word_cap = word.title()
            if word_cap in self.normalizer.graph_neighbors:
                related_terms = self.normalizer.graph_neighbors[word_cap]
                for term in related_terms[:3]:
                    neighbors.add(term.lower())

        return direct_keywords, list(neighbors)

    def integrate_and_rank(self, results_dict: Dict[str, List[Dict]], user_intent: str, limit: int = 10) -> List[Dict]:
        """
        Main Entry Point.
        """
        # 1. Expand Intent
        direct_keywords, semantic_neighbors = self._get_semantic_expansion(user_intent)
        
        merged_list = []
        seen_jobs = [] 

        # --- Step 1: Deduplicate ---
        for source, jobs in results_dict.items():
            if not isinstance(jobs, list): continue
            
            for job in jobs:
                # Safety: ensure job is a dict
                if not isinstance(job, dict): continue
                
                job['_source'] = source 
                is_duplicate = False
                
                for i, existing_job in enumerate(seen_jobs):
                    if self._is_match(job, existing_job):
                        # Merge Data
                        seen_jobs[i] = self._merge_jobs(existing_job, job)
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    seen_jobs.append(job)

        # --- Step 2: Context-Aware Ranking ---
        ranked_jobs = []
        for job in seen_jobs:
            relevance = self._score_job(job, direct_keywords, semantic_neighbors)
            job['_relevance_score'] = round(relevance, 2) # Round for cleaner debug output
            ranked_jobs.append(job)

        # Sort by relevance desc
        ranked_jobs.sort(key=lambda x: x['_relevance_score'], reverse=True)

        return ranked_jobs[:limit]