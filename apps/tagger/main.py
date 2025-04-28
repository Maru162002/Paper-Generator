# apps/tagger/main.py
# ------------------------------------------------------------
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import os, json

# --- OpenAI (v1.x client) ------------------------------------
from openai import OpenAI           # pip install openai>=1.0.*
client = OpenAI()                   # reads OPENAI_API_KEY from env

# --- Mongo (optional) ---------------------------------------
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017")
mongo = AsyncIOMotorClient(MONGO_URI).paper_gen   # db: paper_gen

# ------------------------------------------------------------
app = FastAPI()

SYSTEM_PROMPT = """
You are an assistant that classifies Cambridge A-Level Mathematics questions.
Return JSON exactly: {"chapters":[...], "difficulty":"easy|medium|hard"}
"""

class Item(BaseModel):
    text: str
    marks: int

# -------------------- Routes --------------------------------
@app.post("/tag")
async def tag_q(item: Item):
    """Classify a question block into chapters & difficulty level."""
    response = client.chat.completions.create(      # NEW syntax
        model="gpt-3.5-turbo",
        temperature=0.2,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": f"{item.text}\nMarks:({item.marks})"}
        ],
    )

    try:
        payload = json.loads(response.choices[0].message.content)
    except json.JSONDecodeError:
        payload = {"chapters": [], "difficulty": "medium"}

    # Save (optional) — comment out if Mongo not running
    await mongo.questions.insert_one({**item.dict(), **payload})

    return payload

@app.get("/questions")
async def list_first(limit: int = 5) -> List[dict]:
    """Return the first N stored questions (debug helper)."""
    cursor = mongo.questions.find().limit(limit)
    return [doc async for doc in cursor]
