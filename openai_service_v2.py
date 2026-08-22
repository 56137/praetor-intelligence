import os
from openai import OpenAI


def _client():
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    return OpenAI(api_key=api_key)


def analyze_security_report(report_text: str, model: str | None = None) -> str:
    """Turn an existing PRAETOR scan/report into an executive analysis."""
    if not report_text or not report_text.strip():
        raise ValueError("report_text cannot be empty")

    model = model or os.getenv("OPENAI_MODEL", "gpt-5.6-luna")
    response = _client().responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": (
                    "You are PRAETOR Intelligence's cybersecurity report analyst. "
                    "Analyze only the supplied report data. Do not invent findings. "
                    "Return a concise executive summary, top risks, business impact, "
                    "and three prioritized remediation actions."
                ),
            },
            {"role": "user", "content": report_text},
        ],
    )
    return response.output_text
