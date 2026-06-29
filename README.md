# 🤖 AI Code Review Agent

An autonomous multi-agent system that reviews GitHub Pull Requests like a senior engineer — posting inline comments on specific lines, detecting real bugs and security vulnerabilities, and tracking progress between commits.

> Built entirely for free. No paid APIs, no paid infrastructure.

---

## What it does

When a developer opens or updates a Pull Request, the agent automatically:

1. Reads the PR diff and understands what changed
2. Fetches your repo's past merged PRs to learn your team's conventions (RAG)
3. Runs a bug detector and security scanner in parallel
4. Posts **inline comments on the exact lines** with problems
5. Gives the PR a **Health Score (0–100)**
6. Tracks what got fixed between commits and what's still broken

**Example review on a real PR:**

```
🚨 [SECURITY] ERROR
The code is vulnerable to SQL injection attacks due to direct string concatenation.
💡 Hint: cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
```

```
## 🤖 AI Code Review

Health Score: `████░░░░░░` 40/100 🔴

The code has critical security vulnerabilities including SQL injection and unhandled exceptions.

🚨 2 errors

Fix the 2 errors above before anything else.

↑ 2 inline comments on the relevant lines.

📊 Changes Since Last Review
Health Score: 40/100 → 60/100 ↑ +20 🟢
✅ Fixed: SQL injection vulnerability
🆕 New issues: Missing input validation

❌ Changes Requested — resolve 2 errors to unlock
```

---

## Architecture

```
GitHub PR Opened
      ↓
FastAPI Webhook Server
      ↓
[Agent 0] Config Reader    ← reads .reviewagent.yml
      ↓
[Agent 1] Context Agent    ← RAG over past merged PRs (ChromaDB)
      ↓
[Agent 2] Language Detector
      ↓
[Agent 3a] Bug Detector  ←→  [Agent 3b] Security Scanner  (parallel)
      ↓
[Agent 4] Merger Agent    ← deduplicates, ranks, formats
      ↓
[Agent 5] Commenter Agent ← posts inline + summary to GitHub
```

Built with **LangGraph** — agents run as a compiled state graph with fan-out/fan-in parallel execution.

---

## Tech stack

| Layer | Tool | Cost |
|-------|------|------|
| Agent orchestration | LangGraph | Free |
| LLM inference | Groq + Llama 3.3 70B | Free tier |
| Vector store | ChromaDB + sentence-transformers | Free |
| GitHub integration | PyGithub + GitHub Apps | Free |
| Web server | FastAPI + Uvicorn | Free |
| Deployment | Render.com | Free tier |

---

## Features

**Core review:**
- Detects bugs — null pointers, division by zero, unhandled exceptions, off-by-one errors
- Catches security vulnerabilities — SQL injection, hardcoded secrets, XSS, missing input validation
- Posts inline comments on specific diff lines (not just a wall of text at the bottom)
- Gives every PR a Health Score from 0–100

**Smart behaviour:**
- Learns your repo's conventions from past merged PRs (RAG)
- Tracks what changed between commits — shows fixed vs still-present vs new issues
- Auto-approves documentation-only PRs
- Prevents duplicate comments — edits existing comment on re-review
- Configurable per repo via `.reviewagent.yml`

**Repo config (`.reviewagent.yml`):**
```yaml
strictness: high          # low / medium / high
focus:
  - security
  - bugs
ignore:
  - suggestions
max_comments: 3
auto_approve_docs: true
```

---

## Getting started

### 1. Clone the repo

```bash
git clone https://github.com/Jitender135/code-review-agent.git
cd code-review-agent
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Create a GitHub App

Go to `github.com/settings/apps/new` and set:
- Permissions: Contents (read), Pull Requests (read + write), Metadata (read)
- Subscribe to events: Pull request
- Download the private key

### 3. Set up environment variables

```bash
# .env
APP_ID=your_app_id
WEBHOOK_SECRET=your_webhook_secret
GROQ_API_KEY=your_groq_key
PRIVATE_KEY_PATH=private-key.pem
```

### 4. Run the server

```bash
uvicorn main:app --reload --port 8000
```

### 5. Install the GitHub App on any repo

Go to your GitHub App settings → Install → select repos.

---

## Testing locally

Use the test script to run the full pipeline without needing a real PR:

```bash
python test_agent.py
```

Edit `TEST_DIFF` in `test_agent.py` to test different code scenarios.

---

## Project structure

```
code-review-agent/
├── main.py                    # FastAPI webhook server
├── test_agent.py              # local test runner
├── agents/
│   ├── pipeline.py            # LangGraph graph definition
│   ├── config_reader.py       # .reviewagent.yml parser
│   ├── context_agent.py       # RAG over merged PRs
│   ├── language_detector.py   # detect language from diff
│   ├── bug_detector.py        # bug detection agent
│   ├── security_scanner.py    # security vulnerability agent
│   ├── merger.py              # merge + deduplicate results
│   ├── commenter.py           # post review to GitHub
│   ├── change_tracker.py      # diff between reviews
│   └── diff_parser.py         # parse unified diff positions
└── .reviewagent.yml           # example config
```

---

## Roadmap

- [x] Multi-agent LangGraph pipeline
- [x] Parallel bug + security scanning
- [x] RAG over repo history
- [x] Inline line comments
- [x] PR Health Score
- [x] Change tracking between commits
- [x] Repo config file
- [ ] Async webhook processing
- [ ] Dashboard for engineering managers
- [ ] Suggested fixes as one-click GitHub suggestions
- [ ] Org-level config
- [ ] Landing page with install button

---

## Resume line

> Built a production-grade multi-agent code review GitHub App using LangGraph with parallel agent execution — dedicated bug detection, security scanning (SQL injection, XSS, hardcoded secrets), and RAG over merged PR history (ChromaDB + sentence-transformers); posts engineer-style inline comments with fixes directly on PR diff lines, tracks issue resolution between commits, and is configurable per repo via YAML.

---

## Author

**Jitender Singh**
Built as a learning project to understand multi-agent AI systems, RAG pipelines, and GitHub App development.