from langchain_core.prompts import ChatPromptTemplate
from components.LLM.llm_loader import load_llm
from constants import *
from components.analyzer_and_decomposer.query_analyzer import query_analyze

# Load Gemini or Ollama dynamically
# llm = load_llm(CURRENT_LLM)

natural_query = "Find the job in Princeton, NJ with a minimum salary of $17, list its company benefits, and explain what a 'Marketing Coordinator' typically does."

# Run the query through query_analyze
result = query_analyze(natural_query)

# Print the result to check if it works
print("Result from query_analyze:")
print(result)