import os
import json
from typing import Dict

from constants import (
    QUERY_ANALYZE_OUTPUT_FILE_PATH,
    QUERY_DECOMPOSE_OUTPUT_FILE_PATH
)

from components.analyzer_and_decomposer.query_decomposer import prepare_federated_queries

# -----------------------------
# 🔹 Decompose a single structured query
# -----------------------------
def decompose_single_query(decomposed_query: Dict) -> Dict:
    """
    Takes a decomposed query with 'structured_query' and 'unstructured_query',
    returns federated queries (structured + unstructured).
    """
    return prepare_federated_queries(decomposed_query)


# -----------------------------
# 🔹 Batch Decomposition from JSONL (Analyzer Output)
# -----------------------------
def decompose_all_queries():
    """
    Reads the query_analyzer output .jsonl file, applies decomposition,
    and saves federated queries to another .jsonl file.
    Prints federated query results per query.
    """
    if not os.path.exists(QUERY_ANALYZE_OUTPUT_FILE_PATH):
        print(f"[ERROR] Input file not found: {QUERY_ANALYZE_OUTPUT_FILE_PATH}")
        return

    os.makedirs(os.path.dirname(QUERY_DECOMPOSE_OUTPUT_FILE_PATH), exist_ok=True)

    with open(QUERY_ANALYZE_OUTPUT_FILE_PATH, "r", encoding="utf-8") as infile, \
         open(QUERY_DECOMPOSE_OUTPUT_FILE_PATH, "w", encoding="utf-8") as outfile:

        line_count = 0
        for line in infile:
            line_count += 1
            try:
                record = json.loads(line)
                query = record.get("query")
                result = record.get("result")

                if not result or not isinstance(result, dict):
                    raise ValueError("Missing or invalid 'result' in record.")

                federated = decompose_single_query(result)

                output_record = {
                    "query": query,
                    "federated_query": federated
                }

                outfile.write(json.dumps(output_record) + "\n")

                # Print per query
                print(f"\n--- Query {line_count} ---")
                print(f"Input Query:\n{query}")
                print(f"Federated Query Output:\n{json.dumps(federated, indent=2)}")
                print("-" * 60)

            except Exception as e:
                print(f"Failed to process line {line_count}: {e}")

    print(f"\nAll queries decomposed and saved to: {QUERY_DECOMPOSE_OUTPUT_FILE_PATH}")
