from typing import TypedDict, List, Annotated
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
import operator
from agents.context_agent import index_repo_history, get_similar_prs
from agents.reviewer import review_diff
from agents.commenter import post_review
from agents.language_detector import detect_language
from agents.bug_detector import detect_bugs
from agents.security_scanner import scan_security
from agents.merger import merge_results


class ReviewState(TypedDict):
    repo_name: str
    pr_number: int
    installation_id: int
    diff: str
    collection_name: str
    similar_prs: List[str]
    language: str
    bug_issues: Annotated[List[dict], operator.add]
    security_issues: Annotated[List[dict], operator.add]
    review: dict


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
    language = detect_language(state["diff"])
    print(f"[Agent 2] Detected language: {language}")
    return {**state, "language": language}


def bug_node(state: ReviewState) -> dict:
    print("\n[Agent 3a] Bug detector running...")
    issues = detect_bugs(state["diff"], state["language"])
    print(f"[Agent 3a] Found {len(issues)} bug issues")
    return {"bug_issues": issues}


def security_node(state: ReviewState) -> dict:
    print("\n[Agent 3b] Security scanner running...")
    issues = scan_security(state["diff"], state["language"])
    print(f"[Agent 3b] Found {len(issues)} security issues")
    return {"security_issues": issues}


def merger_node(state: ReviewState) -> ReviewState:
    print("\n[Agent 4] Merger agent running...")
    review = merge_results(
        state["bug_issues"],
        state["security_issues"],
        state["similar_prs"],
        state["language"]
    )
    print(f"[Agent 4] Merged review — approved: {review.get('approved')}")
    return {**state, "review": review}


def commenter_node(state: ReviewState) -> ReviewState:
    print("\n[Agent 5] Commenter agent running...")
    post_review(
        state["repo_name"],
        state["pr_number"],
        state["review"],
        state["installation_id"]
    )
    print("[Agent 5] Comment posted to GitHub")
    return state


def build_pipeline():
    graph = StateGraph(ReviewState)

    graph.add_node("context", context_node)
    graph.add_node("language", language_node)
    graph.add_node("bug_detector", bug_node)
    graph.add_node("security_scanner", security_node)
    graph.add_node("merger", merger_node)
    graph.add_node("commenter", commenter_node)

    # sequential start
    graph.set_entry_point("context")
    graph.add_edge("context", "language")

    # fan-out — both run after language
    graph.add_edge("language", "bug_detector")
    graph.add_edge("language", "security_scanner")

    # fan-in — merger waits for both
    graph.add_edge("bug_detector", "merger")
    graph.add_edge("security_scanner", "merger")

    graph.add_edge("merger", "commenter")
    graph.add_edge("commenter", END)

    return graph.compile()


review_pipeline = build_pipeline()