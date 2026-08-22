import os
from openai import OpenAI


def _client():
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    return OpenAI(api_key=api_key)


def analyze_security_report(report_text: str, model: str = "gpt-5-mini") -> str:
    """Turn an existing PRAETOR scan/report into a concise executive analysis."""
    if not report_text or not report_text.strip():
        raise ValueError("report_text cannot be empty")

    response = _client().responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": (
                    "You are PRAETOR Intelligence's cybersecurity report analyst. "
                    "Analyze only the supplied report data. Do not invent findings. "
                    "Return: executive summary, top risks, business impact, and "
                    "three prioritized remediation actions."
                ),
            },
            {
                "role": "user",
                "content": report_text,
            },
        ],
    )
    return response.output_text
