# D:\Projects\NextMove\components\synthesizer\result_synthesizer.py

import json
from typing import Dict, Any, List
from constants import (
    CURRENT_PROMPTS,  # <-- UPDATED: Import the dynamic prompt registry
    RESULT_SYNTHESIZER_HUMAN_PROMPT,
    CURRENT_LLM
)
from components.LLM.llm_loader import load_llm
from langchain_core.messages import SystemMessage, HumanMessage


def synthesize_results(
    natural_language_query: str,
    unstructured_query: str,
    database_results: Dict[str, Any]
) -> Dict[str, Any]:
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
    
    # 1. Retrieve the correct System Prompt dynamically based on CURRENT_LLM
    system_prompt_str = CURRENT_PROMPTS["synthesizer_system"]
    
    human_prompt_str = RESULT_SYNTHESIZER_HUMAN_PROMPT.format(
        natural_language_query=natural_language_query,
        unstructured_query=unstructured_query or "None",
        database_results_json=results_json
    )
    # ---

    try:
        # 2. Load the LLM using your loader
        llm = load_llm(CURRENT_LLM, temperature=0.1)

        # 3. Create LangChain messages
        messages = [
            SystemMessage(content=system_prompt_str),
            HumanMessage(content=human_prompt_str)
        ]
        
        print(f"\n[LLM Call] Invoking {CURRENT_LLM} for synthesis...")
        
        # 4. Invoke the model
        response = llm.invoke(messages)
        
        # 5. Get the text content
        final_answer = response.content
        
        # 6. Return a dictionary
        return {
            "final_answer": final_answer,
            "prompts_used": {
                "system": system_prompt_str,
                "human": human_prompt_str
            }
        }
        
    except Exception as e:
        print(f"[ERROR] Final LLM synthesis failed: {e}")
        if "GEMINI_API_KEY" in str(e) or "GROQ_API_KEY" in str(e):
            print(f"CRITICAL: API Key for {CURRENT_LLM} not found or invalid.")
            print("Please make sure your API keys are set in the .env file.")
        
        # Return a dictionary even on error
        return {
            "final_answer": "I was able to retrieve the data, but I encountered an error when trying to formulate a final answer. Here is the raw data: " + results_json,
            "prompts_used": {
                "system": system_prompt_str,
                "human": human_prompt_str,
                "error": str(e)
            }
        }