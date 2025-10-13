from entities.config import GAV_MAPPINGS, SOURCE_TO_TABLE, SOURCE_TO_DB_Type, GLOBAL_SCHEMA
from .query_analyzer import query_analyze
from components.validator.SQLValidatorWrapper import FederatedSQLValidator
from components.translator.MySQL_translator import SQLTranslator
from components.LLM.query_retry_handler import QueryRetryHandler


def prepare_federated_queries(natural_query: str, max_retries: int = 3, use_llm_retry: bool = True) -> dict:
    """
    Analyze a natural language query, generate SQL queries for each structured source,
    validate them, and optionally retry using LLM if queries are invalid.

    Args:
        natural_query (str): User input query.
        max_retries (int): Max retry attempts for invalid SQL.
        use_llm_retry (bool): Whether to use LLM to retry invalid queries.

    Returns:
        dict: {
            'analyzed_result': output from query_analyzer,
            'structured': {source_name: {"query": ..., "valid": ..., "errors": [...] }},
            'unstructured': LLM subquery,
            'valid': overall validity,
            'validation_errors': list of errors per source
        }
    """
    # Step 1: Analyze the natural query
    analyzed_result = query_analyze(natural_query)
    unstructured_query = analyzed_result.get("unstructured_query", "")
    global_sql_query = analyzed_result.get("sql_query", "")

    if not global_sql_query:
        raise ValueError("Query Analyzer did not return a SQL query.")

    # Step 2: Initialize validator
    validator = FederatedSQLValidator()
    structured_queries = {}

    # Step 3: Optionally retry global SQL if invalid
    if use_llm_retry:
        retry_handler = QueryRetryHandler(max_retries=max_retries)
        validation_result = validator.validate_query(global_sql_query, source_name="GLOBAL_SCHEMA")
        if not validation_result.get("is_valid", False):
            global_sql_query = retry_handler.retry_global_sql(
                natural_query=natural_query,
                previous_sql=global_sql_query,
                validation_errors=validation_result.get("errors", [])
            )

    # Step 4: Translate and validate per source
    for source in GAV_MAPPINGS.keys():
        db_type = SOURCE_TO_DB_Type.get(source, "MySQL")
        dialect = "mysql" if db_type.lower() == "mysql" else "postgres"

        translator = SQLTranslator(
            source=source,
            global_table_names=["Global_Job_Postings"],
            dialect=dialect
        )

        translated_query = translator.translate_query(global_sql_query)
        source_validation = validator.validate_query(translated_query, source_name=source)

        # Optionally retry translation if invalid
        if use_llm_retry and not source_validation.get("is_valid", False):
            local_schema = validator.get_source_schema(source)  # Assuming this method exists
            translated_query = retry_handler.retry_translation(
                global_sql=global_sql_query,
                source_name=source,
                db_type=db_type,
                previous_translation=translated_query,
                local_schema=local_schema,
                validation_errors=source_validation.get("errors", [])
            )
            # Re-validate after retry
            source_validation = validator.validate_query(translated_query, source_name=source)

        structured_queries[source] = {
            "query": translated_query,
            "valid": source_validation.get("is_valid", False),
            "errors": source_validation.get("errors", [])
        }

    # Step 5: Aggregate overall validity
    all_valid = all(q["valid"] for q in structured_queries.values())
    validation_errors = [] if all_valid else [q["errors"] for q in structured_queries.values()]

    # Step 6: Return final result
    return {
        # "analyzed_result": analyzed_result,
        "structured": structured_queries,
        "unstructured": unstructured_query,
        # "valid": all_valid,
        # "validation_errors": validation_errors,
    }
