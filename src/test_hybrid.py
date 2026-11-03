
import json
import pickle
import re
from pathlib import Path

import faiss
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]

VECTOR_DIR = ROOT / "vector_store"
CHUNK_DIR = ROOT / "data" / "processed" / "chunks"
OUTPUT_DIR = ROOT / "evaluation"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

DENSE_TOP_K = 10
BM25_TOP_K = 10

# Keep 10 candidates for the cross-encoder.
RERANK_CANDIDATE_K = 10

# Final results used for evaluation.
FINAL_TOP_K = 5

RRF_K = 60

model = SentenceTransformer(MODEL_NAME)


# --------------------------------------------------
# TOKENIZATION
# --------------------------------------------------

def tokenize(text):
    return re.findall(r"[a-zA-Z0-9]+", text.lower())


# --------------------------------------------------
# LOAD FAISS VECTOR STORE
# --------------------------------------------------

def load_vector_store(strategy):

    index_path = VECTOR_DIR / f"{strategy}_index.faiss"
    metadata_path = VECTOR_DIR / f"{strategy}_metadata.pkl"

    index = faiss.read_index(str(index_path))

    with open(metadata_path, "rb") as file:
        metadata = pickle.load(file)

    if index.ntotal != len(metadata):
        raise ValueError("Index and metadata sizes do not match!")

    return index, metadata


# --------------------------------------------------
# LOAD BM25
# --------------------------------------------------

def load_bm25(strategy):

    chunk_path = CHUNK_DIR / f"{strategy}_chunks.jsonl"

    chunks = []

    with open(chunk_path, "r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                chunks.append(json.loads(line))

    corpus = [
        tokenize(chunk.get("text", ""))
        for chunk in chunks
    ]

    bm25 = BM25Okapi(corpus)

    return bm25, chunks


# --------------------------------------------------
# FAISS DENSE RETRIEVAL
# --------------------------------------------------

def retrieve_dense(query, index, metadata, top_k=DENSE_TOP_K):

    query_embedding = model.encode(
        [query],
        convert_to_numpy=True,
        normalize_embeddings=True
    )

    scores, indices = index.search(
        query_embedding.astype("float32"),
        min(top_k, index.ntotal)
    )

    results = []

    for score, idx in zip(scores[0], indices[0]):

        if idx < 0:
            continue

        chunk = metadata[idx]

        results.append({
            "score": float(score),
            "chunk_id": chunk["chunk_id"],
            "source_id": chunk["source_id"],
            "source_title": chunk["source_title"],
            "issuer": chunk.get("issuer"),
            "page": chunk["page"],
            "text": chunk["text"]
        })

    return results


# --------------------------------------------------
# BM25 KEYWORD RETRIEVAL
# --------------------------------------------------

def retrieve_bm25(query, bm25, chunks, top_k=BM25_TOP_K):

    query_tokens = tokenize(query)

    scores = bm25.get_scores(query_tokens)

    ranked_indices = sorted(
        range(len(scores)),
        key=lambda i: scores[i],
        reverse=True
    )[:min(top_k, len(scores))]

    results = []

    for idx in ranked_indices:

        chunk = chunks[idx]

        results.append({
            "score": float(scores[idx]),
            "chunk_id": chunk["chunk_id"],
            "source_id": chunk["source_id"],
            "source_title": chunk["source_title"],
            "issuer": chunk.get("issuer"),
            "page": chunk["page"],
            "text": chunk["text"]
        })

    return results


# --------------------------------------------------
# RECIPROCAL RANK FUSION
# --------------------------------------------------

def reciprocal_rank_fusion(dense_results, bm25_results):

    fused_scores = {}
    chunk_details = {}

    retrieval_lists = [
        dense_results,
        bm25_results
    ]

    for results in retrieval_lists:

        for rank, result in enumerate(results, start=1):

            chunk_id = result["chunk_id"]

            if chunk_id not in fused_scores:

                fused_scores[chunk_id] = 0.0
                chunk_details[chunk_id] = result.copy()

            fused_scores[chunk_id] += 1.0 / (RRF_K + rank)

    ranked_chunks = sorted(
        fused_scores.keys(),
        key=lambda chunk_id: fused_scores[chunk_id],
        reverse=True
    )

    final_results = []

    for chunk_id in ranked_chunks:

        result = chunk_details[chunk_id].copy()

        result["rrf_score"] = fused_scores[chunk_id]

        result.pop("score", None)

        final_results.append(result)

    return final_results


# --------------------------------------------------
# RUN HYBRID EXPERIMENT
# --------------------------------------------------

def run_experiment(strategy, queries):

    print("\n" + "=" * 70)
    print(f"HYBRID RETRIEVAL: {strategy.upper()}")
    print("=" * 70)

    index, metadata = load_vector_store(strategy)

    bm25, chunks = load_bm25(strategy)

    print("FAISS vectors:", index.ntotal)
    print("BM25 chunks:", len(chunks))

    if index.ntotal != len(chunks):
        raise ValueError(
            f"{strategy}: FAISS and BM25 chunk counts do not match!"
        )

    all_results = []

    for query in queries:

        dense_results = retrieve_dense(
            query,
            index,
            metadata
        )

        bm25_results = retrieve_bm25(
            query,
            bm25,
            chunks
        )

        hybrid_results = reciprocal_rank_fusion(
            dense_results,
            bm25_results
        )

        # Preserve Top-10 candidates for cross-encoder reranking.
        hybrid_candidates = hybrid_results[:RERANK_CANDIDATE_K]

        # Preserve Top-5 as the current hybrid baseline.
        final_results = hybrid_results[:FINAL_TOP_K]

        all_results.append({
            "query": query,
            "strategy": strategy,
            "dense_results": dense_results,
            "bm25_results": bm25_results,
            "hybrid_candidates": hybrid_candidates,
            "hybrid_results": final_results
        })

        print("\nQUERY:", query)

        print("\nTop-5 Hybrid Results:")

        for rank, result in enumerate(final_results, start=1):

            print(
                f"{rank}. {result['source_id']} | "
                f"Page {result['page']} | "
                f"RRF: {result['rrf_score']:.6f}"
            )

        print(
            f"Saved {len(hybrid_candidates)} candidates "
            "for reranking."
        )

    return all_results


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():

    queries = [
        "What should I do if I receive a phishing email?",
        "How can I protect my online accounts using multi-factor authentication?",
        "What should I do if my account has been compromised?",
        "How should passwords be stored securely?",
        "What are the steps involved in responding to a cybersecurity incident?"
    ]

    fixed_results = run_experiment("fixed", queries)

    recursive_results = run_experiment("recursive", queries)

    all_results = fixed_results + recursive_results

    output_path = OUTPUT_DIR / "hybrid_results.json"

    with open(output_path, "w", encoding="utf-8") as file:

        json.dump(
            all_results,
            file,
            indent=4,
            ensure_ascii=False
        )

    print("\n" + "=" * 70)
    print("HYBRID RETRIEVAL COMPLETED")
    print("=" * 70)

    print("Total searches:", len(all_results))
    print("Reranking candidates per query:", RERANK_CANDIDATE_K)
    print("Final Top-K:", FINAL_TOP_K)
    print("RRF constant:", RRF_K)
    print("Results saved to:", output_path)


if __name__ == "__main__":
    main()
