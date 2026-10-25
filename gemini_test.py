
import os

from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError(
        "GEMINI_API_KEY not found. Check your .env file."
    )

client = genai.Client(api_key=api_key)

response = client.models.generate_content(
    model="gemini-3.8-flash",
    contents=(
        "Extract the governing jurisdiction from this sentence: "
        "'This Agreement shall be governed by the laws of Nevada.' "
        "Return only the jurisdiction name."
    ),
)

print("Gemini response:")
print(response.text)
