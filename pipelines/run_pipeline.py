# D:\Projects\NextMove\pipelines\run_pipeline.py

import json
from pipelines.query_analyzer_test_pipeline import run_single_query
from pipelines.query_decomposer_test_pipeline import decompose_single_query
from components.connectors.mysql_connector import MySQLConnector

def run_pipeline(natural_language_query: str, show_json: bool = False):
    """
    Runs the full pipeline:
    - Analyze natural language query to JSON (structured + unstructured)
    - Decompose JSON into SQL queries for each source
    - Execute queries on respective databases
    - Return combined results

    Args:
        natural_language_query (str): The user's natural language query.
        show_json (bool): If True, prints the JSON output from analyzer.

    Returns:
        dict: Combined query results keyed by source name.
    """
    print("=== NextMove Pipeline Started ===")

    # Step 1: Analyze the natural language query
    analyzed_json = run_single_query(natural_language_query)
    if analyzed_json is None:
        print("[ERROR] Query analysis failed. Aborting pipeline.")
        return None

    if show_json:
        print("\n[DEBUG] Analyzer JSON Output:")
        print(json.dumps(analyzed_json, indent=2))

    # Step 2: Decompose analyzed query to get SQL queries for each source
    federated_queries = decompose_single_query(analyzed_json)
    structured_queries = federated_queries.get("structured", {})

    # Step 3: Execute SQL queries on each source
    results = {}

    # MySQL source: LinkedIn_Job_Postings.csv
    linkedin_sql = structured_queries.get("LinkedIn_Job_Postings.csv")
    if linkedin_sql:
        try:
            mysql_conn = MySQLConnector()
            mysql_conn.connect()
            rows = mysql_conn.execute_query(linkedin_sql)
            results["LinkedIn_Job_Postings.csv"] = rows
            mysql_conn.disconnect()
            print(f"[INFO] Retrieved {len(rows)} rows from MySQL source.")
        except Exception as e:
            print(f"[ERROR] MySQL query execution failed: {e}")
            results["LinkedIn_Job_Postings.csv"] = None
    else:
        print("[WARN] No MySQL query generated for LinkedIn_Job_Postings.csv")

    # Postgres source: job_descriptions.csv
    # Placeholder - replace with PostgresConnector usage later
    job_desc_sql = structured_queries.get("job_descriptions.csv")
    if job_desc_sql:
        print("[INFO] Postgres SQL query generated (execution placeholder):")
        print(job_desc_sql)
        # TODO: Implement PostgresConnector and query execution here
        results["job_descriptions.csv"] = None
    else:
        print("[WARN] No SQL query generated for job_descriptions.csv")

    print("=== Pipeline Completed ===")
    return results
