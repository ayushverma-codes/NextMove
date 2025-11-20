import json
import os
from langchain_core.messages import SystemMessage, HumanMessage
from components.LLM.llm_loader import load_llm
from constants import (
    HISTORY_FILE_PATH, 
    HISTORY_LIMIT_K, 
    CURRENT_LLM, 
    CURRENT_PROMPTS
)

# Safety Limits
MAX_STORED_RESPONSE_LEN = 1500  # Max chars to save per AI response in JSON
MAX_CONTEXT_WINDOW_CHARS = 4000 # Max chars to send to Query Analyzer (~1000 tokens)

class HistoryHandler:
    def __init__(self):
        self.file_path = HISTORY_FILE_PATH
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
        Returns a safe string representation of history.
        Prioritizes the Summary and the NEWEST turns. 
        Drops older 'recent' turns if they exceed MAX_CONTEXT_WINDOW_CHARS.
        """
        # 1. Start with the Summary
        context_str = ""
        if self.summary:
            context_str += f"PREVIOUS SUMMARY: {self.summary}\n\n"
        
        if not self.recent_turns:
            return context_str if context_str else ""

        # 2. Build Recent Log (Reverse order: Newest -> Oldest to check size)
        turns_text_list = []
        current_length = len(context_str)
        
        # Iterate backwards (newest first)
        for turn in reversed(self.recent_turns):
            turn_text = f"User: {turn['user']}\nAI: {turn['ai']}\n"
            
            # Check if adding this turn exceeds the safety limit
            if current_length + len(turn_text) < MAX_CONTEXT_WINDOW_CHARS:
                turns_text_list.insert(0, turn_text) # Prepend to keep chronological order
                current_length += len(turn_text)
            else:
                # If we hit the limit, stop adding older turns.
                # We prefer keeping the newest context over the oldest "recent" context.
                break
        
        if turns_text_list:
            context_str += "RECENT INTERACTION LOG:\n" + "".join(turns_text_list)
        
        return context_str

    def add_interaction(self, user_query: str, ai_response: str):
        """
        Adds a turn, truncating massive responses to save space,
        and triggers summarization if K is reached.
        """
        
        # --- SAFETY TRUNCATION ---
        # If AI response is too long (e.g., giant SQL error or 50 job listings), 
        # truncate the middle to preserve start (context) and end (conclusion).
        clean_response = ai_response
        if len(ai_response) > MAX_STORED_RESPONSE_LEN:
            keep = MAX_STORED_RESPONSE_LEN // 2
            clean_response = ai_response[:keep] + "\n... [RESPONSE TRUNCATED FOR MEMORY] ...\n" + ai_response[-keep:]

        self.recent_turns.append({
            "user": user_query,
            "ai": clean_response
        })
        
        # Check if limit reached
        if len(self.recent_turns) >= self.limit:
            print(f"[History] Limit {self.limit} reached. Summarizing...")
            self._summarize_and_prune()
        
        self._save_history()

    def _summarize_and_prune(self):
        """Calls LLM to condense recent turns + old summary into new summary."""
        system_prompt = CURRENT_PROMPTS["summarizer"]
        
        # We use the full recent turns here because the Summarizer LLM usually has 
        # a larger context window and needs full details to create a good summary.
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
            
            # Update state
            self.summary = new_summary
            self.recent_turns = [] # Clear recent turns after summarization
            print(f"[History] Summary updated.")
            
        except Exception as e:
            print(f"[Error] Failed to summarize history: {e}")
            # Do not clear recent_turns on failure