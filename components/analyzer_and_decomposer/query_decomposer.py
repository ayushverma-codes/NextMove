import pprint
from entities.config import GAV_MAPPINGS, SOURCE_TO_TABLE, SOURCE_TO_DB_Type, GLOBAL_SCHEMA
from components.validator.SQLValidatorWrapper import FederatedSQLValidator
from components.translator.MySQL_translator import SQLTranslator
from components.LLM.query_retry_handler import QueryRetryHandler


def prepare_federated_queries(
    analyzed_result: dict,
    max_retries: int = 3,
    use_llm_retry: bool = True
) -> dict:
    """
    Take analyzer result → validate global SQL → retry if invalid → translate to sources → retry if invalid.
    Returns structured queries, global_sql, and unstructured query.
    """

    unstructured_query = analyzed_result.get("unstructured_query", "")
    global_sql_query = analyzed_result.get("sql_query", "")
    original_query = analyzed_result.get("original_query", "")

    if not global_sql_query:
        raise ValueError("Query Analyzer did not return a SQL query.")

    # Initialize validator & retry handler
    validator = FederatedSQLValidator()
    retry_handler = QueryRetryHandler(max_retries=max_retries) if use_llm_retry else None

    # Validate & retry global SQL
    global_sql_valid = False
    attempt = 0
    while attempt < max_retries and not global_sql_valid:
        validation_result = validator.validate_query(global_sql_query, source_name="GLOBAL_SCHEMA")
        global_sql_valid = validation_result.get("is_valid", False)

        if global_sql_valid:
            break

        if not use_llm_retry:
            break

        # Retry via LLM
        global_sql_query = retry_handler.retry_global_sql(
            natural_query=original_query,
            previous_sql=global_sql_query,
            validation_errors=validation_result.get("errors", [])
        )
        attempt += 1

    # Translate and validate per source
    structured_queries = {}
    for source in GAV_MAPPINGS.keys():
        db_type = SOURCE_TO_DB_Type.get(source, "MySQL")
        dialect = "mysql" if db_type.lower() == "mysql" else "postgres"

        translator = SQLTranslator(
            source=source,
            global_table_names=["Global_Job_Postings"],
            dialect=dialect
        )

        translated_query = translator.translate_query(global_sql_query)
        attempt = 0
        valid_translation = False
        while attempt < max_retries and not valid_translation:
            source_validation = validator.validate_query(translated_query, source_name=source)
            valid_translation = source_validation.get("is_valid", False)

            if valid_translation:
                break

            if not use_llm_retry:
                break

            local_schema = validator.get_source_schema(source)
            translated_query = retry_handler.retry_translation(
                global_sql=global_sql_query,
                source_name=source,
                db_type=db_type,
                previous_translation=translated_query,
                local_schema=local_schema,
                validation_errors=source_validation.get("errors", [])
            )
            attempt += 1

        structured_queries[source] = translated_query

    # Return simplified JSON
    return {
        "structured": structured_queries,
        "unstructured": unstructured_query,
        "global_sql": global_sql_query
    }
