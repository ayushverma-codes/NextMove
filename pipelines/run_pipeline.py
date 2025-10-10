import json
from pipelines.query_analyzer_test_pipeline import run_single_query
from pipelines.query_decomposer_test_pipeline import decompose_single_query
from components.connectors.mysql_connector import MySQLConnector


def run_pipeline(natural_language_query: str, show_analysis_json: bool = False, show_decomposition_json: bool = False):
    """
    Executes the full NextMove pipeline:
    1. Analyze natural language query
    2. Decompose structured JSON into SQL
    3. Execute SQL queries on corresponding sources

    Args:
        natural_language_query (str): The natural language query to process.
        show_analysis_json (bool): If True, prints structured output from analyzer.
        show_decomposition_json (bool): If True, prints decomposed federated queries.

    Returns:
        dict: Results from executing each structured query by source.
    """
    print("=== NextMove Pipeline Started ===\n")

    # Step 1: Analyze Query
    print("[STEP 1] Analyzing query...")
    analyzed_result = run_single_query(natural_language_query)
    if analyzed_result is None:
        print("[ERROR] Failed to analyze query. Pipeline aborted.")
        return None

    if show_analysis_json:
        print("\n[DEBUG] Analyzer Output:")
        print(json.dumps(analyzed_result, indent=2))

    # Step 2: Decompose Query
    print("\n[STEP 2] Decomposing analyzed query...")
    federated_queries = decompose_single_query(analyzed_result)

    if show_decomposition_json:
        print("\n[DEBUG] Decomposer Output (Federated Queries):")
        print(json.dumps(federated_queries, indent=2))

    structured_queries = federated_queries.get("structured", {})

    # Step 3: Execute Structured Queries
    print("\n[STEP 3] Executing structured queries on data sources...\n")
    results = {}

    # 🔹 MySQL: LinkedIn_Job_Postings
    linkedin_sql = structured_queries.get("LinkedIn_Job_Postings.csv")
    if linkedin_sql:
        print("[MySQL] Running query on LinkedIn_Job_Postings.csv:")
        print(linkedin_sql)
        try:
            mysql = MySQLConnector()
            mysql.connect()
            rows = mysql.execute_query(linkedin_sql)
            mysql.disconnect()
            print(f"[INFO] Retrieved {len(rows)} rows from MySQL.\n")
            results["LinkedIn_Job_Postings.csv"] = rows
        except Exception as e:
            print(f"[ERROR] MySQL query failed: {e}\n")
            results["LinkedIn_Job_Postings.csv"] = None
    else:
        print("[WARN] No SQL generated for LinkedIn_Job_Postings.csv\n")
        results["LinkedIn_Job_Postings.csv"] = None

    # 🔸 Placeholder: Postgres (job_descriptions.csv)
    job_desc_sql = structured_queries.get("job_descriptions.csv")
    if job_desc_sql:
        print("[Postgres] SQL generated for job_descriptions.csv (execution not implemented):")
        print(job_desc_sql)
        results["job_descriptions.csv"] = None
    else:
        print("[WARN] No SQL generated for job_descriptions.csv\n")
        results["job_descriptions.csv"] = None

    print("=== Pipeline Completed ===")
    return results
