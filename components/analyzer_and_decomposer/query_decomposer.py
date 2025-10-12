from entities.config import GAV_MAPPINGS, SOURCE_TO_TABLE, SOURCE_TO_DB_Type
from .query_analyzer import query_analyze
from components.validator.SQLValidatorWrapper import FederatedSQLValidator
from components.translator.MySQL_translator import SQLTranslator


def prepare_federated_queries(natural_query: str) -> dict:
    """
    Main function to:
    1. Analyze a natural language query using the query_analyzer.
    2. Generate SQL queries for each structured source based on GAV mappings.
    3. Validate each query.
    4. Return structured queries and unstructured LLM subqueries.

    Args:
        natural_query (str): User’s input text query.

    Returns:
        dict: {
            'analyzed_result': output from query_analyzer,
            'structured': {source_name: {"query": ..., "valid": ..., "errors": [...] }},
            'unstructured': LLM subquery,
            'valid': overall validity,
            'validation_errors': list of errors per source
        }
    """

    # Step 1: Analyze the natural language query
    analyzed_result = query_analyze(natural_query)
    unstructured_query = analyzed_result.get("unstructured_query", "")
    global_sql_query = analyzed_result.get("sql_query", "")

    if not global_sql_query:
        raise ValueError("Query Analyzer did not return a SQL query.")

    # Step 2: Initialize validator
    validator = FederatedSQLValidator()
    structured_queries = {}

    # Step 3: Translate and validate per source
    for source in GAV_MAPPINGS.keys():
        # Determine SQL dialect from config
        db_type = SOURCE_TO_DB_Type.get(source, "MySQL")
        dialect = "mysql" if db_type.lower() == "mysql" else "postgres"

        # Translator instance
        translator = SQLTranslator(
            source=source,
            global_table_names=["Global_Job_Postings"],
            dialect=dialect
        )

        # Translate query from global schema to source-specific schema
        translated_query = translator.translate_query(global_sql_query)

        # Validate translated SQL against source schema
        source_validation = validator.validate_query(translated_query, source_name=source)

        structured_queries[source] = {
            "query": translated_query,
            "valid": source_validation.get("is_valid", False),
            "errors": source_validation.get("errors", [])
        }

    # Step 4: Aggregate overall validity
    all_valid = all(q["valid"] for q in structured_queries.values())
    validation_errors = [] if all_valid else [q["errors"] for q in structured_queries.values()]

    # Step 5: Return combined result
    return {
        # "analyzed_result": analyzed_result,
        "structured": structured_queries,
        "unstructured": unstructured_query,
        # "valid": all_valid,
        # "validation_errors": validation_errors
    }
