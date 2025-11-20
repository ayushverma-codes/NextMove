import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq 

def load_llm(llm_name: str, temperature: float = 0.0):
    """
    Load and return a LangChain LLM instance (Gemini or Ollama/Groq)
    based on the provided llm_name.
    """

    # Load .env from project root
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
    env_path = os.path.join(root_dir, ".env")
    load_dotenv(env_path)

    llm_name = llm_name.lower()

    if "gemini" in llm_name:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in .env")

        return ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=temperature,
            max_retries=2,
            google_api_key=api_key,
        )

    elif "groq" in llm_name:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in .env")
            
        # UPDATED: Switched to Llama 3.3 70B (Versatile) as the previous model is decommissioned
        return ChatGroq(
            model="llama-3.3-70b-versatile", 
            temperature=temperature,
            max_retries=2,
            api_key=api_key
        )

    else:
        raise ValueError(f"Unsupported LLM name: {llm_name}")