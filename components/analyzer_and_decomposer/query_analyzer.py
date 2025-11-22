from langchain_core.prompts import ChatPromptTemplate
from ..LLM.llm_loader import load_llm
from constants import CURRENT_LLM, CURRENT_PROMPTS, DEFAULT_LIMIT, QUERY_ANALYZER_HUMAN_PROMPT, GLOBAL_SCHEMA
import json

# Load current LLM
llm = load_llm(CURRENT_LLM)

def parse_llm_json_response(llm_response: str) -> dict:
    """
    Parses an LLM response that returns JSON wrapped in triple backticks.
    """
    # Handle both string and AIMessage object
    raw_content = llm_response.content.strip() if hasattr(llm_response, 'content') else str(llm_response).strip()

    # Remove surrounding triple backticks if present
    if raw_content.startswith("```") and raw_content.endswith("```"):
        lines = raw_content.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        raw_content = "\n".join(lines).strip()

    try:
        result_json = json.loads(raw_content)
    except json.JSONDecodeError as e:
        # Fallback: try to find the first '{' and last '}'
        try:
            start = raw_content.find('{')
            end = raw_content.rfind('}') + 1
            if start != -1 and end != -1:
                json_str = raw_content[start:end]
                result_json = json.loads(json_str)
            else:
                raise ValueError("No JSON found")
        except Exception:
            raise ValueError(
                f"Failed to parse JSON from LLM response: {e}\nRaw content:\n{raw_content}"
            )

    return result_json

def query_analyze(natural_query: str, chat_history_context: str = ""):
    """
    Analyzes the query.
    CRITICAL: Injects 'chat_history_context' into the prompt to allow Intent Resolution.
    """
    # Get the specific prompt for the active LLM
    system_prompt = CURRENT_PROMPTS["analyzer_system"]
    
    # --- CONTEXT INJECTION ---
    # We manually build the top part of the human input to ensure Context is visible
    if chat_history_context:
        full_human_input = (
            f"=== PREVIOUS CONVERSATION CONTEXT ===\n"
            f"{chat_history_context}\n"
            f"=====================================\n\n"
            f"LATEST USER QUERY: {natural_query}\n"
        )
    else:
        full_human_input = f"LATEST USER QUERY: {natural_query}"

    # Create the prompt template
    chat_prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input_content}"), # We pass the combined string here
    ])

    # Fill variables
    prompt = chat_prompt.invoke(
        {
            "DEFAULT_LIMIT": DEFAULT_LIMIT,
            "schema": ", ".join(GLOBAL_SCHEMA.keys()),
            "input_content": full_human_input 
        }
    )

    # Invoke LLM
    response = llm.invoke(prompt.messages)
    
    result_json = parse_llm_json_response(response)
    
    # Fallback: If LLM forgot to generate 'user_intent', use raw query
    if result_json and "user_intent" not in result_json:
        result_json["user_intent"] = natural_query

    return result_json