# D:\Projects\NextMove\components\synthesizer\result_synthesizer.py

import json
from typing import Dict, Any, List
from constants import (
    RESULT_SYNTHESIZER_SYSTEM_PROMPT,
    RESULT_SYNTHESIZER_HUMAN_PROMPT,
    CURRENT_LLM
)
# This imports directly from your loader, as requested
from components.LLM.llm_loader import load_llm
from langchain_core.messages import SystemMessage, HumanMessage


def synthesize_results(
    natural_language_query: str,
    unstructured_query: str,
    database_results: Dict[str, List[Dict[str, Any]]]
) -> str:
    """
    Takes the retrieved database results and the original query,
    and calls an LLM to synthesize a final natural language answer.
    """
    print("[STEP 4] Synthesizing final answer with LLM...")

    # Convert database results to a clean JSON string for the prompt
    # Use default=str to handle any non-serializable types like dates
    try:
        results_json = json.dumps(database_results, indent=2, default=str)
    except Exception as e:
        print(f"[WARN] Could not serialize DB results to JSON: {e}")
        results_json = str(database_results)

    # Format the prompt
    human_prompt = RESULT_SYNTHESIZER_HUMAN_PROMPT.format(
        natural_language_query=natural_language_query,
        unstructured_query=unstructured_query or "None",
        database_results_json=results_json
    )

    # Call the LLM
    try:
        # 1. Load the LLM using your loader
        llm = load_llm(CURRENT_LLM, temperature=0.1)

        # 2. Create LangChain messages
        messages = [
            SystemMessage(content=RESULT_SYNTHESIZER_SYSTEM_PROMPT),
            HumanMessage(content=human_prompt)
        ]
        
        print(f"\n[LLM Call] Invoking {CURRENT_LLM} for synthesis...")
        
        # 3. Invoke the model
        response = llm.invoke(messages)
        
        # 4. Return the text content
        final_answer = response.content
        return final_answer
        
    except Exception as e:
        print(f"[ERROR] Final LLM synthesis failed: {e}")
        if "GEMINI_API_KEY" in str(e):
            print("CRITICAL: 'GEMINI_API_KEY not found' error.")
            print("Please make sure GEMINI_API_KEY is set in your .env file.")
        return "I was able to retrieve the data, but I encountered an error when trying to formulate a final answer. Here is the raw data: " + results_json