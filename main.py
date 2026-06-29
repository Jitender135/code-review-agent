import hmac
import hashlib
import os
import time
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from dotenv import load_dotenv
from github import Github

from agents.github_client import get_github_client
from agents.pipeline import review_pipeline

load_dotenv()

app = FastAPI()

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
APP_ID = os.getenv("APP_ID")
PRIVATE_KEY_PATH = os.getenv("PRIVATE_KEY_PATH")


def get_github_client(installation_id: int):
    with open(PRIVATE_KEY_PATH, "r") as f:
        private_key = f.read()


def get_pr_diff(repo_name: str, pr_number: int, installation_id: int):
    gh = get_github_client(installation_id)
    repo = gh.get_repo(repo_name)
    pr = repo.get_pull(pr_number)
    diff = ""
    for f in pr.get_files():
        if f.patch:
            diff += f"--- {f.filename} ---\n"
            diff += f"{f.patch}\n\n"
    return diff


def verify_signature(payload: bytes, signature: str) -> bool:
    expected = "sha256=" + hmac.new(
        WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def run_review(repo_name: str, pr_number: int, installation_id: int):
    """
    Runs in the background after webhook returns 200.
    All errors are caught here so they never crash the server.
    """
    start = time.time()
    print(f"\n[Background] Starting review for PR #{pr_number} on {repo_name}")

    try:
        diff = get_pr_diff(repo_name, pr_number, installation_id)
        print(f"[Background] Diff fetched — {len(diff)} characters")

        review_pipeline.invoke({
            "repo_name": repo_name,
            "pr_number": pr_number,
            "installation_id": installation_id,
            "diff": diff,
            "config": {},
            "collection_name": "",
            "similar_prs": [],
            "language": "",
            "bug_issues": [],
            "security_issues": [],
            "review": {}
        })

        elapsed = round(time.time() - start, 1)
        print(f"[Background] Review complete in {elapsed}s for PR #{pr_number}")

    except Exception as e:
        elapsed = round(time.time() - start, 1)
        print(f"[Background] Review failed after {elapsed}s for PR #{pr_number}: {e}")

        # post a fallback comment so the developer knows something went wrong
        try:
            gh = get_github_client(installation_id)
            repo = gh.get_repo(repo_name)
            pr = repo.get_pull(pr_number)
            pr.create_issue_comment(
                "## 🤖 AI Code Review\n\n"
                "⚠️ The review could not be completed due to an internal error. "
                "Please try pushing a new commit to trigger a re-review.\n\n"
                f"*Error: {str(e)[:200]}*"
            )
        except Exception as comment_error:
            print(f"[Background] Could not post fallback comment: {comment_error}")


@app.get("/")
async def root():
    return {"status": "code review agent is running"}


@app.post("/webhook")
async def handle_webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.body()

    signature = request.headers.get("X-Hub-Signature-256", "")
    if not verify_signature(payload, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    data = await request.json()
    action = data.get("action")

    if action not in ["opened", "synchronize"]:
        return {"status": "ignored", "action": action}

    pr_number = data["pull_request"]["number"]
    repo_name = data["repository"]["full_name"]
    installation_id = data["installation"]["id"]

    print(f"\nWebhook received — PR #{pr_number} {action} on {repo_name}")
    print(f"Queuing background review...")

    # return immediately — review runs in background
    background_tasks.add_task(run_review, repo_name, pr_number, installation_id)

    return {"status": "queued", "pr": pr_number, "repo": repo_name}