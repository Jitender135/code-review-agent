from typing import TypedDict, List, Annotated
import operator
from langgraph.graph import StateGraph, END
from agents.context_agent import index_repo_history, get_similar_prs
from agents.reviewer import review_diff
from agents.commenter import post_review
from agents.language_detector import detect_language
from agents.bug_detector import detect_bugs
from agents.security_scanner import scan_security
from agents.merger import merge_results
from agents.config_reader import read_repo_config


class ReviewState(TypedDict):
    repo_name: str
    pr_number: int
    installation_id: int
    diff: str
    config: dict
    collection_name: str
    similar_prs: List[str]
    language: str
    bug_issues: Annotated[List[dict], operator.add]
    security_issues: Annotated[List[dict], operator.add]
    review: dict


def config_node(state: ReviewState) -> ReviewState:
    print("\n[Agent 0] Config reader running...")
    config = read_repo_config(state["repo_name"], state["installation_id"])
    print(f"[Agent 0] Strictness: {config['strictness']} | Focus: {config['focus']} | Max comments: {config['max_comments']}")

    # auto approve docs-only PRs if configured
    if config.get("auto_approve_docs"):
        diff = state["diff"]
        import re
        files = re.findall(r"^--- (.+?) ---$", diff, re.MULTILINE)
        doc_extensions = [".md", ".txt", ".rst", ".yml", ".yaml"]
        if files and all(
            any(f.strip().endswith(ext) for ext in doc_extensions)
            for f in files
        ):
            print("[Agent 0] Docs-only PR detected — auto approving")
            return {**state, "config": config, "review": {
                "summary": "This PR only modifies documentation files. Auto approved.",
                "issues": [],
                "approved": True,
                "_auto_approved": True
            }}

    return {**state, "config": config}


def context_node(state: ReviewState) -> ReviewState:
    print("\n[Agent 1] Context agent running...")
    collection_name = index_repo_history(
        state["repo_name"],
        state["installation_id"]
    )
    similar_prs = get_similar_prs(collection_name, state["diff"])
    print(f"[Agent 1] Retrieved {len(similar_prs)} similar PRs")
    return {**state, "collection_name": collection_name, "similar_prs": similar_prs}


def language_node(state: ReviewState) -> ReviewState:
    print("\n[Agent 2] Language detector running...")
    # use config language hint if provided
    config_lang = state["config"].get("language")
    if config_lang:
        print(f"[Agent 2] Language from config: {config_lang}")
        return {**state, "language": config_lang}
    language = detect_language(state["diff"])
    print(f"[Agent 2] Detected language: {language}")
    return {**state, "language": language}


def bug_node(state: ReviewState) -> dict:
    config = state["config"]
    if "bugs" not in config.get("focus", ["bugs"]):
        print("\n[Agent 3a] Bug detector skipped — not in focus")
        return {"bug_issues": []}
    print("\n[Agent 3a] Bug detector running...")
    issues = detect_bugs(state["diff"], state["language"])
    print(f"[Agent 3a] Found {len(issues)} bug issues")
    return {"bug_issues": issues}


def security_node(state: ReviewState) -> dict:
    config = state["config"]
    if "security" not in config.get("focus", ["security"]):
        print("\n[Agent 3b] Security scanner skipped — not in focus")
        return {"security_issues": []}
    print("\n[Agent 3b] Security scanner running...")
    issues = scan_security(state["diff"], state["language"])
    print(f"[Agent 3b] Found {len(issues)} security issues")
    return {"security_issues": issues}


def merger_node(state: ReviewState) -> ReviewState:
    # skip if already auto approved
    if state.get("review", {}).get("_auto_approved"):
        print("\n[Agent 4] Merger skipped — auto approved")
        return state

    print("\n[Agent 4] Merger agent running...")
    config = state["config"]
    strictness = config.get("strictness", "medium")
    max_comments = config.get("max_comments", 3)
    ignore = config.get("ignore", [])

    bug_issues = state["bug_issues"]
    security_issues = state["security_issues"]

    # apply ignore list
    if "suggestions" in ignore:
        bug_issues = [i for i in bug_issues if i.get("severity") != "suggestion"]
        security_issues = [i for i in security_issues if i.get("severity") != "suggestion"]

    # apply strictness
    if strictness == "low":
        bug_issues = [i for i in bug_issues if i.get("severity") == "error"]
        security_issues = [i for i in security_issues if i.get("severity") == "error"]
    elif strictness == "high":
        pass  # keep everything

    review = merge_results(
        bug_issues,
        security_issues,
        state["similar_prs"],
        state["language"],
        max_comments=max_comments
    )
    print(f"[Agent 4] Merged review — approved: {review.get('approved')}")
    return {**state, "review": review}


def commenter_node(state: ReviewState) -> ReviewState:
    print("\n[Agent 5] Commenter agent running...")
    post_review(
        state["repo_name"],
        state["pr_number"],
        state["review"],
        state["installation_id"],
        state["diff"]
    )
    print("[Agent 5] Comment posted to GitHub")
    return state


def should_skip_review(state: ReviewState) -> str:
    if state.get("review", {}).get("_auto_approved"):
        return "commenter"
    return "language"


def build_pipeline():
    graph = StateGraph(ReviewState)

    graph.add_node("config", config_node)
    graph.add_node("context", context_node)
    graph.add_node("language", language_node)
    graph.add_node("bug_detector", bug_node)
    graph.add_node("security_scanner", security_node)
    graph.add_node("merger", merger_node)
    graph.add_node("commenter", commenter_node)

    graph.set_entry_point("config")
    graph.add_edge("config", "context")

    # conditional — skip full review if auto approved
    graph.add_conditional_edges("context", should_skip_review, {
        "language": "language",
        "commenter": "commenter"
    })

    graph.add_edge("language", "bug_detector")
    graph.add_edge("language", "security_scanner")
    graph.add_edge("bug_detector", "merger")
    graph.add_edge("security_scanner", "merger")
    graph.add_edge("merger", "commenter")
    graph.add_edge("commenter", END)

    return graph.compile()


review_pipeline = build_pipeline()