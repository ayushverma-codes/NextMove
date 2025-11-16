# D:\Projects\NextMove\pipelines\run_pipeline.py

import json
from pipelines.query_analyzer_test_pipeline import run_single_query
from pipelines.query_decomposer_test_pipeline import decompose_single_query
from components.connectors.mysql_connector import MySQLConnector
# Import the new synthesizer
from components.synthesizer.result_synthesizer import synthesize_results 

# Import the new DB credentials from config
from entities.config import (
    LINKEDIN_DB_HOST, LINKEDIN_DB_USER, LINKEDIN_DB_PASSWORD, LINKEDIN_DB_NAME,
    NAUKRI_DB_HOST, NAUKRI_DB_USER, NAUKRI_DB_PASSWORD, NAUKRI_DB_NAME
)
from typing import Dict, Any

# Define a short timeout for API robustness
DB_CONNECTION_TIMEOUT = 3 # 3 seconds


def run_pipeline(natural_language_query: str, debug_mode: bool = False) -> Dict[str, Any]:
    """
    Executes the full NextMove pipeline and returns a structured dictionary.

    Args:
        natural_language_query (str): The natural language query to process.
        debug_mode (bool): If True, returns intermediate artifacts.

    Returns:
        dict: Contains 'final_answer' and optional 'debug_info'.
    """
    print("=== NextMove Pipeline Started ===\n")

    # Step 1: Analyze Query
    print("[STEP 1] Analyzing query...")
    analyzed_result = run_single_query(natural_language_query)
    if analyzed_result is None:
        print("[ERROR] Failed to analyze query. Pipeline aborted.")
        return {
            "final_answer": "I'm sorry, I wasn't able to understand your query. Could you please rephrase it?",
            "debug_info": {"error": "Query analysis failed"}
        }

    unstructured_query = analyzed_result.get("unstructured_query", "")

    # Step 2: Decompose Query
    print("\n[STEP 2] Decomposing analyzed query...")
    federated_queries = decompose_single_query(analyzed_result)
    
    structured_queries = federated_queries.get("structured", {})
    db_results = {}

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
        db_results["Linkedin_source"] = "No query generated." # Report this in debug mode

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
        db_results["Naukri_source"] = "No query generated." # Report this in debug mode

    # Step 4: Synthesize Results
    final_answer = synthesize_results(
        natural_language_query=natural_language_query,
        unstructured_query=unstructured_query,
        database_results=db_results
    )

    print("\n=== Pipeline Completed ===")
    
    # Construct the final response dictionary based on debug_mode
    if debug_mode:
        return {
            "final_answer": final_answer,
            "debug_info": {
                "1_query_analysis": analyzed_result,
                "2_query_decomposition": federated_queries,
                "3_database_results": db_results
            }
        }
    else:
        return {
            "final_answer": final_answer,
            "debug_info": None # No debug info in normal mode
        }