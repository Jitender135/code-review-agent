"""
Run this script to test the agent without needing to open a real PR.
Usage: python test_agent.py
"""

import os
from dotenv import load_dotenv
from github import Github, Auth
import jwt
import time

load_dotenv()

APP_ID = os.getenv("APP_ID")
PRIVATE_KEY_PATH = os.getenv("PRIVATE_KEY_PATH")
INSTALLATION_ID = 142895464  # your installation ID from earlier

# test diff — change this to test different scenarios
TEST_DIFF = """--- README.md ---
@@ -1,3 +1,4 @@
 # test-review-agent
+This is a documentation update
 hello testing !
"""

TEST_REPO = "Jitender135/test-review-agent"
TEST_PR = 7  # use any open PR number


def get_github_client():
    with open(PRIVATE_KEY_PATH, "r") as f:
        private_key = f.read()
    auth = Auth.AppInstallationAuth(
        Auth.AppAuth(APP_ID, private_key),
        INSTALLATION_ID
    )
    return Github(auth=auth)


def run_test():
    print("=" * 50)
    print("Running agent test...")
    print("=" * 50)

    from agents.pipeline import review_pipeline

    result = review_pipeline.invoke({
        "repo_name": TEST_REPO,
        "pr_number": TEST_PR,
        "installation_id": INSTALLATION_ID,
        "diff": TEST_DIFF,
        "config": {},
        "collection_name": "",
        "similar_prs": [],
        "language": "",
        "bug_issues": [],
        "security_issues": [],
        "review": {}
    })

    print("\n" + "=" * 50)
    print("Test complete!")
    print("Check PR #" + str(TEST_PR) + " on GitHub")
    print("=" * 50)


if __name__ == "__main__":
    run_test()