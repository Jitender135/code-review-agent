import os
from github import Github, Auth
from dotenv import load_dotenv
from agents.diff_parser import parse_diff_positions, find_position

load_dotenv()

APP_ID = os.getenv("APP_ID")
PRIVATE_KEY_PATH = os.getenv("PRIVATE_KEY_PATH")
BOT_HEADER = "## 🤖 AI Code Review"


def get_github_client(installation_id: int):
    with open(PRIVATE_KEY_PATH, "r") as f:
        private_key = f.read()
    auth = Auth.AppInstallationAuth(
        Auth.AppAuth(APP_ID, private_key),
        installation_id
    )
    return Github(auth=auth)


def build_inline_comment(issue: dict) -> str:
    category = issue.get("category", "general").upper()
    severity = issue.get("severity", "warning")
    comment = issue.get("comment", "")
    fix = issue.get("fix", "")

    icon = "🚨" if severity == "error" else "⚠️" if severity == "warning" else "💡"

    body = f"{icon} **[{category}]** {comment}\n\n"

    if fix:
        body += f"**Fix:**\n```\n{fix}\n```"

    return body


def calculate_health_score(issues: list) -> int:
    errors = len([i for i in issues if i.get("severity") == "error"])
    warnings = len([i for i in issues if i.get("severity") == "warning"])
    suggestions = len([i for i in issues if i.get("severity") == "suggestion"])
    score = 100 - (errors * 20) - (warnings * 8) - (suggestions * 3)
    return max(0, min(100, score))


def build_summary_comment(review: dict, health_score: int, inline_count: int) -> str:
    issues = review.get("issues", [])
    errors = [i for i in issues if i.get("severity") == "error"]
    warnings = [i for i in issues if i.get("severity") == "warning"]
    suggestions = [i for i in issues if i.get("severity") == "suggestion"]
    fallback_issues = [i for i in issues if not i.get("_inlined", False)]

    approved = review.get("approved", False)
    verdict_icon = "✅" if approved else "❌"
    verdict_text = "Approved" if approved else "Changes Requested"

    filled = int(health_score / 10)
    bar = "█" * filled + "░" * (10 - filled)

    body = f"{BOT_HEADER}\n\n"
    body += f"### PR Health Score: `{health_score}/100`\n"
    if health_score >= 80:
        body += f"`{bar}` Great shape!\n\n"
    elif health_score >= 60:
        body += f"`{bar}` Needs some work.\n\n"
    else:
        body += f"`{bar}` Significant issues found.\n\n"

    body += f"> {review.get('summary', '')}\n\n"
    body += "---\n\n"

    if errors:
        body += f"### 🎯 Priority: Fix errors first\n\n"
        body += f"This PR has **{len(errors)} error(s)** that must be resolved before reviewing the {len(warnings)} warning(s) and {len(suggestions)} suggestion(s).\n\n"

    if issues:
        body += "### 📋 Issues Summary\n\n"
        body += "| Severity | Count | Action |\n"
        body += "|----------|-------|--------|\n"
        if errors:
            body += f"| 🚨 Error | {len(errors)} | Must fix before merge |\n"
        if warnings:
            body += f"| ⚠️ Warning | {len(warnings)} | Should fix |\n"
        if suggestions:
            body += f"| 💡 Suggestion | {len(suggestions)} | Optional |\n"
        body += "\n"

    if inline_count > 0:
        body += f"📌 *{inline_count} inline comment(s) posted directly on the relevant lines above.*\n\n"

    if fallback_issues:
        body += "---\n\n### Issues without line reference\n\n"
        for issue in fallback_issues:
            category = issue.get("category", "general").upper()
            severity = issue.get("severity", "warning")
            icon = "🚨" if severity == "error" else "⚠️" if severity == "warning" else "💡"
            body += f"{icon} **[{category}]** `{issue.get('file', 'unknown')}`\n\n"
            body += f"> {issue.get('comment', '')}\n\n"
            if issue.get("fix"):
                body += f"**Fix:** `{issue.get('fix')}`\n\n"
            body += "---\n"

    body += f"\n### {verdict_icon} Verdict: {verdict_text}\n"
    if not approved and errors:
        body += f"\n*Resolve {len(errors)} error(s) to unlock approval.*\n"

    return body


def find_existing_bot_comment(pr):
    for comment in pr.get_issue_comments():
        if comment.body.startswith(BOT_HEADER):
            return comment
    return None

def delete_old_inline_comments(pr, gh_client, repo):
    try:
        reviews = pr.get_reviews()
        for review in reviews:
            if review.user.login.endswith("[bot]") or "bot" in review.user.login.lower():
                # delete all comments from this review
                pass
        
        # delete inline review comments from our bot
        for comment in pr.get_review_comments():
            try:
                # check if it's from our bot by looking for our icon
                if "🚨" in comment.body or "⚠️" in comment.body or "💡" in comment.body:
                    comment.delete()
            except Exception as e:
                print(f"Could not delete comment: {e}")
    except Exception as e:
        print(f"Error cleaning old comments: {e}")


def post_review(repo_name: str, pr_number: int, review: dict, installation_id: int, diff: str = ""):
    gh = get_github_client(installation_id)
    repo = gh.get_repo(repo_name)
    pr = repo.get_pull(pr_number)
    commit = list(pr.get_commits())[-1]

    # clean old inline comments first
    print("Cleaning old inline comments...")
    delete_old_inline_comments(pr, gh, repo)

    diff_map = parse_diff_positions(diff) if diff else {}
    issues = review.get("issues", [])

    print(f"Diff map keys: {list(diff_map.keys())}")
    print(f"Issues: {[(i.get('file'), i.get('line_hint','')[:30]) for i in issues]}")

    inline_comments = []
    inline_count = 0

    for issue in issues:
        filename = issue.get("file", "")
        line_hint = issue.get("line_hint", "")
        position = find_position(diff_map, filename, line_hint)

        print(f"  {filename} | '{line_hint[:30]}' → position {position}")

        if position:
            inline_comments.append({
                "path": filename,
                "position": position,
                "body": build_inline_comment(issue)
            })
            issue["_inlined"] = True
            inline_count += 1
        else:
            issue["_inlined"] = False

    if inline_comments:
        try:
            pr.create_review(
                commit=commit,
                body="",
                event="COMMENT",
                comments=inline_comments
            )
            print(f"Posted {inline_count} inline comments")
        except Exception as e:
            print(f"Inline comment error: {e}")
            for issue in issues:
                issue["_inlined"] = False
            inline_count = 0

    health_score = calculate_health_score(issues)
    summary = build_summary_comment(review, health_score, inline_count)
    existing = find_existing_bot_comment(pr)

    if existing:
        existing.edit(summary)
        print(f"Updated summary comment on PR #{pr_number}")
    else:
        pr.create_issue_comment(summary)
        print(f"Posted summary comment on PR #{pr_number}")