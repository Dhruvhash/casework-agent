# Inference options

The default is local Ollama with `llama3.2:3b`. Embeddings use the already installed `nomic-embed-text:latest` model (768 dimensions). Neither adapter downloads models automatically. These local calls have no API fee. Model memory is released after each call to fit the development laptop.

For stronger inference, set these values in the existing local `.env`:

```dotenv
LLM_PROVIDER=openai
OPENAI_MODEL=gpt-5.4-mini
OPENAI_API_KEY=your_key_here
```

API usage is billed separately. The application never switches from local to paid inference silently. Keep `.env` private. An absent key fails explicitly. The provider and model used are recorded in each investigation trace.

Both providers receive graph facts and retrieved policy/history context. A deterministic controller applies approval routes and exposure thresholds. Model output cannot issue arbitrary GSQL or banking actions. Structured output is validated; incomplete local output has at most one retry. Token counts come from provider usage fields, including the retry.

The default probability is an explainable heuristic, not a calibrated fraud model. A stronger language model does not establish benchmark accuracy. Customer confirmation/denial options are simulations and remain labeled as such.

Model capabilities: https://developers.openai.com/api/docs/models/gpt-5.4-mini
