import os
import yaml
from dotenv import load_dotenv
from agents.github_client import get_github_client

load_dotenv()

DEFAULT_CONFIG = {
    "strictness": "medium",
    "focus": ["security", "bugs", "style"],
    "ignore": [],
    "max_comments": 3,
    "auto_approve_docs": True,
    "language": None
}


def read_repo_config(repo_name: str, installation_id: int) -> dict:
    try:
        gh = get_github_client(installation_id)
        repo = gh.get_repo(repo_name)
        file = repo.get_contents(".reviewagent.yml")
        raw = file.decoded_content.decode("utf-8")
        config = yaml.safe_load(raw)
        print(f"Config loaded from .reviewagent.yml: {config}")
        merged = DEFAULT_CONFIG.copy()
        merged.update(config)
        return merged
    except Exception:
        print("No .reviewagent.yml found — using defaults")
        return DEFAULT_CONFIG.copy()