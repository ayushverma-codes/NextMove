import os
import json
from typing import Dict
from constants import (
    QUERY_ANALYZE_OUTPUT_FILE_PATH,
    QUERY_DECOMPOSE_OUTPUT_FILE_PATH
)
from components.analyzer_and_decomposer.query_decomposer import prepare_federated_queries

# -----------------------------
# 🔹 Decompose a single query
# -----------------------------
def decompose_single_query(analyzer_result: Dict) -> Dict:
    """
    Takes analyzer output (dict containing sql_query + unstructured_query),
    runs decomposition, translation, validation, and optional LLM retry.
    """
    return prepare_federated_queries(
        analyzed_result=analyzer_result,
        use_llm_retry=True,
    )


# -----------------------------
# 🔹 Batch Decomposition from JSONL
# -----------------------------
def decompose_all_queries():
    """
    Reads the query_analyzer output .jsonl file, applies decomposition,
    and saves federated queries to another .jsonl file.
    """
    if not os.path.exists(QUERY_ANALYZE_OUTPUT_FILE_PATH):
        raise FileNotFoundError(f"Input file not found: {QUERY_ANALYZE_OUTPUT_FILE_PATH}")

    os.makedirs(os.path.dirname(QUERY_DECOMPOSE_OUTPUT_FILE_PATH), exist_ok=True)

    with open(QUERY_ANALYZE_OUTPUT_FILE_PATH, "r", encoding="utf-8") as infile, \
         open(QUERY_DECOMPOSE_OUTPUT_FILE_PATH, "w", encoding="utf-8") as outfile:

        for line_count, line in enumerate(infile, start=1):
            try:
                record = json.loads(line)
                query = record.get("query")
                result = record.get("result")

                if not result or not isinstance(result, dict):
                    raise ValueError("Missing or invalid 'result' in record.")

                # Attach original query for retry context
                result["original_query"] = query

                federated = decompose_single_query(result)

                output_record = {
                    "query": query,
                    "federated_query": federated
                }

                outfile.write(json.dumps(output_record) + "\n")

            except Exception as e:
                # Only essential error message
                print(f"❌ Failed to process line {line_count}: {e}")

