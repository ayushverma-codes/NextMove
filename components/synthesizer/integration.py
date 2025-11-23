# D:\Projects\NextMove\components\synthesizer\integration.py

import difflib
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any

class ResultIntegrator:
    def __init__(self, threshold: float = 0.85):
        self.threshold = threshold
        # Weights for scoring
        self.WEIGHT_TITLE_MATCH = 3.0
        self.WEIGHT_SKILL_MATCH = 2.0
        self.WEIGHT_DESC_MATCH = 1.0
        self.WEIGHT_RECENCY = 1.5

    # ==========================================
    # 1. DEDUPLICATION LOGIC (Entity Resolution)
    # ==========================================
    def _normalize_text(self, text: str) -> str:
        if not text: return ""
        return str(text).lower().strip()

    def _is_match(self, job_a: Dict, job_b: Dict) -> bool:
        """
        Determines if two jobs are the same entity based on Title and Company.
        Uses Week-5 String Matching concepts.
        """
        title_a = self._normalize_text(job_a.get('title'))
        title_b = self._normalize_text(job_b.get('title'))
        comp_a = self._normalize_text(job_a.get('company_name'))
        comp_b = self._normalize_text(job_b.get('company_name'))

        # 1. Exact Match Check (Fastest blocking strategy)
        if title_a == title_b and comp_a == comp_b:
            return True

        # 2. Fuzzy Match (Sequence Matching)
        # Only perform fuzzy check if companies are very similar
        comp_sim = difflib.SequenceMatcher(None, comp_a, comp_b).ratio()
        if comp_sim < 0.8: # High threshold for company name
            return False
            
        title_sim = difflib.SequenceMatcher(None, title_a, title_b).ratio()
        return title_sim >= self.threshold

    def _merge_jobs(self, existing_job: Dict, new_job: Dict) -> Dict:
        """
        Data Fusion: Merges attributes. Prioritizes non-empty values.
        """
        # Use the existing job as base
        merged = existing_job.copy()
        
        # If existing lacks salary but new has it, take it
        if not existing_job.get('salary_range') and new_job.get('salary_range'):
            merged['salary_range'] = new_job['salary_range']
            
        # Append source tag
        if '_source' in existing_job and '_source' in new_job:
            if new_job['_source'] not in existing_job['_source']:
                merged['_source'] = f"{existing_job['_source']}, {new_job['_source']}"
        
        return merged

    # ==========================================
    # 2. RANKING LOGIC (Context & Scoring)
    # ==========================================
    def _calculate_date_score(self, date_str: str) -> float:
        """
        Calculates a score (0.0 to 1.0) based on recency.
        """
        if not date_str: return 0.0
        try:
            # Handle common SQL date formats
            # Assuming YYYY-MM-DD or DATETIME format from SQL
            if isinstance(date_str, str):
                # Simple parsing logic - extend based on your actual DB format
                if "T" in date_str: date_obj = datetime.fromisoformat(date_str)
                else: date_obj = datetime.strptime(str(date_str)[:10], "%Y-%m-%d")
            else:
                date_obj = date_str # It might already be a datetime object

            days_old = (datetime.now() - date_obj).days
            if days_old < 0: days_old = 0
            
            # Decay function: 1 / (days + 1)
            return 1.0 / (days_old + 1)
        except:
            return 0.0

    def _calculate_text_score(self, text: str, keywords: List[str]) -> float:
        """
        Calculates term overlap score.
        """
        if not text: return 0.0
        text_lower = text.lower()
        score = 0.0
        for kw in keywords:
            # Exact word match logic
            if re.search(r'\b' + re.escape(kw) + r'\b', text_lower):
                score += 1.0
        return score

    def _score_job(self, job: Dict, intent_keywords: List[str]) -> float:
        """
        Computes composite relevance score.
        """
        # 1. Semantic/Keyword Scores
        score_title = self._calculate_text_score(job.get('title', ''), intent_keywords)
        score_skills = self._calculate_text_score(job.get('skills', ''), intent_keywords)
        score_desc = self._calculate_text_score(job.get('description', ''), intent_keywords)
        
        semantic_score = (
            (score_title * self.WEIGHT_TITLE_MATCH) +
            (score_skills * self.WEIGHT_SKILL_MATCH) +
            (score_desc * self.WEIGHT_DESC_MATCH)
        )

        # 2. Recency Score
        recency_score = self._calculate_date_score(job.get('job_posting_date'))
        
        # Total Score
        return semantic_score + (recency_score * self.WEIGHT_RECENCY)

    def integrate_and_rank(self, results_dict: Dict[str, List[Dict]], user_intent: str, limit: int = 10) -> List[Dict]:
        """
        Main Entry Point: Deduplicates, Ranks, and returns Top-K.
        """
        # 1. Extract Keywords from Intent (Simple Tokenization)
        # In a more advanced version, use TermNormalizer here
        intent_keywords = [w.lower() for w in user_intent.split() if len(w) > 3]

        merged_list = []
        seen_jobs = [] # List of dicts

        # --- Step 1: Deduplicate ---
        for source, jobs in results_dict.items():
            if not isinstance(jobs, list): continue
            
            for job in jobs:
                job['_source'] = source # Tag source
                is_duplicate = False
                
                for i, existing_job in enumerate(seen_jobs):
                    if self._is_match(job, existing_job):
                        # Merge Data
                        seen_jobs[i] = self._merge_jobs(existing_job, job)
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    seen_jobs.append(job)

        # --- Step 2: Rank ---
        ranked_jobs = []
        for job in seen_jobs:
            relevance = self._score_job(job, intent_keywords)
            job['_relevance_score'] = relevance
            ranked_jobs.append(job)

        # Sort by relevance desc
        ranked_jobs.sort(key=lambda x: x['_relevance_score'], reverse=True)

        # --- Step 3: Top K ---
        return ranked_jobs[:limit]