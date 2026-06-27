import json
from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SECURITY_PROMPT = """You are an expert security engineer specializing in finding vulnerabilities.
Your ONLY job is to find security vulnerabilities in this code diff — not bugs, not style, only security issues.

Language: {language}

Look specifically for:
- Hardcoded secrets, passwords, API keys, tokens
- SQL injection vulnerabilities
- Command injection vulnerabilities
- Cross-site scripting (XSS)
- Insecure deserialization
- Missing input validation or sanitization
- Exposed sensitive data in logs or error messages
- Insecure random number generation
- Missing authentication or authorization checks
- Insecure file operations or path traversal
- Use of deprecated or insecure cryptography
- Insecure HTTP instead of HTTPS
- Missing rate limiting
- Open redirects

Return ONLY valid JSON, no explanation, no markdown:
{{
  "issues": [
    {{
      "file": "filename",
      "line_hint": "the problematic code snippet",
      "severity": "error or warning",
      "vulnerability_type": "e.g sql_injection, hardcoded_secret, xss",
      "comment": "specific explanation of the vulnerability and how to fix it"
    }}
  ]
}}

If no vulnerabilities found, return:
{{
  "issues": []
}}

PR Diff:
{diff}
"""


def scan_security(diff: str, language: str) -> list:
    prompt = SECURITY_PROMPT.format(
        language=language,
        diff=diff[:6000]
    )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.1
    )

    raw = response.choices[0].message.content.strip()

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    try:
        result = json.loads(raw.strip())
        return result.get("issues", [])
    except json.JSONDecodeError:
        print(f"Security scanner JSON parse error: {raw[:200]}")
        return []