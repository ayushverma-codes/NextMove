from langchain_core.prompts import ChatPromptTemplate
from components.LLM.llm_loader import load_llm
from constants import *
import json
from components.analyzer_and_decomposer.query_analyzer import query_analyze
from pipelines.query_analyzer_test_pipeline import analyze_all_queries, run_single_query

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

analyze_all_queries()

# @app.post("/analyze/")
# def analyze_query(query: str):
#     return run_single_query(query)
