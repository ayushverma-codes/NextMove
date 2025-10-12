from entities.config import GAV_MAPPINGS, SOURCE_TO_TABLE
from .query_analyzer import query_analyze
import re

def generate_sql_from_structured_query(structured_query: dict, source_csv: str) -> str:
    """
    Convert structured_query into a SQL-like filter for a specific structured CSV source.
    Improvements:
    - Consistently uses backticks for table and column names.
    - Automatically casts numeric columns (like salary) before comparison.
    - Ensures only columns present in GAV_MAPPINGS[source_csv] are used.
    - Handles numeric operators in string values like '>= 120000'.
    """
    mapping = GAV_MAPPINGS[source_csv]
    table_name = f"`{SOURCE_TO_TABLE.get(source_csv, source_csv)}`"  # consistent quoting

    conditions = []

    # Support both flat and decomposed query forms
    where_clause = structured_query.get("where_clause", structured_query)
    select_clause = structured_query.get("select_clause", [])

    # --- Build WHERE conditions ---
    for attr, value in where_clause.items():
        # Only include columns present in GAV mapping
        if attr not in mapping or mapping[attr] is None:
            continue

        col = f"`{mapping[attr]}`"
        if value is None:
            continue

        # Handle numeric comparisons if value is a string like ">= 120000"
        if isinstance(value, str):
            match = re.match(r"^(>=|<=|>|<|=)\s*(\d+(\.\d+)?)$", value.strip())
            if match:
                op, num_val, _ = match.groups()
                conditions.append(f"CAST({col} AS REAL) {op} {num_val}")
                continue
            # If pure numeric string
            if value.replace(".", "", 1).isdigit():
                conditions.append(f"CAST({col} AS REAL) = {value}")
                continue

        # Handle numeric types directly
        if isinstance(value, (int, float)):
            conditions.append(f"CAST({col} AS REAL) = {value}")
        # Handle list of values (e.g., multiple skills)
        elif isinstance(value, list):
            or_conditions = " OR ".join([f"{col} LIKE '%{v}%'" for v in value])
            conditions.append(f"({or_conditions})")
        # Generic string fallback
        else:
            conditions.append(f"{col} LIKE '%{value}%'")

    # --- Build SELECT clause ---
    valid_select_cols = [f"`{mapping[attr]}`" for attr in select_clause if attr in mapping and mapping[attr] is not None]
    select_expr = ", ".join(valid_select_cols) if valid_select_cols else "*"

    # --- Final SQL assembly ---
    if conditions:
        sql_query = f"SELECT {select_expr} FROM {table_name} WHERE " + " AND ".join(conditions)
    else:
        sql_query = f"SELECT {select_expr} FROM {table_name}"

    return sql_query



def prepare_federated_queries(natural_query: str) -> dict:
    """
    Main function to:
    1. Analyze a natural language query using the query_analyzer.
    2. Generate SQL-like queries for each structured source based on GAV mappings.
    3. Return both structured (SQLs) and unstructured (LLM) subqueries.

    Args:
        natural_query (str): User’s input text query.

    Returns:
        dict: {
            'analyzed_result': parsed analyzer output,
            'structured': {source_name: sql_query},
            'unstructured': llm_subquery
        }
    """

    # Step 1: Analyze query using LLM-based analyzer
    analyzed_result = query_analyze(natural_query)

    structured_query = analyzed_result.get("structured_query", {})
    unstructured_query = analyzed_result.get("unstructured_query", "")

    # Step 2: Generate SQL queries for each structured source
    structured_queries = {}
    for source in GAV_MAPPINGS.keys():
        sql_query = generate_sql_from_structured_query(structured_query, source)
        structured_queries[source] = sql_query

    # Step 3: Return combined result
    return {
        # "analyzed_result": analyzed_result,
        "structured": structured_queries,
        "unstructured": unstructured_query
    }
