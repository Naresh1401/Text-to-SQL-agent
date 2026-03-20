import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from src.sql.text2sql import Text2SQLEngine, is_safe_sql

app = FastAPI(title="Text-to-SQL Agent", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_engine = None

def get_engine():
    global _engine
    if _engine is None:
        from openai import OpenAI
        class LLM:
            def __init__(self):
                self.client = OpenAI()
                self.model  = os.getenv("LLM_MODEL","gpt-4o-mini")
            def generate(self, system, user):
                r = self.client.chat.completions.create(
                    model=self.model, temperature=0.0, max_tokens=512,
                    messages=[{"role":"system","content":system},{"role":"user","content":user}],
                    response_format={"type":"json_object"})
                return r.choices[0].message.content
        _engine = Text2SQLEngine(LLM(), os.getenv("DB_PATH","./data/sample.db"))
    return _engine

class QueryRequest(BaseModel):
    question: str

@app.get("/health")
def health(): return {"status":"ok"}

@app.get("/schema")
def schema():
    e = get_engine()
    return {"tables": {t: [c["name"] for c in cols] for t,cols in e.schema.tables.items()}}

@app.post("/query")
def query(request: QueryRequest):
    if not request.question.strip():
        raise HTTPException(400, "Question cannot be empty")
    result = get_engine().query(request.question)
    return result.to_dict()

@app.post("/validate-sql")
def validate_sql(body: dict):
    sql = body.get("sql","")
    safe, err = is_safe_sql(sql)
    return {"safe": safe, "error": err}