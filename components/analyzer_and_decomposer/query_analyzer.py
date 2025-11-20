from langchain_core.prompts import ChatPromptTemplate
from ..LLM.llm_loader import load_llm
from constants import CURRENT_LLM, CURRENT_PROMPTS, DEFAULT_LIMIT, QUERY_ANALYZER_HUMAN_PROMPT, GLOBAL_SCHEMA
import json

# Load current LLM
llm = load_llm(CURRENT_LLM)

def parse_llm_json_response(llm_response: str) -> dict:
    """
    Parses an LLM response that returns JSON wrapped in triple backticks (```json ... ```).
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

def query_analyze(natural_query: str):
    # Get the specific prompt for the active LLM
    system_prompt = CURRENT_PROMPTS["analyzer_system"]
    
    chat_prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", QUERY_ANALYZER_HUMAN_PROMPT),
    ])

    prompt = chat_prompt.invoke(
        {
            "DEFAULT_LIMIT": DEFAULT_LIMIT,
            "schema": ", ".join(GLOBAL_SCHEMA.keys()),
            "user_query": natural_query,
        }
    )

    # FIX: Use .invoke() instead of calling llm() directly
    response = llm.invoke(prompt.messages)
    
    result_json = parse_llm_json_response(response)
    return result_json