PRAETOR OpenAI integration

The OpenAI API key is supplied at runtime through Secret Manager as OPENAI_API_KEY.
The application endpoint is registered by openai_wsgi.py and exposes POST /ai/analyze.
The endpoint accepts JSON: {"report_text": "..."} and returns an executive analysis.
Default model: gpt-5.6-luna. Override with OPENAI_MODEL if needed.
