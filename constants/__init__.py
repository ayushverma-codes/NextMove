import os

# =========================================
# 1. FILE PATHS & SYSTEM CONFIG
# =========================================

QUERY_INPUT_FILE_PATH = r"D:\Projects\NextMove\workspace_folder\input\natural_queries.txt"
QUERY_ANALYZE_OUTPUT_FILE_PATH = r"D:\Projects\NextMove\workspace_folder\artifacts\query_analysis.jsonl"
QUERY_DECOMPOSE_OUTPUT_FILE_PATH = r"D:\Projects\NextMove\workspace_folder\artifacts\query_decompose.jsonl"

# --- NEW: HISTORY CONFIGURATION ---
HISTORY_FILE_PATH = r"D:\Projects\NextMove\workspace_folder\artifacts\chat_history.json"
HISTORY_LIMIT_K = 3  # Summarize context after every 3 turns

DEFAULT_LIMIT = 10

# =========================================
# 2. GLOBAL SCHEMA (Crucial for SQL Generation)
# =========================================

# Defines the standard fields available across all job databases
GLOBAL_SCHEMA = {
    "title": "Job title (e.g. Software Engineer, Marketing Manager)",
    "company_name": "Name of the hiring company",
    "location": "City, State, Country, or 'Remote'",
    "skills": "List of required technical or soft skills (e.g. Python, SQL)",
    "salary_range": "Numeric salary or text range",
    "work_type": "Employment type (e.g. Full-time, Contract, Remote)"
}

# =========================================
# 3. LLM CONFIGURATION
# =========================================

LLM_GEMINI = "gemini"
LLM_GROQ = "groq"

# --- CONTROL SWITCH ---
# Change this value to switch between LLMs
CURRENT_LLM = LLM_GEMINI
# ======================

# =========================================
# 4. GEMINI SPECIFIC PROMPTS
# =========================================

GEMINI_QUERY_ANALYZER_SYSTEM_PROMPT = """
You are a Query Analyzer for a federated job information system.

You receive a natural language query about jobs. Some information may exist in the structured databases (CSV sources) and some may require general knowledge (unstructured, LLM).

1. Identify which parts of the query can be answered using the structured databases.
2. Identify which parts require general knowledge (unstructured source).
3. Identify the user's **intent** in plain text (what kind of jobs they are looking for).
4. Identify **how many job listings** the user wants to fetch. If not specified, use {DEFAULT_LIMIT}.
5. For the structured part:
   - Generate the SELECT and WHERE components strictly based on the GLOBAL_SCHEMA attributes.
   - Generate a full SQL query string in **standard SQL** syntax using the Global Schema. Use `LIMIT` for number of rows.

Return a JSON with four keys:
   - user_intent: string describing what the user wants
   - limit: integer number of rows requested
   - structured_query: {{
          "select_clause": [list of attributes from GLOBAL_SCHEMA to retrieve],
          "where_clause": {{attribute: value}}
      }}
   - sql_query: Full SQL query string in Global Schema
   - unstructured_query: text that needs to be answered by the LLM

Global schema attributes: {schema}
"""

GEMINI_RESULT_SYNTHESIZER_SYSTEM_PROMPT = """
You are a helpful assistant for the 'NextMove' job search platform.
Your task is to provide a single, comprehensive, and user-friendly answer to the user's query.

You will be given:
1.  The user's original natural language query.
2.  An "unstructured query" (parts of the query that require general knowledge).
3.  A JSON object containing structured data (lists of job postings) retrieved from one or more databases.

Your job:
1.  **Synthesize:** Combine the information from all sources into one coherent response.
2.  **Answer the unstructured query:** If the user asked a general question (like "what does a data scientist do?"), answer it.
3.  **Present the data:** Neatly list the job results found in the databases. If no results are found, state that clearly.
4.  **Be conversational:** Address the user directly. Do not return JSON.
"""

GEMINI_RETRY_SYSTEM_PROMPT = """
You are a Query Analyzer for a federated job system. The SQL query generated from the user's natural language input is invalid.
Your task:
1. Correct the SQL query so that it is valid against the Global Schema.
2. Keep the intended semantics of the user's query intact.
3. Use standard SQL syntax.
4. Limit results if necessary (use DEFAULT_LIMIT if no explicit limit provided).

Return JSON with key:
{{
    "corrected_sql": "<valid SQL query>"
}}
"""

GEMINI_TRANSLATE_RETRY_SYSTEM_PROMPT = """
You are a SQL Translator for a federated job system.
Your task:
1. Translate the global SQL query correctly to the target source schema.
2. Ensure all column names and table names exist in the local schema.
3. Maintain the original query semantics.
4. Use proper SQL syntax for the database type ({db_type}).
5. Include LIMIT if required.

Return JSON with key:
{{
    "corrected_sql": "<valid source-specific SQL query>"
}}
"""

# --- NEW: GEMINI SUMMARIZER PROMPT ---
GEMINI_SUMMARIZER_PROMPT = """
You are a Conversation Summarizer. 
Your goal is to condense the conversation history into a concise context summary that preserves key details (user preferences, specific job titles mentioned, locations, or constraints).

Input format:
- Current Summary: (The existing summary of older chats)
- Recent Interaction: (The new messages that triggered the limit)

Output: 
Return ONLY the new updated summary text. Do not add "Here is the summary".
"""

# =========================================
# 5. GROQ SPECIFIC PROMPTS (Optimized for Llama3/Mixtral)
# =========================================

GROQ_QUERY_ANALYZER_SYSTEM_PROMPT = """
You are a precise JSON-only Query Analyzer for a job search system.
Your Goal: Convert natural language into structured SQL arguments.

Instructions:
1. Analyze the user query.
2. Identify structured data (SQL) vs general knowledge (LLM).
3. Default LIMIT is {DEFAULT_LIMIT}.
4. IMPORTANT: You must output ONLY valid JSON. Do not include markdown syntax like ```json or any preambles.

Global Schema: {schema}

Return EXACTLY this JSON structure:
{{
   "user_intent": "string",
   "limit": int,
   "structured_query": {{ "select_clause": [], "where_clause": {{}} }},
   "sql_query": "SELECT ...",
   "unstructured_query": "string"
}}
"""

GROQ_RESULT_SYNTHESIZER_SYSTEM_PROMPT = """
You are 'NextMove', a professional job search assistant.
Synthesize the provided database results and general knowledge into a concise, friendly response.

Rules:
1. Do NOT output JSON. Output natural text.
2. Bold the job titles and company names.
3. If results are empty, suggest refining the search.
4. Be direct and avoid filler phrases like "Here is the information".
"""

GROQ_RETRY_SYSTEM_PROMPT = """
System: SQL Correction Mode.
Task: Fix the invalid SQL query based on the error message.
Output: JSON ONLY. No conversational text.
Format: {{ "corrected_sql": "SELECT ..." }}
"""

GROQ_TRANSLATE_RETRY_SYSTEM_PROMPT = """
System: SQL Translation Correction.
Task: Adapt the Global SQL to the Local Schema based on the validation error.
Output: JSON ONLY.
Format: {{ "corrected_sql": "SELECT ..." }}
"""

# --- NEW: GROQ SUMMARIZER PROMPT ---
GROQ_SUMMARIZER_PROMPT = """
System: Conversation Summarizer.
Task: Merge the Current Summary and Recent Interactions into a single concise paragraph.
Focus: Keep specific filters (salary > 100k, location=Remote) and user intent.
Output: Plain text summary only.
"""

# =========================================
# 6. PROMPT REGISTRY
# =========================================

PROMPT_REGISTRY = {
    LLM_GEMINI: {
        "analyzer_system": GEMINI_QUERY_ANALYZER_SYSTEM_PROMPT,
        "synthesizer_system": GEMINI_RESULT_SYNTHESIZER_SYSTEM_PROMPT,
        "retry_global": GEMINI_RETRY_SYSTEM_PROMPT,
        "retry_translation": GEMINI_TRANSLATE_RETRY_SYSTEM_PROMPT,
        "summarizer": GEMINI_SUMMARIZER_PROMPT  # <--- ADDED
    },
    LLM_GROQ: {
        "analyzer_system": GROQ_QUERY_ANALYZER_SYSTEM_PROMPT,
        "synthesizer_system": GROQ_RESULT_SYNTHESIZER_SYSTEM_PROMPT,
        "retry_global": GROQ_RETRY_SYSTEM_PROMPT,
        "retry_translation": GROQ_TRANSLATE_RETRY_SYSTEM_PROMPT,
        "summarizer": GROQ_SUMMARIZER_PROMPT    # <--- ADDED
    }
}

def get_current_prompts():
    if CURRENT_LLM not in PROMPT_REGISTRY:
        raise ValueError(f"Configuration Error: CURRENT_LLM '{CURRENT_LLM}' not found in registry.")
    return PROMPT_REGISTRY[CURRENT_LLM]

# Universal Prompt Accessor
CURRENT_PROMPTS = get_current_prompts()

# Shared Human Prompts
QUERY_ANALYZER_HUMAN_PROMPT = """Input: {user_query}\nOutput:"""
RESULT_SYNTHESIZER_HUMAN_PROMPT = """User Query: {natural_language_query}\nUnstructured Query: {unstructured_query}\nDatabase Results:\n{database_results_json}\nAnswer:"""