import sys
import os
import json
import time
import pandas as pd
import numpy as np
from tqdm import tqdm  # For progress bar

# --- PATH SETUP ---
# Add project root to path so we can import 'pipelines' and 'components'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pipelines.run_pipeline import run_pipeline
from components.LLM.llm_loader import load_llm
from langchain_core.messages import HumanMessage

# --- CONFIGURATION ---
OUTPUT_FILE = "evaluation/experiment_results.csv"
TEST_DATA_FILE = "evaluation/test_queries.json"

# Load Judge LLM (Use Gemini for consistent reasoning)
judge_llm = load_llm("gemini", temperature=0.0)

def calculate_ndcg(relevance_scores, k=5):
    """Calculates Normalized Discounted Cumulative Gain."""
    # FIX: Replace np.asfarray with np.asarray(..., dtype=float)
    relevance_scores = np.asarray(relevance_scores, dtype=float)[:k]
    
    if relevance_scores.size == 0: return 0.0
    
    dcg = np.sum((2 ** relevance_scores - 1) / np.log2(np.arange(2, relevance_scores.size + 2)))
    
    # Sort for Ideal DCG
    ideal_relevance = sorted(relevance_scores, reverse=True)
    # FIX: Replace np.asfarray here too
    ideal_relevance_array = np.asarray(ideal_relevance, dtype=float)
    
    idcg = np.sum((2 ** ideal_relevance_array - 1) / np.log2(np.arange(2, len(ideal_relevance) + 2)))
    
    return dcg / idcg if idcg > 0 else 0.0

def llm_judge_relevance(query, job_title, job_company, job_skills):
    """
    Uses LLM to rate relevance from 1-5.
    This acts as the 'Ground Truth' judge for your research paper.
    """
    prompt = f"""
    Task: Rate the relevance of a job result to a user search query.
    
    User Query: "{query}"
    
    Job Result:
    - Title: {job_title}
    - Company: {job_company}
    - Skills: {job_skills}
    
    On a scale of 1 to 5:
    5: Perfect match (Exact role and intent)
    4: Good match (Related role/seniority)
    3: Acceptable (Broadly relevant domain)
    2: Poor match (Wrong role or seniority)
    1: Irrelevant (Completely unrelated)
    
    OUTPUT ONLY THE INTEGER NUMBER (1-5).
    """
    try:
        res = judge_llm.invoke([HumanMessage(content=prompt)])
        # Extract number from response
        score = int(''.join(filter(str.isdigit, res.content)))
        return min(max(score, 1), 5)
    except:
        return 1 # Default to irrelevant on error

def run_evaluation():
    # 1. Load Queries
    if not os.path.exists(TEST_DATA_FILE):
        print(f"❌ Error: {TEST_DATA_FILE} not found.")
        return

    with open(TEST_DATA_FILE, 'r') as f:
        test_cases = json.load(f)

    results = []
    print(f"🚀 Starting Evaluation on {len(test_cases)} queries...\n")

    # 2. Run Loop with Progress Bar
    for case in tqdm(test_cases, desc="Processing Queries"):
        query = case['query']
        q_type = case['type']
        
        start_time = time.time()
        try:
            # --- RUN THE SYSTEM ---
            # We use debug_mode=True to inspect the DB results directly
            pipeline_out = run_pipeline(query, debug_mode=True, use_history=False)
            latency = time.time() - start_time
            
            # Extract internal data
            debug_info = pipeline_out.get("debug_info", {})
            db_results = debug_info.get("3_database_results", {})
            
            # Check if SQL was generated successfully
            analysis = debug_info.get("1_query_analysis", {})
            sql_generated = bool(analysis.get("sql_query"))
            
            # Check jobs found
            final_jobs = db_results.get("Top_Ranked_Jobs", [])
            jobs_count = len(final_jobs)
            
            # --- CALCULATE METRICS ---
            relevance_scores = []
            if jobs_count > 0:
                # Only judge top 5 to save time/cost
                for job in final_jobs[:5]:
                    score = llm_judge_relevance(
                        query, 
                        job.get('title', ''), 
                        job.get('company_name', ''), 
                        job.get('skills', '')
                    )
                    relevance_scores.append(score)
            
            ndcg_score = calculate_ndcg(relevance_scores, k=5)
            avg_relevance = np.mean(relevance_scores) if relevance_scores else 0

            # Log Result
            results.append({
                "ID": case['id'],
                "Type": q_type,
                "Query": query,
                "Latency(s)": round(latency, 2),
                "SQL_Gen": sql_generated,
                "Jobs_Found": jobs_count,
                "NDCG@5": round(ndcg_score, 3),
                "Avg_Relevance": round(avg_relevance, 2)
            })

        except Exception as e:
            print(f"\n⚠️ Error on query '{query}': {e}")
            results.append({
                "ID": case['id'],
                "Type": q_type,
                "Query": query,
                "Latency(s)": 0,
                "SQL_Gen": False,
                "Jobs_Found": 0,
                "NDCG@5": 0.0,
                "Avg_Relevance": 0.0,
                "Error": str(e)
            })

    # 3. Save & Summary
    df = pd.DataFrame(results)
    df.to_csv(OUTPUT_FILE, index=False)
    
    print(f"\n✅ Evaluation Complete. Results saved to {OUTPUT_FILE}")
    
    # Print Category-wise breakdown for the Paper
    if not df.empty:
        print("\n=== 📊 Research Results Summary ===")
        summary = df.groupby("Type")[["Latency(s)", "NDCG@5", "Jobs_Found"]].mean()
        print(summary)

if __name__ == "__main__":
    run_evaluation()