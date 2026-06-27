import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

REVIEW_PROMPT = """You are a senior software engineer doing a code review.
You have been given examples of good merged PRs from this repository to understand its conventions.

Similar past PRs from this repo for context:
{context}

Now analyze the following new PR diff and return ONLY valid JSON, nothing else.
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
- Use the past PRs as context for what good code looks like in this repo
- severity must be exactly one of: error, warning, suggestion
- Be specific and helpful in comments
- If no issues found, return empty issues array and approved true

PR Diff to review:
{diff}
"""

def review_diff(diff: str, context: list = []) -> dict:
    if context:
        context_str = "\n---\n".join(context)
    else:
        context_str = "No past PRs available for context."

    prompt = REVIEW_PROMPT.format(
        context=context_str[:3000],
        diff=diff[:6000]
    )

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