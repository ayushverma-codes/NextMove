import json
from langchain_core.prompts import ChatPromptTemplate
from ..LLM.llm_loader import load_llm
from constants import CURRENT_LLM, CURRENT_PROMPTS, GLOBAL_SCHEMA

# Load current LLM dynamically
llm = load_llm(CURRENT_LLM)

def parse_llm_json_response(llm_response: str) -> dict:
    """
    Parse LLM JSON response wrapped in triple backticks if present.
    """
    raw_content = llm_response.content.strip() if hasattr(llm_response, 'content') else str(llm_response).strip()

    # Remove surrounding triple backticks
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
        # Simple fallback to try and find brace boundaries
        try:
            start = raw_content.find('{')
            end = raw_content.rfind('}') + 1
            result_json = json.loads(raw_content[start:end])
        except:
            raise ValueError(f"Failed to parse JSON from LLM response: {e}")

    return result_json


class QueryRetryHandler:
    """
    Handles retries for invalid SQL queries:
    1. Global SQL retry
    2. Source-specific translation retry
    """

    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries

    def retry_global_sql(self, natural_query: str, previous_sql: str, validation_errors: list) -> str:
        system_prompt = CURRENT_PROMPTS["retry_global"]

        prompt_template = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{user_query}")
        ])

        for _ in range(self.max_retries):
            prompt = prompt_template.invoke({
                "user_query": natural_query,
                "natural_query": natural_query,
                "global_schema": ", ".join(GLOBAL_SCHEMA.keys()),
                "previous_sql": previous_sql,
                "validation_errors": "\n".join(validation_errors)
            })

            # FIX: Use .invoke()
            response = llm.invoke(prompt.messages)
            
            try:
                result = parse_llm_json_response(response)
                corrected_sql = result.get("corrected_sql")
                if corrected_sql:
                    return corrected_sql
            except Exception:
                continue # Try again if parsing fails

        raise RuntimeError(f"Failed to generate valid global SQL after {self.max_retries} retries.")

    def retry_translation(
        self,
        global_sql: str,
        source_name: str,
        db_type: str,
        previous_translation: str,
        local_schema: dict,
        validation_errors: list
    ) -> str:
        system_prompt = CURRENT_PROMPTS["retry_translation"]
        
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{user_query}")
        ])

        for _ in range(self.max_retries):
            prompt = prompt_template.invoke({
                "user_query": global_sql,
                "global_sql": global_sql,
                "source_name": source_name,
                "db_type": db_type,
                "previous_translation": previous_translation,
                "global_schema": ", ".join(GLOBAL_SCHEMA.keys()),
                "local_schema": json.dumps(local_schema, indent=2),
                "validation_errors": "\n".join(validation_errors)
            })

            # FIX: Use .invoke()
            response = llm.invoke(prompt.messages)
            
            try:
                result = parse_llm_json_response(response)
                corrected_sql = result.get("corrected_sql")
                if corrected_sql:
                    return corrected_sql
            except Exception:
                continue

        raise RuntimeError(f"Failed to generate valid translation for source '{source_name}' after {self.max_retries} retries.")