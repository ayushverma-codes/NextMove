import json
# Ensure we import the analyzer directly to pass the context argument
from components.analyzer_and_decomposer.query_analyzer import query_analyze
from pipelines.query_decomposer_test_pipeline import decompose_single_query
from components.connectors.mysql_connector import MySQLConnector
from components.synthesizer.result_synthesizer import synthesize_results
# Import History Handler
from components.history_manager.history_handler import HistoryHandler

from entities.config import (
    LINKEDIN_DB_HOST, LINKEDIN_DB_USER, LINKEDIN_DB_PASSWORD, LINKEDIN_DB_NAME,
    NAUKRI_DB_HOST, NAUKRI_DB_USER, NAUKRI_DB_PASSWORD, NAUKRI_DB_NAME
)
from typing import Dict, Any

DB_CONNECTION_TIMEOUT = 3 # 3 seconds


def run_pipeline(
    natural_language_query: str, 
    debug_mode: bool = False,
    use_history: bool = False
) -> Dict[str, Any]:
    """
    Executes the full NextMove pipeline and returns a structured dictionary.
    Supports History Awareness and Debug Mode.
    """
    print("=== NextMove Pipeline Started ===\n")

    # --- 0. Context Management ---
    chat_context = ""
    history_handler = None

    if use_history:
        print("[INFO] History Aware Mode: ON. Loading context...")
        try:
            history_handler = HistoryHandler()
            chat_context = history_handler.get_context_string()
        except Exception as e:
            print(f"[WARN] Failed to load history: {e}. Proceeding without context.")
    else:
        print("[INFO] History Aware Mode: OFF.")

    # Step 1: Analyze Query
    print("[STEP 1] Analyzing query...")
    
    # Pass the context (it will be empty if use_history is False)
    analyzed_result = query_analyze(natural_language_query, chat_history_context=chat_context)
    
    if analyzed_result is None:
        print("[ERROR] Failed to analyze query. Pipeline aborted.")
        return {
            "final_answer": "I'm sorry, I wasn't able to understand your query. Could you please rephrase it?",
            "debug_info": {"error": "Query analysis failed"}
        }

    unstructured_query = analyzed_result.get("unstructured_query", "")
    global_sql = analyzed_result.get("sql_query")

    federated_queries = {}
    db_results = {}
    
    if global_sql:
        print("\n[INFO] SQL query found. Running decomposition and execution...")
        
        # Step 2: Decompose Query
        print("\n[STEP 2] Decomposing analyzed query...")
        federated_queries = decompose_single_query(analyzed_result)
        structured_queries = federated_queries.get("structured", {})

        # Step 3: Execute Structured Queries
        print("\n[STEP 3] Executing structured queries on data sources...\n")

        # 🔹 MySQL: Linkedin_source
        linkedin_sql = structured_queries.get("Linkedin_source")
        if linkedin_sql:
            print("[MySQL] Running query on Linkedin_source:")
            print(linkedin_sql)
            try:
                mysql_linkedin = MySQLConnector(
                    host=LINKEDIN_DB_HOST,
                    user=LINKEDIN_DB_USER,
                    password=LINKEDIN_DB_PASSWORD,
                    database=LINKEDIN_DB_NAME,
                    timeout=DB_CONNECTION_TIMEOUT
                )
                mysql_linkedin.connect()
                rows = mysql_linkedin.execute_query_as_dict(linkedin_sql)
                mysql_linkedin.disconnect()
                print(f"[INFO] Retrieved {len(rows)} rows from Linkedin_source.\n")
                db_results["Linkedin_source"] = rows
            except Exception as e:
                print(f"[ERROR] Linkedin_source query failed: {e}\n")
                db_results["Linkedin_source"] = {"error": f"Failed to connect or query: {e}"}
        else:
            print("[WARN] No SQL generated for Linkedin_source\n")
            db_results["Linkedin_source"] = "No query generated."

        # 🔹 MySQL: Naukri_source
        naukri_sql = structured_queries.get("Naukri_source")
        if naukri_sql:
            print("[MySQL] Running query on Naukri_source:")
            print(naukri_sql)
            try:
                mysql_naukri = MySQLConnector(
                    host=NAUKRI_DB_HOST,
                    user=NAUKRI_DB_USER,
                    password=NAUKRI_DB_PASSWORD,
                    database=NAUKRI_DB_NAME,
                    timeout=DB_CONNECTION_TIMEOUT
                )
                mysql_naukri.connect()
                rows = mysql_naukri.execute_query_as_dict(naukri_sql)
                mysql_naukri.disconnect()
                print(f"[INFO] Retrieved {len(rows)} rows from Naukri_source.\n")
                db_results["Naukri_source"] = rows
            except Exception as e:
                print(f"[ERROR] Naukri_source query failed: {e}\n")
                db_results["Naukri_source"] = {"error": f"Failed to connect or query: {e}"}
        else:
            print("[WARN] No SQL generated for Naukri_source\n")
            db_results["Naukri_source"] = "No query generated."

    else:
        print("\n[INFO] No SQL query detected. Bypassing Steps 2 & 3.")
        federated_queries = {"info": "Bypassed: No SQL query from analyzer."}
        db_results = {"info": "Bypassed: No SQL query to execute."}


    # Step 4: Synthesize Results
    synthesis_response = synthesize_results(
        natural_language_query=natural_language_query,
        unstructured_query=unstructured_query,
        database_results=db_results
    )
    final_answer = synthesis_response["final_answer"]
    final_llm_prompts = synthesis_response["prompts_used"]

    # --- Step 5: Update History (Conditional) ---
    if use_history and history_handler:
        print("[STEP 5] Updating Persistent History...")
        try:
            history_handler.add_interaction(natural_language_query, final_answer)
        except Exception as e:
            print(f"[ERROR] Failed to save history: {e}")

    print("\n=== Pipeline Completed ===")
    
    # Construct the final response dictionary
    if debug_mode:
        return {
            "final_answer": final_answer,
            "debug_info": {
                "mode_settings": {"use_history": use_history},
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