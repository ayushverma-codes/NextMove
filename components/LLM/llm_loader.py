import os
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
# from langchain_ollama import ChatOllama


def load_llm(llm_name: str, temperature: float = 0.0):
    """
    Load and return a LangChain LLM instance (Gemini or Ollama)
    based on the provided llm_name.

    Args:
        llm_name (str): Name of the model. Example: "gemini" or "ollama"
        temperature (float): Controls randomness in output.

    Returns:
        An initialized LLM object ready for chaining.
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

    elif "ollama" in llm_name or "llama" in llm_name:
        return ChatOllama(
            model="llama3.1",
            temperature=temperature,
        )

    else:
        raise ValueError(f"Unsupported LLM name: {llm_name}")
