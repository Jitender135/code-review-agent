import os
from github import Github, Auth
from dotenv import load_dotenv
import jwt
import time

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


def post_review(repo_name: str, pr_number: int, review: dict, installation_id: int):
    gh = get_github_client(installation_id)
    repo = gh.get_repo(repo_name)
    pr = repo.get_pull(pr_number)

    body = "## AI Code Review\n\n"
    body += f"**Summary:** {review['summary']}\n\n"

    if review.get("issues"):
        body += "### Issues Found\n\n"
        for issue in review["issues"]:
            emoji = "🚨" if issue["severity"] == "error" else "⚠️" if issue["severity"] == "warning" else "💡"
            body += f"{emoji} **{issue['severity'].upper()}** in `{issue['file']}`\n"
            body += f"> {issue['comment']}\n\n"
    else:
        body += "### No issues found\n\n"

    verdict = "✅ **Approved**" if review.get("approved") else "❌ **Changes Requested**"
    body += f"### Verdict: {verdict}\n"

    pr.create_issue_comment(body)
    print(f"Review posted to PR #{pr_number}")