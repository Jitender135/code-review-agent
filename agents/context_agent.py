import os
import re
import chromadb
from dotenv import load_dotenv
from agents.github_client import get_github_client

load_dotenv()

chroma_client = chromadb.PersistentClient(path="./chroma_db")


def simple_embed(text: str) -> list:
    """
    Keyword frequency vector — no model needed.
    Works well enough for finding similar PRs.
    """
    keywords = [
        "def", "class", "import", "return", "if", "for", "while",
        "try", "except", "raise", "async", "await", "sql", "select",
        "insert", "update", "delete", "password", "token", "secret",
        "api", "key", "auth", "login", "user", "error", "exception",
        "null", "none", "index", "list", "dict", "str", "int", "bool"
    ]
    text_lower = text.lower()
    return [float(text_lower.count(kw)) for kw in keywords]


def index_repo_history(repo_name: str, installation_id: int):
    print(f"\nIndexing past PRs for {repo_name}...")
    gh = get_github_client(installation_id)
    repo = gh.get_repo(repo_name)

    collection_name = repo_name.replace("/", "__").replace("-", "_")
    collection = chroma_client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"}
    )

    merged_prs = []
    for pr in repo.get_pulls(state="closed", sort="updated", direction="desc"):
        if pr.merged and len(merged_prs) < 20:
            merged_prs.append(pr)

    if not merged_prs:
        print("No merged PRs found — skipping indexing")
        return collection_name

    docs, ids, metadatas, embeddings = [], [], [], []
    for pr in merged_prs:
        files = list(pr.get_files())
        diff_text = " ".join([
            f.filename + ": " + (f.patch or "")
            for f in files[:5]
        ])
        doc = f"PR Title: {pr.title}\nDiff: {diff_text[:1000]}"
        docs.append(doc)
        ids.append(str(pr.number))
        metadatas.append({"title": pr.title, "url": pr.html_url})
        embeddings.append(simple_embed(doc))

    collection.upsert(
        documents=docs,
        ids=ids,
        metadatas=metadatas,
        embeddings=embeddings
    )
    print(f"Indexed {len(docs)} merged PRs")
    return collection_name


def get_similar_prs(collection_name: str, current_diff: str, n: int = 3):
    try:
        collection = chroma_client.get_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        count = collection.count()
        if count == 0:
            return []
        query_embedding = simple_embed(current_diff[:500])
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n, count)
        )
        return results["documents"][0]
    except Exception as e:
        print(f"RAG retrieval error: {e}")
        return []