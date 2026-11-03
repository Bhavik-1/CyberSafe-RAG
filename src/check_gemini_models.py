
import os
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY"),
    http_options=types.HttpOptions(timeout=60000)
)

print("Checking available Gemini models...")

try:
    for model in client.models.list():
        if "flash" in model.name.lower():
            print(model.name)

except Exception as e:
    print(type(e).__name__, str(e))
