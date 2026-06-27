import hmac
import hashlib
import os
from fastapi import FastAPI, Request, HTTPException
from dotenv import load_dotenv
from github import Github, Auth
import jwt
import time
import json


from agents.reviewer import review_diff
from agents.commenter import post_review

load_dotenv()

app = FastAPI()

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
APP_ID = os.getenv("APP_ID")
PRIVATE_KEY_PATH = os.getenv("PRIVATE_KEY_PATH")


def get_github_client(installation_id: int):
    with open(PRIVATE_KEY_PATH, "r") as f:
        private_key = f.read()

    payload = {
        "iat": int(time.time()) - 60,
        "exp": int(time.time()) + 600,
        "iss": APP_ID
    }

    encoded_jwt = jwt.encode(payload, private_key, algorithm="RS256")

    auth = Auth.AppInstallationAuth(
        Auth.AppAuth(APP_ID, private_key),
        installation_id
    )
    return Github(auth=auth)


def get_pr_diff(repo_name: str, pr_number: int, installation_id: int):
    gh = get_github_client(installation_id)
    repo = gh.get_repo(repo_name)
    pr = repo.get_pull(pr_number)

    diff = ""
    for f in pr.get_files():
        diff += f"--- {f.filename} ---\n"
        diff += f"{f.patch or 'binary file'}\n\n"

    return diff


def verify_signature(payload: bytes, signature: str) -> bool:
    expected = "sha256=" + hmac.new(
        WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@app.get("/")
async def root():
    return {"status": "code review agent is running"}


@app.post("/webhook")
async def handle_webhook(request: Request):
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

    print(f"\nPR #{pr_number} {action} on {repo_name}")

    diff = get_pr_diff(repo_name, pr_number, installation_id)
    print("\nSending to Groq for review...")
    review = review_diff(diff)
    print("\nReview result:")
    print(json.dumps(review, indent=2))
    post_review(repo_name, pr_number, review, installation_id)

    return {"status": "received", "pr": pr_number, "repo": repo_name}