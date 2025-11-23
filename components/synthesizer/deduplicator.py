import difflib

class ResultDeduplicator:
    def __init__(self, threshold=0.85):
        self.threshold = threshold

    def _is_match(self, job_a, job_b):
        """
        Week 5: String Matching.
        Compares Title AND Company to decide if two jobs are the same.
        """
        # 1. Normalize
        title_a = str(job_a.get('title', '')).lower().strip()
        title_b = str(job_b.get('title', '')).lower().strip()
        comp_a = str(job_a.get('company_name', '')).lower().strip()
        comp_b = str(job_b.get('company_name', '')).lower().strip()

        # 2. Exact Match Check (Fastest)
        if title_a == title_b and comp_a == comp_b:
            return True

        # 3. Fuzzy Match (SequenceMatcher ~ Jaro-Winkler logic)
        # We require HIGH similarity on Title AND Company
        title_sim = difflib.SequenceMatcher(None, title_a, title_b).ratio()
        if title_sim < self.threshold:
            return False
            
        comp_sim = difflib.SequenceMatcher(None, comp_a, comp_b).ratio()
        return comp_sim >= self.threshold

    def deduplicate(self, results_dict):
        """
        Merges results from multiple sources (Linkedin, Naukri).
        """
        merged_list = []
        seen_jobs = [] # List of jobs already added

        for source, jobs in results_dict.items():
            if not isinstance(jobs, list): continue
            
            for job in jobs:
                is_duplicate = False
                for existing_job in seen_jobs:
                    if self._is_match(job, existing_job):
                        is_duplicate = True
                        # Optional: Merge attributes (e.g., if one has salary and other doesn't)
                        # Week 2: Data Fusion
                        if not existing_job.get('salary_range') and job.get('salary_range'):
                            existing_job['salary_range'] = job['salary_range']
                        break
                
                if not is_duplicate:
                    # Add source tag for provenance
                    job['_source'] = source 
                    merged_list.append(job)
                    seen_jobs.append(job)

        return merged_list