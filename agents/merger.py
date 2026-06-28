import json
from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

MERGER_PROMPT = """You are a senior engineering lead doing a final code review.
You have results from a bug detector and security scanner.

Language: {language}

Bug issues found:
{bug_issues}

Security issues found:
{security_issues}

Similar past PRs for context:
{context}

Rules:
- MAXIMUM 3 issues total in your output — pick only the most critical ones
- NEVER create two issues for the same line or function
- Combine related issues into one comment
- Each issue must be for a DIFFERENT line of code
- line_hint must be copied EXACTLY from the diff
- fix must be actual corrected code, short and clear
- summary must be 2 sentences max, written like a senior engineer
- approved is false if any errors exist

Return ONLY valid JSON:
{{
  "summary": "2 sentence assessment",
  "issues": [
    {{
      "file": "filename",
      "severity": "error or warning or suggestion",
      "category": "bug or security or style",
      "line_hint": "exact code from diff",
      "comment": "one clear sentence explaining the problem",
      "fix": "corrected code snippet"
    }}
  ],
  "approved": true or false
    }}
    """


def merge_results(
    bug_issues: list,
    security_issues: list,
    similar_prs: list,
    language: str,
    max_comments: int = 3
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
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1
    )

    raw = response.choices[0].message.content.strip()

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    try:
        result = json.loads(raw.strip())

        seen_lines = set()
        deduped = []
        for issue in result.get("issues", []):
            hint = issue.get("line_hint", "").strip()
            if hint not in seen_lines:
                seen_lines.add(hint)
                deduped.append(issue)

        result["issues"] = deduped[:max_comments]
        return result

    except json.JSONDecodeError:
        print(f"Merger JSON parse error: {raw[:200]}")
        return {
            "summary": "Review completed with parsing issues.",
            "issues": [],
            "approved": False
        }