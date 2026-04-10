from openai import OpenAI
from dotenv import load_dotenv
import os
load_dotenv()

client = OpenAI(
api_key = os.getenv("OPENAI_API_KEY"),
base_url = os.getenv("OPENAI_BASE_URL")
)
def call_llm(prompt: str):
    response = client.chat.completions.create(
    model = "deepseek-chat",
    messages = [{
    "role" : "user",
    "content" : prompt}],
    max_tokens=800
    )
    return response.choices[0].message.content
