"""Explicit inference providers. No silent cloud calls or invented token counts."""
from __future__ import annotations

import json
import os
from pathlib import Path
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]


class InferenceClient:
    def __init__(self, provider=None, session=None):
        load_dotenv(ROOT / ".env")
        self.provider = provider or os.getenv("LLM_PROVIDER", "ollama")
        if self.provider not in {"ollama", "openai"}:
            raise ValueError("LLM_PROVIDER must be ollama or openai")
        self.model = os.getenv("OPENAI_MODEL", "gpt-5.4-mini") if self.provider == "openai" else os.getenv("OLLAMA_MODEL", "llama3.2:3b")
        self.session = session or requests.Session()
        self.session.trust_env = False
        self.tokens = 0

    def json(self, instructions, evidence, schema, _retry=False):
        """Ground generation in supplied evidence; caller must validate semantics."""
        prompt = json.dumps(evidence, ensure_ascii=False)
        if self.provider == "openai":
            key = os.getenv("OPENAI_API_KEY")
            if not key:
                raise RuntimeError("Set OPENAI_API_KEY in local .env to use OpenAI; or select LLM_PROVIDER=ollama")
            response = self.session.post("https://api.openai.com/v1/responses", headers={"Authorization": f"Bearer {key}"}, json={
                "model": self.model, "instructions": instructions, "input": prompt,
                "store": False, "max_output_tokens": 2400,
                "reasoning": {"effort": "low"},
                "text": {"format": {"type": "json_schema", "name": "investigation", "strict": True, "schema": schema}},
            }, timeout=(10, 180))
            response.raise_for_status()
            body = response.json()
            self.tokens += body.get("usage", {}).get("total_tokens", 0)
            if body.get("status") != "completed":
                raise RuntimeError("OpenAI response incomplete; no decision accepted")
            text = "".join(c.get("text", "") for item in body.get("output", []) for c in item.get("content", []) if c.get("type") == "output_text")
        else:
            host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
            response = self.session.post(host + "/api/chat", json={
                "model": self.model, "stream": False, "format": schema,
                "messages": [{"role": "system", "content": instructions}, {"role": "user", "content": prompt}],
                "keep_alive": 0,
                "options": {"temperature": 0, "num_ctx": 4096, "num_predict": 1400, "num_gpu": int(os.getenv('OLLAMA_NUM_GPU', '0'))},
            }, timeout=(10, 180))
            if not response.ok:
                raise RuntimeError('Local inference failed: '+response.text[:400])
            body = response.json()
            self.tokens += body.get("prompt_eval_count", 0) + body.get("eval_count", 0)
            text = body["message"]["content"]
        try:
            result = json.loads(text)
        except ValueError:
            if self.provider == 'ollama' and not _retry:
                return self.json(instructions+' Keep every field concise. Return only the required JSON.', evidence, schema, True)
            raise RuntimeError('Model returned incomplete JSON after bounded retry; no decision accepted')
        from jsonschema import validate
        validate(result, schema)
        return result


def embed(texts):
    """Use the already installed Nomic model; do not download models implicitly."""
    session = requests.Session()
    session.trust_env = False
    response = session.post(os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/") + "/api/embed", json={
        "model": os.getenv("EMBEDDING_MODEL", "nomic-embed-text:latest"), "input": texts, "keep_alive": 0, "options": {"num_gpu": int(os.getenv('OLLAMA_NUM_GPU','0'))},
    }, timeout=(10, 180))
    response.raise_for_status()
    return response.json()["embeddings"]
