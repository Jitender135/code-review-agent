import os
from sentence_transformers import SentenceTransformer
import chromadb
from dotenv import load_dotenv
from agents.github_client import get_github_client

load_dotenv()

embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
chroma_client = chromadb.PersistentClient(path="./chroma_db")


def index_repo_history(repo_name: str, installation_id: int):
    print(f"\nIndexing past PRs for {repo_name}...")
    gh = get_github_client(installation_id)
    repo = gh.get_repo(repo_name)

    collection_name = repo_name.replace("/", "__").replace("-", "_")
    collection = chroma_client.get_or_create_collection(name=collection_name)

    merged_prs = []
    for pr in repo.get_pulls(state="closed", sort="updated", direction="desc"):
        if pr.merged and len(merged_prs) < 20:
            merged_prs.append(pr)

    if not merged_prs:
        print("No merged PRs found — skipping indexing")
        return collection_name

    docs, ids, metadatas = [], [], []
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

    collection.upsert(documents=docs, ids=ids, metadatas=metadatas)
    print(f"Indexed {len(docs)} merged PRs")
    return collection_name


def get_similar_prs(collection_name: str, current_diff: str, n: int = 3):
    try:
        collection = chroma_client.get_collection(name=collection_name)
        count = collection.count()
        if count == 0:
            return []
        results = collection.query(
            query_texts=[current_diff[:500]],
            n_results=min(n, count)
        )
        return results["documents"][0]
    except Exception as e:
        print(f"RAG retrieval error: {e}")
        return []