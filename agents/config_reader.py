import os
from github import Github, Auth
from dotenv import load_dotenv
import yaml

load_dotenv()

APP_ID = os.getenv("APP_ID")
PRIVATE_KEY_PATH = os.getenv("PRIVATE_KEY_PATH")

DEFAULT_CONFIG = {
    "strictness": "medium",
    "focus": ["security", "bugs", "style"],
    "ignore": [],
    "max_comments": 3,
    "auto_approve_docs": True,
    "language": None
}


def get_github_client(installation_id: int):
    with open(PRIVATE_KEY_PATH, "r") as f:
        private_key = f.read()
    auth = Auth.AppInstallationAuth(
        Auth.AppAuth(APP_ID, private_key),
        installation_id
    )
    return Github(auth=auth)


def read_repo_config(repo_name: str, installation_id: int) -> dict:
    try:
        gh = get_github_client(installation_id)
        repo = gh.get_repo(repo_name)
        file = repo.get_contents(".reviewagent.yml")
        raw = file.decoded_content.decode("utf-8")
        config = yaml.safe_load(raw)
        print(f"Config loaded from .reviewagent.yml: {config}")

        # merge with defaults — repo config overrides defaults
        merged = DEFAULT_CONFIG.copy()
        merged.update(config)
        return merged

    except Exception:
        print("No .reviewagent.yml found — using defaults")
        return DEFAULT_CONFIG.copy()