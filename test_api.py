import os
from openai import OpenAI
from dotenv import load_dotenv, find_dotenv

# Load .env
load_dotenv(find_dotenv(), override=True)

# Get API key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("❌ No API key found. Check your .env file.")
    exit()

# Test OpenAI connection
client = OpenAI(api_key=api_key)

try:
    response = client.models.list()
    print("✅ API Key works! First 5 models:")
    for model in response.data[:5]:
        print("-", model.id)
except Exception as e:
    print("❌ Error:", e)