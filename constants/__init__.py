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
3. For the structured part, generate the SELECT and WHERE components of an SQL-like query, strictly based on the GLOBAL_SCHEMA attributes.

Return a JSON with two keys:
   - structured_query: {{
         "select_clause": [list of attributes from GLOBAL_SCHEMA to retrieve],
         "where_clause": {{attribute: value}}
     }}
   - unstructured_query: text that needs to be answered by the LLM

Global schema attributes: {schema}

Example:
Input: "Find remote Marketing Coordinator jobs in Princeton, NJ with a minimum salary of $17 that require skills like communication, Excel, SQL, and project management. Also, list the company benefits and explain what a 'Marketing Coordinator' typically does."
Output:
{{
  "structured_query": {{
      "select_clause": ["title", "company_name", "location", "skills", "salary_range", "work_type"],
      "where_clause": {{
          "title": "Marketing Coordinator",
          "location": "Princeton, NJ",
          "work_type": "remote",
          "skills": ["communication", "Excel", "SQL", "project management"],
          "salary_range": ">= 17"
      }}
  }},
  "unstructured_query": "List company benefits and explain typical responsibilities of a 'Marketing Coordinator'."
}}
"""


QUERY_ANALYZER_HUMAN_PROMPT = """Input: {user_query}
Output:"""

# Query Analyzer and Decomposer

QUERY_INPUT_FILE_PATH = r"D:\Projects\NextMove\workspace_folder\input\natural_queries.txt"  # Path to the input file with natural language queries
QUERY_ANALYZE_OUTPUT_FILE_PATH = r"D:\Projects\NextMove\workspace_folder\artifacts\query_analysis.jsonl"

QUERY_DECOMPOSE_OUTPUT_FILE_PATH = r"D:\Projects\NextMove\workspace_folder\artifacts\query_decompose.jsonl"

