# D:\Projects\NextMove\pipelines\run_pipeline.py

import json
import copy # <--- ADDED IMPORT
from typing import Dict, Any
from components.analyzer_and_decomposer.query_analyzer import query_analyze
from pipelines.query_decomposer_test_pipeline import decompose_single_query
from components.connectors.mysql_connector import MySQLConnector
from components.synthesizer.result_synthesizer import synthesize_results
from components.history_manager.history_handler import HistoryHandler
from components.learner.graph_learner import GraphLearner 
from components.synthesizer.integration import ResultIntegrator 

from entities.config import (
    LINKEDIN_DB_HOST, LINKEDIN_DB_USER, LINKEDIN_DB_PASSWORD, LINKEDIN_DB_NAME,
    NAUKRI_DB_HOST, NAUKRI_DB_USER, NAUKRI_DB_PASSWORD, NAUKRI_DB_NAME
)

DB_CONNECTION_TIMEOUT = 3

def run_pipeline(
    natural_language_query: str, 
    debug_mode: bool = False,
    use_history: bool = False,
    session_id: str = "default_session"
) -> Dict[str, Any]:
    """
    Executes the full NextMove pipeline with Integration, Ranking, and Active Learning.
    """
    print(f"=== NextMove Pipeline Started (Session: {session_id}) ===\n")

    # --- 0. Context Management ---
    chat_context = ""
    history_handler = None

    if use_history:
        print("[INFO] History Aware Mode: ON. Loading context...")
        try:
            history_handler = HistoryHandler(session_id=session_id)
            chat_context = history_handler.get_context_string()
        except Exception as e:
            print(f"[WARN] Failed to load history: {e}. Proceeding without context.")
    else:
        print("[INFO] History Aware Mode: OFF.")

    # --- Step 1: Analyze Query ---
    print("[STEP 1] Analyzing query...")
    analyzed_result = query_analyze(natural_language_query, chat_history_context=chat_context)
    
    if analyzed_result is None:
        return {
            "final_answer": "I'm sorry, I wasn't able to understand your query.",
            "debug_info": {"error": "Query analysis failed"}
        }

    user_intent = analyzed_result.get("user_intent", natural_language_query)
    unstructured_query = analyzed_result.get("unstructured_query", "")
    global_sql = analyzed_result.get("sql_query")

    print(f"   > Resolved Intent: {user_intent}")

    federated_queries = {}
    db_results = {}
    
    # --- Step 2 & 3: Decompose & Execute ---
    if global_sql:
        print("\n[INFO] SQL query found. Running decomposition and execution...")
        
        # Step 2: Decomposition
        print("\n[STEP 2] Decomposing analyzed query...")
        federated_queries = decompose_single_query(analyzed_result)
        structured_queries = federated_queries.get("structured", {})

        # Step 3: Execution
        print("\n[STEP 3] Executing structured queries on data sources...\n")

        def run_mysql(host, user, pwd, db, sql, source):
            if not sql: return "No query generated."
            try:
                conn = MySQLConnector(host, user, pwd, db, timeout=DB_CONNECTION_TIMEOUT)
                conn.connect()
                rows = conn.execute_query_as_dict(sql)
                conn.disconnect()
                return rows
            except Exception as e:
                # We return a dict with 'error' key to track failures per source
                return {"error": f"Failed: {e}"}

        db_results["Linkedin_source"] = run_mysql(
            LINKEDIN_DB_HOST, LINKEDIN_DB_USER, LINKEDIN_DB_PASSWORD, LINKEDIN_DB_NAME,
            structured_queries.get("Linkedin_source"), "Linkedin"
        )
        
        db_results["Naukri_source"] = run_mysql(
            NAUKRI_DB_HOST, NAUKRI_DB_USER, NAUKRI_DB_PASSWORD, NAUKRI_DB_NAME,
            structured_queries.get("Naukri_source"), "Naukri"
        )

        # --- CAPTURE RAW DATA FOR DEBUGGING ---
        # Make a deep copy before Integration overwrites it
        raw_db_debug = copy.deepcopy(db_results)
        # --------------------------------------

        # --- STEP 3.5: Integration & Ranking (Updated for Robustness) ---
        print("[INFO] Integrating and Ranking results...")
        try:
            integrator = ResultIntegrator()
            
            # 1. Isolate valid job lists (ignore errors for calculation)
            valid_job_lists = {k: v for k, v in db_results.items() if isinstance(v, list)}
            
            # 2. Determine Limit
            limit = analyzed_result.get("limit", 10)
            
            # 3. Run Integration Logic
            if valid_job_lists:
                top_k_jobs = integrator.integrate_and_rank(
                    results_dict=valid_job_lists,
                    user_intent=user_intent,
                    limit=limit
                )
            else:
                top_k_jobs = []

            # 4. ROBUST OUTPUT CONSTRUCTION
            # If we found jobs, we ONLY send the jobs to the LLM.
            # We suppress errors from specific sources so the LLM focuses on the data we found.
            if top_k_jobs:
                print(f"[INFO] Success: Found {len(top_k_jobs)} jobs. Suppressing partial errors.")
                db_results = {"Top_Ranked_Jobs": top_k_jobs}
            else:
                # [FIX] Keep BOTH errors and empty lists so we can see Naukri's status
                print("[WARN] No jobs found. Some sources failed, others returned 0.") 
                errors = {k: v for k, v in db_results.items() if isinstance(v, dict) and "error" in v}
                empty_successes = {k: v for k, v in db_results.items() if isinstance(v, list) and not v}
                
                db_results = {**errors, **empty_successes}
                
                if errors:
                    print("[WARN] No jobs found due to DB errors.")
                    db_results = errors # Pass errors to LLM
                else:
                    print("[INFO] Query ran successfully but returned 0 results.")
                    db_results = {"Top_Ranked_Jobs": []} # Empty list implies valid search, just no matches

        except Exception as e:
            print(f"[WARN] Integration/Ranking failed: {e}. Using raw results.")
            # In a catastrophic integration fail, we fall back to whatever db_results we had
    
        # ------------------------------------------------

        # --- PHASE 2: ACTIVE LEARNING ---
        try:
            # Fire the learner to update the graph based on what we found
            learner = GraphLearner()
            # We pass the raw db_results or integrated ones; learner handles format check
            learner.learn_from_results(user_intent, db_results)
        except Exception as e:
            print(f"[WARN] Learning step skipped: {e}")
        # --------------------------------------

    else:
        print("\n[INFO] No SQL query detected. Bypassing Steps 2 & 3.")
        federated_queries = {"info": "Bypassed: General knowledge query."}
        db_results = {"info": "Bypassed: No SQL executed."}
        raw_db_debug = {"info": "No SQL executed"} # Default for debug

    # --- Step 4: Synthesize ---
    print("[STEP 4] Synthesizing final answer...")
    synthesis_response = synthesize_results(
        natural_language_query=natural_language_query,
        unstructured_query=unstructured_query,
        database_results=db_results,
        user_intent=user_intent
    )
    
    final_answer = synthesis_response["final_answer"]
    final_llm_prompts = synthesis_response["prompts_used"]

    # --- Step 5: History Update ---
    if use_history and history_handler:
        try:
            history_handler.add_interaction(natural_language_query, final_answer)
        except Exception as e:
            print(f"[ERROR] Failed to save history: {e}")

    print("\n=== Pipeline Completed ===")
    
    # Return Final Answer & Debug Info
    if debug_mode:
        return {
            "final_answer": final_answer,
            "debug_info": {
                "session_id": session_id,
                "0_history_context": chat_context,
                "1_query_analysis": analyzed_result,
                "2_query_decomposition": federated_queries,
                # --- NEW: Added RAW vs INTEGRATED Results ---
                "3a_RAW_db_results": raw_db_debug if 'raw_db_debug' in locals() else "No SQL",
                "3b_INTEGRATED_results": db_results,
                # --------------------------------------------
                "4_final_llm_prompts": final_llm_prompts
            }
        }
    else:
        return {
            "final_answer": final_answer,
            "debug_info": None
        }