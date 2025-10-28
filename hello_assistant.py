import os
from dotenv import load_dotenv
from openai import OpenAI

# Load your API key from the .env file
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Simple test message
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Say hello to my information systems class!"}]
)

# Print the model's reply
print(response.choices[0].message.content)
