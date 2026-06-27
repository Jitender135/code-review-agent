import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

REVIEW_PROMPT = """You are a senior software engineer doing a code review.
Analyze the following PR diff and return ONLY valid JSON, nothing else.
No explanation, no markdown, just the raw JSON object.

Return this exact structure:
{{
  "summary": "2-3 sentence overall assessment of this PR",
  "issues": [
    {{
      "file": "filename here",
      "severity": "error or warning or suggestion",
      "comment": "specific actionable feedback"
    }}
  ],
  "approved": true or false
}}

Rules:
- If the diff looks good with no issues, return empty issues array and approved true
- severity must be exactly one of: error, warning, suggestion
- Be specific and helpful in comments
- If it is a markdown or readme file, check for clarity and formatting

PR Diff:
{diff}
"""

def review_diff(diff: str) -> dict:
    prompt = REVIEW_PROMPT.format(diff=diff[:8000])

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )

    raw = response.choices[0].message.content.strip()

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    return json.loads(raw.strip())