#
#Entrypoint shim.
#Imports the canonical FastAPI app from app.server for uvicorn compatibility.
#


from fastapi import FastAPI
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Project Blackboard API is live"}

@app.get("/ask")
def ask(question: str):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": question}]
    )
    return {"answer": response.choices[0].message.content}

