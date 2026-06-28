import re


def extract_issues_from_comment(comment_body: str) -> list:
    """
    Parse issues from a previous bot comment body.
    Returns a list of issue strings for comparison.
    """
    if not comment_body:
        return []

    issues = []

    # extract inline comment references from summary
    # look for lines like "🚨 [SECURITY]..." or "⚠️ [BUG]..."
    lines = comment_body.split("\n")
    for line in lines:
        line = line.strip()
        if any(icon in line for icon in ["🚨", "⚠️", "💡"]):
            # clean up markdown and extract core issue text
            clean = re.sub(r"\*\*|\`|🚨|⚠️|💡", "", line).strip()
            if clean and len(clean) > 5:
                issues.append(clean.lower().strip())

    return issues


def extract_score_from_comment(comment_body: str) -> int | None:
    """Extract the health score from a previous bot comment."""
    match = re.search(r"Health Score.*?(\d+)/100", comment_body)
    if match:
        return int(match.group(1))
    return None


def categorize_changes(old_issues: list, new_issues: list) -> dict:
    """
    Compare old and new issues to find what changed.
    Returns fixed, still_present, and new_issues lists.
    """
    def normalize(text: str) -> str:
        return re.sub(r"\s+", " ", text.lower().strip())

    def is_similar(a: str, b: str) -> bool:
        a, b = normalize(a), normalize(b)
        if a == b:
            return True
        # check if key words overlap
        words_a = set(a.split())
        words_b = set(b.split())
        common = words_a & words_b
        meaningful = {w for w in common if len(w) > 4}
        return len(meaningful) >= 2

    fixed = []
    still_present = []
    new = []

    for old in old_issues:
        found = any(is_similar(old, new) for new in new_issues)
        if found:
            still_present.append(old)
        else:
            fixed.append(old)

    for new_issue in new_issues:
        found = any(is_similar(new_issue, old) for old in old_issues)
        if not found:
            new.append(new_issue)

    return {
        "fixed": fixed,
        "still_present": still_present,
        "new": new
    }


def build_change_summary(
    changes: dict,
    old_score: int | None,
    new_score: int
) -> str:
    """Build the change tracking section of the review comment."""

    # no previous review
    if old_score is None and not any(changes.values()):
        return ""

    body = "---\n### 📊 Changes Since Last Review\n\n"

    # score change
    if old_score is not None:
        diff = new_score - old_score
        if diff > 0:
            body += f"**Health Score:** {old_score}/100 → {new_score}/100 ↑ +{diff} 🟢\n\n"
        elif diff < 0:
            body += f"**Health Score:** {old_score}/100 → {new_score}/100 ↓ {diff} 🔴\n\n"
        else:
            body += f"**Health Score:** {old_score}/100 → {new_score}/100 → No change\n\n"

    # fixed issues
    if changes["fixed"]:
        body += "**✅ Fixed:**\n"
        for issue in changes["fixed"]:
            body += f"- ~~{issue}~~\n"
        body += "\n"

    # still present
    if changes["still_present"]:
        body += "**⚠️ Still needs attention:**\n"
        for issue in changes["still_present"]:
            body += f"- {issue}\n"
        body += "\n"

    # new issues
    if changes["new"]:
        body += "**🆕 New issues in this commit:**\n"
        for issue in changes["new"]:
            body += f"- {issue}\n"
        body += "\n"

    return body