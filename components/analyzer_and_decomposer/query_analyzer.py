from langchain_core.prompts import ChatPromptTemplate
from ..LLM.llm_loader import load_llm
from constants import *
import json
from entities.config import GLOBAL_SCHEMA


# Load Gemini or Ollama dynamically
llm = load_llm(CURRENT_LLM)

def parse_llm_json_response(llm_response: str) -> dict:
    """
    Parses an LLM response that returns JSON wrapped in triple backticks (```json ... ```).
    
    Args:
        llm_response (str): The raw response content from the LLM.
    
    Returns:
        dict: Parsed JSON object.
    
    Raises:
        ValueError: If the content cannot be parsed as JSON.
    """
    raw_content = llm_response.content.strip()

    # Remove surrounding triple backticks if present
    if raw_content.startswith("```") and raw_content.endswith("```"):
        lines = raw_content.splitlines()
        # Remove the first line if it contains ``` or ```json
        if lines[0].startswith("```"):
            lines = lines[1:]
        # Remove the last line if it contains ```
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        raw_content = "\n".join(lines).strip()

    # Parse the cleaned string as JSON
    try:
        result_json = json.loads(raw_content)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Failed to parse JSON from LLM response: {e}\nRaw content:\n{raw_content}"
        )

    return result_json

def query_analyze(natural_query: str):
    chat_prompt = ChatPromptTemplate.from_messages([
        ("system", QUERY_ANALYZER_SYSTEM_PROMPT),
        ("human", QUERY_ANALYZER_HUMAN_PROMPT),
    ])

    prompt = chat_prompt.invoke(
        {
            "schema": ", ".join(GLOBAL_SCHEMA.keys()),
            "user_query": natural_query,
        }
    )

    response = llm(prompt.messages)

    # print("\nLLM response: \n")
    # print(response)
    # print("\n")

    result_json = parse_llm_json_response(response)
    return result_json