import os
from github import Github, Auth
from dotenv import load_dotenv

load_dotenv()

APP_ID = os.getenv("APP_ID")
PRIVATE_KEY_PATH = os.getenv("PRIVATE_KEY_PATH")


def get_github_client(installation_id: int):
    with open(PRIVATE_KEY_PATH, "r") as f:
        private_key = f.read()
    auth = Auth.AppInstallationAuth(
        Auth.AppAuth(APP_ID, private_key),
        installation_id
    )
    return Github(auth=auth)


def format_issue(issue: dict) -> str:
    category = issue.get("category", "general").upper()
    severity = issue.get("severity", "warning")
    file = issue.get("file", "unknown")
    comment = issue.get("comment", "")
    line_hint = issue.get("line_hint", "")
    fix = issue.get("fix", "")

    if severity == "error":
        icon = "🚨"
    elif severity == "warning":
        icon = "⚠️"
    else:
        icon = "💡"

    block = f"{icon} **[{category}]** `{file}`\n\n"

    if line_hint:
        block += f"**Found:**\n```\n{line_hint}\n```\n\n"

    block += f"**Issue:** {comment}\n\n"

    if fix:
        block += f"**Fix:**\n```\n{fix}\n```\n\n"

    block += "---\n"
    return block


def post_review(repo_name: str, pr_number: int, review: dict, installation_id: int):
    gh = get_github_client(installation_id)
    repo = gh.get_repo(repo_name)
    pr = repo.get_pull(pr_number)

    issues = review.get("issues", [])
    errors = [i for i in issues if i.get("severity") == "error"]
    warnings = [i for i in issues if i.get("severity") == "warning"]
    suggestions = [i for i in issues if i.get("severity") == "suggestion"]

    approved = review.get("approved", False)
    verdict_icon = "✅" if approved else "❌"
    verdict_text = "Approved" if approved else "Changes Requested"

    body = "## 🤖 AI Code Review\n\n"
    body += f"> {review.get('summary', '')}\n\n"
    body += "---\n\n"

    if not issues:
        body += "### ✅ Everything looks good\n\n"
        body += "No bugs, security issues, or style problems found. Nice work!\n\n"
    else:
        if errors:
            body += f"### 🚨 Errors ({len(errors)})\n\n"
            body += "*These must be fixed before merging.*\n\n"
            for issue in errors:
                body += format_issue(issue)

        if warnings:
            body += f"\n### ⚠️ Warnings ({len(warnings)})\n\n"
            body += "*These should be addressed.*\n\n"
            for issue in warnings:
                body += format_issue(issue)

        if suggestions:
            body += f"\n### 💡 Suggestions ({len(suggestions)})\n\n"
            body += "*Optional improvements.*\n\n"
            for issue in suggestions:
                body += format_issue(issue)

    body += f"\n---\n### {verdict_icon} Verdict: {verdict_text}\n"

    if not approved and errors:
        body += f"\n*{len(errors)} error(s) must be resolved before this PR can be merged.*\n"

    pr.create_issue_comment(body)
    print(f"Review posted to PR #{pr_number}")