
import json
import re
from pathlib import Path

from rank_bm25 import BM25Okapi

ROOT = Path(__file__).resolve().parents[1]

CHUNK_DIR = ROOT / "data" / "processed" / "chunks"
OUTPUT_DIR = ROOT / "evaluation"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TOP_K = 5

QUERIES = [
    "What should I do if I receive a phishing email?",
    "How can I protect my online accounts using multi-factor authentication?",
    "What should I do if my account has been compromised?",
    "How should passwords be stored securely?",
    "What are the steps involved in responding to a cybersecurity incident?"
]


def tokenize(text):
    """
    Convert text into lowercase word tokens.
    Keep technical terms and cybersecurity keywords.
    """
    return re.findall(r"[a-zA-Z0-9]+", text.lower())


def load_chunks(filename):
    path = CHUNK_DIR / filename

    if not path.exists():
        raise FileNotFoundError(f"Chunk file not found: {path}")

    chunks = []

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                chunks.append(json.loads(line))

    return chunks


def build_bm25(chunks):
    corpus = [
        tokenize(chunk.get("text", ""))
        for chunk in chunks
    ]

    bm25 = BM25Okapi(corpus)

    return bm25


def search_bm25(query, bm25, chunks, top_k=TOP_K):
    query_tokens = tokenize(query)

    scores = bm25.get_scores(query_tokens)

    ranked_indices = sorted(
        range(len(scores)),
        key=lambda i: scores[i],
        reverse=True
    )[:top_k]

    results = []

    for index in ranked_indices:
        chunk = chunks[index]

        results.append({
            "score": float(scores[index]),
            "chunk_id": chunk.get("chunk_id"),
            "source_id": chunk.get("source_id"),
            "source_title": chunk.get("source_title"),
            "page": chunk.get("page"),
            "text": chunk.get("text", "")
        })

    return results


def run_experiment(strategy, filename):
    print("\n" + "=" * 65)
    print(f"BM25 RETRIEVAL: {strategy.upper()}")
    print("=" * 65)

    chunks = load_chunks(filename)

    print("Chunks loaded:", len(chunks))

    bm25 = build_bm25(chunks)

    all_results = []

    for query in QUERIES:
        results = search_bm25(query, bm25, chunks)

        all_results.append({
            "query": query,
            "strategy": f"bm25_{strategy}",
            "results": results
        })

        print("\nQuery:", query)

        for rank, result in enumerate(results, start=1):
            print(
                f"{rank}. {result['source_id']} | "
                f"Page {result['page']} | "
                f"Score: {result['score']:.4f}"
            )

    return all_results


def main():
    fixed_results = run_experiment(
        "fixed",
        "fixed_chunks.jsonl"
    )

    recursive_results = run_experiment(
        "recursive",
        "recursive_chunks.jsonl"
    )

    all_results = fixed_results + recursive_results

    output_path = OUTPUT_DIR / "bm25_results.json"

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(
            all_results,
            file,
            indent=4,
            ensure_ascii=False
        )

    print("\n" + "=" * 65)
    print("BM25 EXPERIMENT COMPLETED")
    print("=" * 65)

    print("Total searches:", len(all_results))
    print("Results saved to:", output_path)


if __name__ == "__main__":
    main()
