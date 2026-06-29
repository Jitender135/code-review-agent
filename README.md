# Code Review Agent

A GitHub App that reviews pull requests automatically. It reads your PR diff, detects bugs and security vulnerabilities, and posts comments directly on the problematic lines — the same way a senior engineer would during a code review.

Built this because code reviews are a bottleneck in most engineering teams. Reviewers are busy, PRs pile up, and developers wait days for feedback. This agent gives instant, consistent feedback on every PR.

---

## What it does

When a PR is opened or updated, the agent:

- Fetches the diff and detects the language
- Reads your repo's past merged PRs to understand your team's conventions
- Runs bug detection and security scanning in parallel
- Posts inline comments on the exact lines that have issues
- Gives the PR a health score from 0 to 100
- Tracks what got fixed between commits

The feedback looks like this on GitHub:

```
🚨 [SECURITY] ERROR
Direct string concatenation in SQL query allows attackers to manipulate the database.
💡 Hint: cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
```

The summary comment shows the health score, a prioritized list of issues, and a diff of what changed since the last review.

---

## How it works

The core is a LangGraph state graph with six agents running in sequence, with the bug detector and security scanner running in parallel:

```
Config Reader → Context Agent → Language Detector
                                      ↓
                          Bug Detector  +  Security Scanner  (parallel)
                                      ↓
                               Merger Agent
                                      ↓
                              Commenter Agent
```

The context agent uses RAG — it embeds your last 20 merged PRs into ChromaDB and retrieves the most similar ones before reviewing a new PR. This means the agent reviews against your team's actual patterns, not generic rules.

---

## Stack

- LangGraph — agent orchestration
- Groq + Llama 3.3 70B — LLM inference (free tier)
- ChromaDB + sentence-transformers — vector store for RAG
- FastAPI — webhook server
- PyGithub — GitHub API

Everything runs on free tiers. No paid APIs.

---

## Configuration

Drop a `.reviewagent.yml` in your repo root to customize behavior:

```yaml
strictness: high
focus:
  - security
  - bugs
ignore:
  - suggestions
max_comments: 3
auto_approve_docs: true
```

The agent reads this before each review. If the file doesn't exist, it uses sensible defaults.

---

## Running locally

```bash
git clone https://github.com/Jitender135/code-review-agent.git
cd code-review-agent
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Set up your `.env`:

```
APP_ID=your_github_app_id
WEBHOOK_SECRET=your_webhook_secret
GROQ_API_KEY=your_groq_key
PRIVATE_KEY_PATH=private-key.pem
```

Run the server:

```bash
uvicorn main:app --reload --port 8000
```

To test without opening a real PR:

```bash
python test_agent.py
```

---

## Why I built this

I wanted to understand how multi-agent AI systems actually work in production — not just call an LLM and return the response, but design agents that hand off state, run in parallel, and produce structured output that drives real actions.

This project taught me LangGraph orchestration, RAG pipeline design, GitHub App authentication, unified diff parsing, and how to evaluate whether an AI system is actually working.

The resume line writes itself — but more importantly, every problem in this project was a real engineering problem with a non-obvious solution.