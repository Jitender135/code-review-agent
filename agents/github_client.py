import os
from github import Github, Auth
from dotenv import load_dotenv

load_dotenv()

APP_ID = os.getenv("APP_ID")


def get_private_key() -> str:
    key = os.getenv("PRIVATE_KEY", "")
    if key:
        return key.replace("\\n", "\n")
    key_path = os.getenv("PRIVATE_KEY_PATH", "private-key.pem")
    if os.path.exists(key_path):
        with open(key_path, "r") as f:
            return f.read()
    raise ValueError("No private key found.")


def get_github_client(installation_id: int) -> Github:
    private_key = get_private_key()
    auth = Auth.AppInstallationAuth(
        Auth.AppAuth(APP_ID, private_key),
        installation_id
    )
    return Github(auth=auth)