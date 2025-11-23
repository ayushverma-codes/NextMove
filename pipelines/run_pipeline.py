import json
from typing import Dict, Any
from components.analyzer_and_decomposer.query_analyzer import query_analyze
from pipelines.query_decomposer_test_pipeline import decompose_single_query
from components.connectors.mysql_connector import MySQLConnector
from components.synthesizer.result_synthesizer import synthesize_results
from components.history_manager.history_handler import HistoryHandler
from components.learner.graph_learner import GraphLearner # <--- NEW IMPORT

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
    Executes the full NextMove pipeline with Active Learning.
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
                return {"error": f"Failed: {e}"}

        db_results["Linkedin_source"] = run_mysql(
            LINKEDIN_DB_HOST, LINKEDIN_DB_USER, LINKEDIN_DB_PASSWORD, LINKEDIN_DB_NAME,
            structured_queries.get("Linkedin_source"), "Linkedin"
        )
        db_results["Naukri_source"] = run_mysql(
            NAUKRI_DB_HOST, NAUKRI_DB_USER, NAUKRI_DB_PASSWORD, NAUKRI_DB_NAME,
            structured_queries.get("Naukri_source"), "Naukri"
        )

        # --- PHASE 2: ACTIVE LEARNING (NEW) ---
        try:
            # Fire the learner to update the graph based on what we found
            learner = GraphLearner()
            learner.learn_from_results(user_intent, db_results)
        except Exception as e:
            print(f"[WARN] Learning step skipped: {e}")
        # --------------------------------------

    else:
        print("\n[INFO] No SQL query detected. Bypassing Steps 2 & 3.")
        federated_queries = {"info": "Bypassed: General knowledge query."}
        db_results = {"info": "Bypassed: No SQL executed."}

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
                "3_database_results": db_results,
                "4_final_llm_prompts": final_llm_prompts
            }
        }
    else:
        return {
            "final_answer": final_answer,
            "debug_info": None
        }