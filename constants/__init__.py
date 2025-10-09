# LLM

LLM1 = "gemini"
LLM2 = "ollama"

CURRENT_LLM = LLM1

# Prompts

# D:\Projects\NextMove\constants\__init__.py

QUERY_ANALYZER_SYSTEM_PROMPT = """
You are a Query Analyzer for a federated job information system.

You receive a natural language query about jobs. Some information may exist in the structured databases (CSV sources) and some may require general knowledge (unstructured, LLM).

1. Identify which parts of the query can be answered using the structured databases.
2. Identify which parts require general knowledge (unstructured source).
3. Return a JSON with two keys:
   - structured_query: {{attribute: value}} pairs based on the GLOBAL_SCHEMA
   - unstructured_query: text that needs to be answered by the LLM

Global schema attributes: {schema}

Example:
Input: "Find the job in Princeton, NJ with a minimum salary of $17, list its company benefits, and explain what a 'Marketing Coordinator' typically does."
Output:
{{
  "structured_query": {{
      "location": "Princeton, NJ",
      "salary_range_min": 17
  }},
  "unstructured_query": "List company benefits and explain typical responsibilities of a 'Marketing Coordinator'."
}}"""

QUERY_ANALYZER_HUMAN_PROMPT = """Input: {user_query}
Output:"""

# Query Analyzer

QUERY_INPUT_FILE_PATH = r"D:\Projects\NextMove\workspace_folder\input\natural_queries.txt"  # Path to the input file with natural language queries
QUERY_ANALYZE_OUTPUT_FILE_PATH = r"D:\Projects\NextMove\workspace_folder\artifacts\query_analysis.jsonl"

