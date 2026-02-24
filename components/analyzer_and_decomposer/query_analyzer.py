# components/analyzer_and_decomposer/query_analyzer.py
from langchain_core.prompts import ChatPromptTemplate
from ..LLM.llm_loader import load_llm
from constants import CURRENT_LLM, CURRENT_PROMPTS, DEFAULT_LIMIT, GLOBAL_SCHEMA
# --- NEW IMPORT ---
from components.matcher.term_normalizer import TermNormalizer 
import json

# Load current LLM
llm = load_llm(CURRENT_LLM)
# Initialize Normalizer
normalizer = TermNormalizer()

def parse_llm_json_response(llm_response: str) -> dict:
    # ... (Keep existing logic unchanged) ...
    raw_content = llm_response.content.strip() if hasattr(llm_response, 'content') else str(llm_response).strip()
    if raw_content.startswith("```") and raw_content.endswith("```"):
        lines = raw_content.splitlines()
        if lines[0].startswith("```"): lines = lines[1:]
        if lines[-1].startswith("```"): lines = lines[:-1]
        raw_content = "\n".join(lines).strip()
    try:
        result_json = json.loads(raw_content)
    except json.JSONDecodeError:
        try:
            start = raw_content.find('{')
            end = raw_content.rfind('}') + 1
            if start != -1 and end != -1:
                result_json = json.loads(raw_content[start:end])
            else: raise ValueError("No JSON found")
        except:
            raise ValueError(f"Failed to parse JSON: {raw_content}")
    return result_json

def query_analyze(natural_query: str, chat_history_context: str = ""):
    """
    Analyzes the query with semantic expansion.
    """
    # Get system prompt
    system_prompt = CURRENT_PROMPTS["analyzer_system"]
    
    # --- SEMANTIC EXPANSION ---
    # Get hints from the graph (Offline Brain)
    semantic_hints = normalizer.expand_query(natural_query)
    
    # --- CONTEXT INJECTION ---
    # Combine History + Semantic Hints + User Query
    full_human_input = (
        f"=== PREVIOUS CONVERSATION CONTEXT ===\n{chat_history_context}\n" if chat_history_context else ""
    )
    
    full_human_input += (
        f"{semantic_hints}\n"
        f"=====================================\n"
        f"LATEST USER QUERY: {natural_query}\n"
    )

    # Debug print to see what LLM receives
    print(f"[QueryAnalyzer] Context Injected:\n{semantic_hints}")

    # Create prompt
    chat_prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input_content}"),
    ])

    # Fill variables
    prompt = chat_prompt.invoke({
        "DEFAULT_LIMIT": DEFAULT_LIMIT,
        "schema": ", ".join(GLOBAL_SCHEMA.keys()),
        "input_content": full_human_input 
    })

    # Invoke LLM
    response = llm.invoke(prompt.messages)
    result_json = parse_llm_json_response(response)
    
    if result_json and "user_intent" not in result_json:
        result_json["user_intent"] = natural_query

    return result_json