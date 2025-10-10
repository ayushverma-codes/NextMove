from entities.config import GAV_MAPPINGS, SOURCE_TO_TABLE

def generate_sql_filter(structured_query: dict, source_csv: str) -> str:
    """
    Convert structured_query into a SQL-like filter for a specific structured CSV source.
    """
    mapping = GAV_MAPPINGS[source_csv]
    table_name = SOURCE_TO_TABLE.get(source_csv, source_csv)  # Get actual DB table name

    conditions = []

    for attr, value in structured_query.items():
        if attr in mapping and mapping[attr] is not None and value is not None:
            col = mapping[attr]
            if isinstance(value, (int, float)):
                if attr.lower().startswith("salary_range_min"):
                    conditions.append(f"{col} >= {value}")
                else:
                    conditions.append(f"{col} = {value}")
            else:
                conditions.append(f"{col} LIKE '%{value}%'")

    if conditions:
        sql_query = f"SELECT * FROM {table_name} WHERE " + " AND ".join(conditions)
    else:
        sql_query = f"SELECT * FROM {table_name}"  # No filters

    return sql_query


def prepare_federated_queries(decomposed_query: dict) -> dict:
    """
    Generate queries for all sources:
      - Structured sources: SQL-like filters
      - Unstructured source: LLM prompt

    Args:
        decomposed_query (dict): Output from query_analyzer containing 'structured_query'
                                 and 'unstructured_query'.

    Returns:
        dict: {'structured': {source_csv: sql_query}, 'unstructured': llm_text}
    """
    structured_queries = {}
    for source in GAV_MAPPINGS.keys():
        sql_query = generate_sql_filter(decomposed_query.get("structured_query", {}), source)
        structured_queries[source] = sql_query

    unstructured_query = decomposed_query.get("unstructured_query", "")

    return {
        "structured": structured_queries,
        "unstructured": unstructured_query
    }

