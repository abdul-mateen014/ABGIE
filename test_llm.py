
import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("LLM_API_KEY")

if not api_key:
    raise ValueError("LLM_API_KEY not found in .env")

client = genai.Client(api_key=api_key)

interaction = client.interactions.create(
    model="gemini-3.8-flash",
    input="Explain how AI works in a few words."
)

print(interaction.output_text)
