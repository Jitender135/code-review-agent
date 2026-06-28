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

    # extract first sentence only — keep it short
    short_comment = comment.split(".")[0].strip()

    # extract short fix hint — first line only
    short_fix = fix.split("\n")[0].strip() if fix else ""

    body = f"{icon} **{category} — {severity.upper()}**\n"
    body += f"{short_comment}.\n\n"

    if short_fix:
        body += f"💡 **Hint:** `{short_fix}`"

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
    verdict_text = "Approved — ready to merge" if approved else "Changes Requested"

    filled = int(health_score / 10)
    bar = "█" * filled + "░" * (10 - filled)

    body = f"{BOT_HEADER}\n\n"

    # health score — one line
    body += f"**Health Score:** `{bar}` {health_score}/100"
    if health_score >= 80:
        body += " 🟢\n\n"
    elif health_score >= 50:
        body += " 🟡\n\n"
    else:
        body += " 🔴\n\n"

    # summary — one line
    summary = review.get("summary", "")
    short_summary = summary.split(".")[0].strip()
    body += f"> {short_summary}.\n\n"

    # quick stats — one line
    stats = []
    if errors:
        stats.append(f"🚨 {len(errors)} error{'s' if len(errors) > 1 else ''}")
    if warnings:
        stats.append(f"⚠️ {len(warnings)} warning{'s' if len(warnings) > 1 else ''}")
    if suggestions:
        stats.append(f"💡 {len(suggestions)} suggestion{'s' if len(suggestions) > 1 else ''}")

    if stats:
        body += " · ".join(stats) + "\n\n"

    # priority nudge — only if errors exist
    if errors:
        body += f"**Fix the {len(errors)} error{'s' if len(errors) > 1 else ''} above before anything else.**\n\n"

    if inline_count > 0:
        body += f"*↑ {inline_count} inline comment{'s' if inline_count > 1 else ''} on the relevant lines.*\n\n"

    # fallback issues — short format
    if fallback_issues:
        body += "---\n"
        for issue in fallback_issues:
            severity = issue.get("severity", "warning")
            icon = "🚨" if severity == "error" else "⚠️" if severity == "warning" else "💡"
            short = issue.get("comment", "").split(".")[0]
            fix = issue.get("fix", "").split("\n")[0]
            body += f"{icon} `{issue.get('file', '')}` — {short}.\n"
            if fix:
                body += f"   💡 `{fix}`\n"
        body += "\n"

    body += f"---\n{verdict_icon} **{verdict_text}**"
    if not approved and errors:
        body += f" — resolve {len(errors)} error{'s' if len(errors) > 1 else ''} to unlock"

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