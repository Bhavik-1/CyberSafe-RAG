
import pickle
from pathlib import Path

import faiss
from sentence_transformers import SentenceTransformer


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
VECTOR_DIR = ROOT / "vector_store"

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

TOP_K = 5

model = SentenceTransformer(MODEL_NAME)


# --------------------------------------------------
# LOAD VECTOR STORE
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
# RETRIEVE RELEVANT CHUNKS
# --------------------------------------------------

def retrieve(query, strategy, top_k=TOP_K):

    index, metadata = load_vector_store(strategy)

    query_embedding = model.encode(
        [query],
        convert_to_numpy=True,
        normalize_embeddings=True
    )

    scores, indices = index.search(
        query_embedding.astype("float32"),
        top_k
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
            "issuer": chunk["issuer"],
            "page": chunk["page"],
            "text": chunk["text"]
        })

    return results


# --------------------------------------------------
# DISPLAY RESULTS
# --------------------------------------------------

def display_results(query, strategy):

    print("\n" + "=" * 75)
    print(f"STRATEGY: {strategy.upper()}")
    print("=" * 75)

    print("QUESTION:", query)

    results = retrieve(query, strategy)

    for rank, result in enumerate(results, start=1):

        print("\n" + "-" * 75)
        print(f"RANK: {rank}")
        print(f"SCORE: {result['score']:.4f}")
        print(f"CHUNK ID: {result['chunk_id']}")
        print(f"SOURCE: {result['source_title']}")
        print(f"ISSUER: {result['issuer']}")
        print(f"PAGE: {result['page']}")

        print("\nTEXT:")
        print(result["text"])


# --------------------------------------------------
# MAIN
# --------------------------------------------------

if __name__ == "__main__":

    queries = [
        "What should I do if I receive a phishing email?",
        "How can I protect my online accounts using multi-factor authentication?",
        "What should I do if my account has been compromised?",
        "How should passwords be stored securely?",
        "What are the steps involved in responding to a cybersecurity incident?"
    ]

    # Save retrieval results instead of printing everything

import json

all_results = []

for query in queries:

    for strategy in ["fixed", "recursive"]:

        results = retrieve(query, strategy)

        all_results.append({
            "query": query,
            "strategy": strategy,
            "results": results
        })

output_path = ROOT / "evaluation" / "retrieval_results.json"

with open(output_path, "w", encoding="utf-8") as file:
    json.dump(all_results, file, indent=4, ensure_ascii=False)

print("\nRetrieval testing completed!")
print("Results saved to:", output_path)
