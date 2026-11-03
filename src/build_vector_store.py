
import json
import pickle
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent

CHUNK_DIR = ROOT / "data" / "processed" / "chunks"
VECTOR_DIR = ROOT / "vector_store"

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

STRATEGIES = ["fixed", "recursive"]


# --------------------------------------------------
# LOAD MODEL
# --------------------------------------------------

print("Loading embedding model...")

model = SentenceTransformer(MODEL_NAME)

print("Model loaded.")
print("Embedding dimension:", model.get_sentence_embedding_dimension())


# --------------------------------------------------
# LOAD CHUNKS
# --------------------------------------------------

def load_chunks(strategy):

    file_path = CHUNK_DIR / f"{strategy}_chunks.jsonl"

    chunks = []

    with open(file_path, "r", encoding="utf-8") as file:

        for line in file:

            if line.strip():
                chunks.append(json.loads(line))

    return chunks


# --------------------------------------------------
# BUILD VECTOR STORE
# --------------------------------------------------

def build_index(strategy):

    print("\n" + "=" * 55)
    print(f"BUILDING {strategy.upper()} VECTOR STORE")
    print("=" * 55)

    chunks = load_chunks(strategy)

    if not chunks:
        raise ValueError(f"No chunks found for {strategy}")

    texts = [chunk["text"] for chunk in chunks]

    print("Chunks loaded:", len(texts))

    print("Generating embeddings...")

    embeddings = model.encode(
        texts,
        batch_size=32,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True
    )

    embeddings = np.asarray(embeddings, dtype="float32")

    print("Embedding shape:", embeddings.shape)

    # Normalized vectors + inner product = cosine similarity
    dimension = embeddings.shape[1]

    index = faiss.IndexFlatIP(dimension)

    index.add(embeddings)

    # Save FAISS index
    VECTOR_DIR.mkdir(parents=True, exist_ok=True)

    index_path = VECTOR_DIR / f"{strategy}_index.faiss"

    faiss.write_index(index, str(index_path))

    # Save metadata in the exact same order as vectors
    metadata_path = VECTOR_DIR / f"{strategy}_metadata.pkl"

    with open(metadata_path, "wb") as file:
        pickle.dump(chunks, file)

    print("\nVector store created successfully.")
    print("Index:", index_path)
    print("Metadata:", metadata_path)
    print("Stored vectors:", index.ntotal)


# --------------------------------------------------
# MAIN
# --------------------------------------------------

if __name__ == "__main__":

    for strategy in STRATEGIES:
        build_index(strategy)

    print("\nAll vector stores built successfully.")
