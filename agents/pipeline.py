from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from agents.context_agent import index_repo_history, get_similar_prs
from agents.reviewer import review_diff
from agents.commenter import post_review


class ReviewState(TypedDict):
    repo_name: str
    pr_number: int
    installation_id: int
    diff: str
    collection_name: str
    similar_prs: List[str]
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


def reviewer_node(state: ReviewState) -> ReviewState:
    print("\n[Agent 2] Reviewer agent running...")
    review = review_diff(state["diff"], context=state["similar_prs"])
    print(f"[Agent 2] Review complete — approved: {review.get('approved')}")
    return {**state, "review": review}


def commenter_node(state: ReviewState) -> ReviewState:
    print("\n[Agent 3] Commenter agent running...")
    post_review(
        state["repo_name"],
        state["pr_number"],
        state["review"],
        state["installation_id"]
    )
    print("[Agent 3] Comment posted to GitHub")
    return state


def build_pipeline():
    graph = StateGraph(ReviewState)

    graph.add_node("context", context_node)
    graph.add_node("reviewer", reviewer_node)
    graph.add_node("commenter", commenter_node)

    graph.set_entry_point("context")
    graph.add_edge("context", "reviewer")
    graph.add_edge("reviewer", "commenter")
    graph.add_edge("commenter", END)

    return graph.compile()


review_pipeline = build_pipeline()