import os
import json
from constants import QUERY_INPUT_FILE_PATH, QUERY_ANALYZE_OUTPUT_FILE_PATH
from components.analyzer_and_decomposer.query_analyzer import query_analyze


def analyze_all_queries():
    """
    Reads all queries from a file, analyzes them using the query analyzer,
    saves results to a .jsonl file, and prints output per query.
    """
    if not os.path.exists(QUERY_INPUT_FILE_PATH):
        print(f"[ERROR] Query file not found: {QUERY_INPUT_FILE_PATH}")
        return

    with open(QUERY_INPUT_FILE_PATH, "r", encoding="utf-8") as file:
        queries = [line.strip() for line in file if line.strip()]

    print(f"\nFound {len(queries)} queries in file.\n")

    os.makedirs(os.path.dirname(QUERY_ANALYZE_OUTPUT_FILE_PATH), exist_ok=True)
    with open(QUERY_ANALYZE_OUTPUT_FILE_PATH, "w", encoding="utf-8") as outfile:
        for i, query in enumerate(queries, start=1):
            print(f"\n--- Query {i} ---")
            print(f"Input: {query}")
            try:
                result = query_analyze(query)
                print("Output:")
                print(json.dumps(result, indent=2))

                # Save to output file
                record = {
                    "query": query,
                    "result": result
                }
                outfile.write(json.dumps(record) + "\n")

            except Exception as e:
                print(f"Error analyzing query: {e}")
                error_record = {
                    "query": query,
                    "error": str(e)
                }
                outfile.write(json.dumps(error_record) + "\n")
            print("-" * 50)

    print(f"\nResults saved to: {QUERY_ANALYZE_OUTPUT_FILE_PATH}")


def run_single_query(query: str):
    """
    Runs a single query through the analyzer and returns the result.
    """
    print(f"\nAnalyzing single query:\n{query}")
    try:
        result = query_analyze(query)
        return result
    except Exception as e:
        print(f"Error: {e}")
        return None
