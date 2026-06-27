import json
from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

BUG_PROMPT = """You are an expert software engineer specializing in finding bugs.
Your ONLY job is to find real bugs in this code diff — not style issues, not formatting, only actual bugs.

Language: {language}

Look specifically for:
- Null/None pointer dereferences
- Division by zero
- Off-by-one errors in loops or arrays
- Unhandled exceptions or missing try/catch
- Incorrect variable usage or typos in variable names
- Infinite loops
- Wrong comparison operators (= instead of ==)
- Missing return statements
- Incorrect data type usage
- Race conditions or concurrency issues
- Memory leaks (for C/C++/Rust)
- Unreachable code

Return ONLY valid JSON, no explanation, no markdown:
{{
  "issues": [
    {{
      "file": "filename",
      "line_hint": "the problematic code snippet",
      "severity": "error or warning",
      "bug_type": "type of bug e.g null_pointer, division_by_zero",
      "comment": "specific explanation of the bug and how to fix it"
    }}
  ]
}}

If no bugs found, return:
{{
  "issues": []
}}

PR Diff:
{diff}
"""


def detect_bugs(diff: str, language: str) -> list:
    prompt = BUG_PROMPT.format(
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
        print(f"Bug detector JSON parse error: {raw[:200]}")
        return []