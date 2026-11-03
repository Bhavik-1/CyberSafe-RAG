
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=True)

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

if not API_KEY:
    raise ValueError("GEMINI_API_KEY missing!")

print("Model:", MODEL)
print("Testing Gemini Interactions API...")

try:
    client = genai.Client(
        api_key=API_KEY,
        http_options={"timeout": 120000}
    )

    interaction = client.interactions.create(
        model=MODEL,
        input="Reply with only: Gemini is working."
    )

    print("\nSUCCESS!")
    print(interaction.output_text)

except Exception as error:
    print("\nREQUEST FAILED")
    print(type(error).__name__)
    print(str(error))
