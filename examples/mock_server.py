"""Mock LLM server for trying llmcomply without API keys.

Run with:  uvicorn examples.mock_server:app --reload
Requires the dev extras:  pip install -e ".[dev]"

It accepts the same JSON body that llmcomply.Suite sends: {"prompt": "..."}.
"""

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="llmcomply mock LLM")


class GenerateRequest(BaseModel):
    prompt: str


@app.post("/generate")
def generate(req: GenerateRequest) -> dict:
    return {"response": f"Mock response to: {req.prompt}"}
