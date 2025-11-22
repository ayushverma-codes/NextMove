import json
import os
from langchain_core.messages import SystemMessage, HumanMessage
from components.LLM.llm_loader import load_llm
from constants import (
    HISTORY_DIR_PATH, 
    HISTORY_LIMIT_K, 
    CURRENT_LLM, 
    CURRENT_PROMPTS
)

# --- SAFETY LIMITS ---
MAX_STORED_RESPONSE_LEN = 1500  # Max chars to save per AI response (prevents bloat)
MAX_CONTEXT_CHARS = 6000        # Max characters allowed before forcing a summary (approx 1.5k tokens)

class HistoryHandler:
    def __init__(self, session_id: str = "default"):
        self.session_id = session_id
        self.file_path = os.path.join(HISTORY_DIR_PATH, f"chat_history_{session_id}.json")
        self.limit = HISTORY_LIMIT_K
        self.llm = load_llm(CURRENT_LLM, temperature=0.0)
        self._load_history()

    def _load_history(self):
        """Loads history from JSON or initializes empty structure."""
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.summary = data.get("summary", "")
                    self.recent_turns = data.get("recent_turns", [])
            except json.JSONDecodeError:
                self._init_empty_history()
        else:
            self._init_empty_history()

    def _init_empty_history(self):
        self.summary = ""
        self.recent_turns = []
        self._save_history()

    def _save_history(self):
        """Persists current state to disk."""
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        data = {
            "summary": self.summary,
            "recent_turns": self.recent_turns
        }
        with open(self.file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def get_context_string(self) -> str:
        """
        Returns the formatted context.
        **LOGIC CHECK (ii):** If context > MAX_CONTEXT_CHARS, force summary immediately.
        """
        # 1. Construct the raw context string
        context_str = ""
        if self.summary:
            context_str += f"PREVIOUS SUMMARY: {self.summary}\n\n"
        
        if self.recent_turns:
            turns_text = "\n".join([f"User: {t['user']}\nAI: {t['ai']}\n" for t in self.recent_turns])
            context_str += f"RECENT INTERACTION LOG:\n{turns_text}"

        # 2. CHECK LENGTH
        if len(context_str) > MAX_CONTEXT_CHARS:
            print(f"[History] Context length ({len(context_str)}) exceeds limit ({MAX_CONTEXT_CHARS}). Forcing summarization...")
            self._summarize_and_prune() # <--- Consolidates history
            
            # Re-construct the string (It will now contain only the new Summary)
            context_str = f"PREVIOUS SUMMARY: {self.summary}\n\n"
        
        return context_str

    def add_interaction(self, user_query: str, ai_response: str):
        """
        Adds a turn and checks if K limit is reached.
        """
        # Safety: Truncate massive responses before storing
        clean_response = ai_response
        if len(ai_response) > MAX_STORED_RESPONSE_LEN:
            keep = MAX_STORED_RESPONSE_LEN // 2
            clean_response = ai_response[:keep] + "\n... [TRUNCATED] ...\n" + ai_response[-keep:]

        self.recent_turns.append({
            "user": user_query,
            "ai": clean_response
        })
        
        # **LOGIC CHECK (i):** Check Turn Count Limit
        if len(self.recent_turns) >= self.limit:
            print(f"[History] Turn limit {self.limit} reached. Summarizing...")
            self._summarize_and_prune()
        
        self._save_history()

    def _summarize_and_prune(self):
        """
        Uses LLM to merge (Summary + Recent Turns) -> (New Summary).
        Clears Recent Turns.
        """
        system_prompt = CURRENT_PROMPTS["summarizer"]
        
        recent_text = "\n".join([f"User: {t['user']}\nAI: {t['ai']}" for t in self.recent_turns])
        
        human_input = (
            f"Current Summary: {self.summary if self.summary else 'None'}\n\n"
            f"Recent Interactions to merge:\n{recent_text}"
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_input)
        ]

        try:
            response = self.llm.invoke(messages)
            new_summary = response.content.strip()
            
            # Update State
            self.summary = new_summary
            self.recent_turns = [] # Clear buffer
            
            print(f"[History] Summary updated successfully.")
            self._save_history() # Save immediately
            
        except Exception as e:
            print(f"[Error] Failed to summarize history: {e}")