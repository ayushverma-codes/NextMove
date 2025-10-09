from langchain_core.prompts import ChatPromptTemplate
from components.llm_loader import load_llm
from constants import *

# Load Gemini or Ollama dynamically
llm = load_llm(CURRENT_LLM)

response = llm.invoke("who are you")

print(response)
# # Define prompt
# prompt = ChatPromptTemplate.from_messages([
#     ("system", "You are a helpful assistant that translates {input_language} to {output_language}."),
#     ("human", "{input}")
# ])

# # Create a chain
# chain = prompt | llm

# # Run example
# response = chain.invoke({
#     "input_language": "English",
#     "output_language": "German",
#     "input": "I love programming."
# })

# print(response.content)
