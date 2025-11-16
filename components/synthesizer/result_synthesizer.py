# D:\Projects\NextMove\components\synthesizer\result_synthesizer.py

import json
from typing import Dict, Any, List
from constants import (
    RESULT_SYNTHESIZER_SYSTEM_PROMPT,
    RESULT_SYNTHESIZER_HUMAN_PROMPT,
    CURRENT_LLM
)
from components.LLM.llm_loader import load_llm
from langchain_core.messages import SystemMessage, HumanMessage


def synthesize_results(
    natural_language_query: str,
    unstructured_query: str,
    database_results: Dict[str, Any]
) -> Dict[str, Any]:  # <-- MODIFIED: Return type is now a Dict
    """
    Takes retrieved data, calls LLM, and returns a dictionary with
    the final answer and the prompts used.
    """
    print("[STEP 4] Synthesizing final answer with LLM...")

    try:
        results_json = json.dumps(database_results, indent=2, default=str)
    except Exception as e:
        print(f"[WARN] Could not serialize DB results to JSON: {e}")
        results_json = str(database_results)

    # --- Format prompts *before* the try block so they are available in 'except' ---
    system_prompt_str = RESULT_SYNTHESIZER_SYSTEM_PROMPT
    human_prompt_str = RESULT_SYNTHESIZER_HUMAN_PROMPT.format(
        natural_language_query=natural_language_query,
        unstructured_query=unstructured_query or "None",
        database_results_json=results_json
    )
    # ---

    try:
        # 1. Load the LLM using your loader
        llm = load_llm(CURRENT_LLM, temperature=0.1)

        # 2. Create LangChain messages
        messages = [
            SystemMessage(content=system_prompt_str),
            HumanMessage(content=human_prompt_str)
        ]
        
        print(f"\n[LLM Call] Invoking {CURRENT_LLM} for synthesis...")
        
        # 3. Invoke the model
        response = llm.invoke(messages)
        
        # 4. Get the text content
        final_answer = response.content
        
        # 5. MODIFIED: Return a dictionary
        return {
            "final_answer": final_answer,
            "prompts_used": {
                "system": system_prompt_str,
                "human": human_prompt_str
            }
        }
        
    except Exception as e:
        print(f"[ERROR] Final LLM synthesis failed: {e}")
        if "GEMINI_API_KEY" in str(e):
            print("CRITICAL: 'GEMINI_API_KEY not found' error.")
            print("Please make sure GEMINI_API_KEY is set in your .env file.")
        
        # MODIFIED: Return a dictionary even on error
        return {
            "final_answer": "I was able to retrieve the data, but I encountered an error when trying to formulate a final answer. Here is the raw data: " + results_json,
            "prompts_used": {
                "system": system_prompt_str,
                "human": human_prompt_str,
                "error": str(e)
            }
        }