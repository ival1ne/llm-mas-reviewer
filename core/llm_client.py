from openai import OpenAI
from dotenv import load_dotenv
import os
load_dotenv()

client = OpenAI(
api_key = os.getenv("OPENAI_API_KEY", "lm-studio"),
base_url = os.getenv("OPENAI_BASE_URL")
)
def call_llm(prompt: str):
    response = client.chat.completions.create(
    model=os.getenv("OPENAI_MODEL", "qwen2.5-coder"),
    messages = [{
    "role" : "user",
    "content" : prompt}],
    temperature = 0.2,
    max_tokens=2000
    )
    return response.choices[0].message.content
