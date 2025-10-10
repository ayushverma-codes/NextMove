from langchain_core.prompts import ChatPromptTemplate
from components.LLM.llm_loader import load_llm
from constants import *
import json
from components.analyzer_and_decomposer.query_analyzer import query_analyze
from pipelines.query_analyzer_test_pipeline import analyze_all_queries, run_single_query
from pipelines.run_pipeline import run_pipeline

# # Load Gemini or Ollama dynamically
# # llm = load_llm(CURRENT_LLM)

# natural_query = "Find the job in Princeton, NJ with a minimum salary of $17, list its company benefits, and explain what a 'Marketing Coordinator' typically does."

# # Run the query through query_analyze
# result = query_analyze(natural_query)

# # Print the result to check if it works
# print("Result from query_analyze:")
# print(result)

# To analyze a specific query
# result = run_single_query("Find remote jobs in marketing with salary above $70,000.")
# print("Result:")
# print(json.dumps(result, indent=2))

# analyze_all_queries()

# @app.post("/analyze/")
# def analyze_query(query: str):
#     return run_single_query(query)

# from pipelines.query_decomposer_test_pipeline import decompose_all_queries, decompose_single_query

# To run the full decomposition pipeline
# decompose_all_queries()

# # To test a single decomposed query manually
# sample_decomposed_query = {
#     "structured_query": {
#         "location": "New York",
#         "title": "Data Analyst"
#     },
#     "unstructured_query": "What benefits are commonly offered?"
# }

# result = decompose_single_query(sample_decomposed_query)
# print("\nSingle federated decomposition result:")
# print(json.dumps(result, indent=2))

# D:\Projects\NextMove\app.py

from pipelines.run_pipeline import run_pipeline

def main():
    print("Welcome to NextMove Query Interface!")
    print("Type your natural language query below (or 'exit' to quit):")

    while True:
        user_query = input("\nEnter query: ").strip()
        if user_query.lower() in {"exit", "quit"}:
            print("Exiting NextMove. Goodbye!")
            break
        
        # Run the pipeline; set show_json=True if you want to see JSON output for debugging
        results = run_pipeline(user_query, show_json=True)

        if results is None:
            print("[ERROR] Pipeline did not return any results.")
            continue

        print("\n--- Query Results ---")
        for source, data in results.items():
            if data is None:
                print(f"{source}: No data retrieved or not implemented yet.")
            else:
                print(f"{source}: Retrieved {len(data)} rows")
                for row in data[:5]:  # Print first 5 rows as sample
                    print(row)
        print("---------------------")

if __name__ == "__main__":
    main()
