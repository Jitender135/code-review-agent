import json
from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

MERGER_PROMPT = """You are a senior engineering lead doing a final code review summary.
You have received results from two specialized agents — a bug detector and a security scanner.

Language: {language}

Bug issues found:
{bug_issues}

Security issues found:
{security_issues}

Similar past PRs from this repo for context:
{context}

Your job:
- Combine all issues into one coherent review
- Remove any duplicates
- Rank by severity (errors first, then warnings, then suggestions)
- For each issue, include the exact problematic code in line_hint
- For each issue, include a concrete fix with corrected code in the fix field
- Write a clear 2-3 sentence summary like a senior engineer would write

Return ONLY valid JSON, no explanation, no markdown:
{{
  "summary": "2-3 sentence overall assessment written like a senior engineer",
  "issues": [
    {{
      "file": "filename",
      "severity": "error or warning or suggestion",
      "category": "bug or security or style",
      "line_hint": "the exact problematic line of code",
      "comment": "clear explanation of what is wrong",
      "fix": "the corrected code or approach"
    }}
  ],
  "approved": true or false
}}

Rules:
- approved must be false if there are any error severity issues
- line_hint must be the actual code from the diff, not a description
- fix must be actual corrected code, not just advice
- Write like a senior engineer, not a bot
"""


def merge_results(
    bug_issues: list,
    security_issues: list,
    similar_prs: list,
    language: str
) -> dict:
    context_str = "\n---\n".join(similar_prs) if similar_prs else "No past PRs available"

    prompt = MERGER_PROMPT.format(
        language=language,
        bug_issues=json.dumps(bug_issues, indent=2) if bug_issues else "None found",
        security_issues=json.dumps(security_issues, indent=2) if security_issues else "None found",
        context=context_str[:2000]
    )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.2
    )

    raw = response.choices[0].message.content.strip()

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        print(f"Merger JSON parse error: {raw[:200]}")
        return {
            "summary": "Review completed with parsing issues.",
            "issues": bug_issues + security_issues,
            "approved": False
        }