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

# Define a short timeout for API robustness
DB_CONNECTION_TIMEOUT = 3 # 3 seconds


def run_pipeline(natural_language_query: str, show_analysis_json: bool = False, show_decomposition_json: bool = False):
    """
    Executes the full NextMove pipeline:
    1. Analyze natural language query
    2. Decompose structured JSON into SQL
    3. Execute SQL queries on corresponding sources (robustly)
    4. Synthesize results with an LLM into a final answer

    Returns:
        str: A single, synthesized natural language answer.
    """
    print("=== NextMove Pipeline Started ===\n")

    # Step 1: Analyze Query
    print("[STEP 1] Analyzing query...")
    analyzed_result = run_single_query(natural_language_query)
    if analyzed_result is None:
        print("[ERROR] Failed to analyze query. Pipeline aborted.")
        return "I'm sorry, I wasn't able to understand your query. Could you please rephrase it?"

    if show_analysis_json:
        print("\n[DEBUG] Analyzer Output:")
        print(json.dumps(analyzed_result, indent=2))
        
    unstructured_query = analyzed_result.get("unstructured_query", "")

    # Step 2: Decompose Query
    print("\n[STEP 2] Decomposing analyzed query...")
    federated_queries = decompose_single_query(analyzed_result)

    if show_decomposition_json:
        print("\n[DEBUG] Decomposer Output (Federated Queries):")
        print(json.dumps(federated_queries, indent=2))

    structured_queries = federated_queries.get("structured", {})
    results = {}

    # Step 3: Execute Structured Queries (Now Robust)
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
                timeout=DB_CONNECTION_TIMEOUT  # Pass the timeout
            )
            mysql_linkedin.connect() # This will fail fast if DB is down
            rows = mysql_linkedin.execute_query_as_dict(linkedin_sql)
            mysql_linkedin.disconnect()
            print(f"[INFO] Retrieved {len(rows)} rows from Linkedin_source.\n")
            results["Linkedin_source"] = rows
        except Exception as e:
            # This is our robustness! We log the error and continue.
            print(f"[ERROR] Linkedin_source query failed: {e}\n")
            results["Linkedin_source"] = [{"error": f"Failed to connect or query: {e}"}]
    else:
        print("[WARN] No SQL generated for Linkedin_source\n")
        results["Linkedin_source"] = [] # Use empty list for no query

    # 🔹 MySQL: Naukri_source (Now Robustly Implemented)
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
                timeout=DB_CONNECTION_TIMEOUT # Pass the timeout
            )
            mysql_naukri.connect() # This will also fail fast
            rows = mysql_naukri.execute_query_as_dict(naukri_sql)
            mysql_naukri.disconnect()
            print(f"[INFO] Retrieved {len(rows)} rows from Naukri_source.\n")
            results["Naukri_source"] = rows
        except Exception as e:
            # Robustness for the second DB
            print(f"[ERROR] Naukri_source query failed: {e}\n")
            results["Naukri_source"] = [{"error": f"Failed to connect or query: {e}"}]
    else:
        print("[WARN] No SQL generated for Naukri_source\n")
        results["Naukri_source"] = []

    # Step 4: Synthesize Results (New Step)
    # This step runs even if one or both DBs failed.
    # The LLM will be given the error messages to explain to the user.
    final_answer = synthesize_results(
        natural_language_query=natural_language_query,
        unstructured_query=unstructured_query,
        database_results=results
    )

    print("\n=== Pipeline Completed ===")
    return final_answer