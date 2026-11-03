
import json
from pathlib import Path

from sentence_transformers import CrossEncoder


# --------------------------------------------------
# 1. CONFIGURATION
# --------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
EVALUATION_DIR = ROOT / "evaluation"

INPUT_FILE = EVALUATION_DIR / "hybrid_results.json"
OUTPUT_FILE = EVALUATION_DIR / "reranked_results.json"

MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"

TOP_K = 5
BATCH_SIZE = 16


# --------------------------------------------------
# 2. LOAD CROSS-ENCODER MODEL
# --------------------------------------------------

print("\nLoading Cross-Encoder model...")

reranker = CrossEncoder(MODEL_NAME)

print("Cross-Encoder model loaded successfully!")


# --------------------------------------------------
# 3. LOAD HYBRID RETRIEVAL RESULTS
# --------------------------------------------------

def load_hybrid_results():

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input file not found: {INPUT_FILE}\n"
            "Run test_hybrid.py first."
        )

    with open(INPUT_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError(
            "Expected hybrid_results.json to contain a list."
        )

    print(f"\nLoaded {len(data)} hybrid experiments.")

    return data


# --------------------------------------------------
# 4. RERANK CANDIDATES
# --------------------------------------------------

def rerank_experiment(experiment):

    query = experiment["query"]
    strategy = experiment["strategy"]

    candidates = experiment.get("hybrid_candidates")

    if not candidates:
        raise ValueError(
            f"No hybrid_candidates found for query: {query}"
        )

    # Create query-document pairs for Cross-Encoder
    pairs = [
        (query, candidate["text"])
        for candidate in candidates
    ]

    # Predict relevance scores
    scores = reranker.predict(
        pairs,
        batch_size=BATCH_SIZE,
        show_progress_bar=False
    )

    # Attach Cross-Encoder scores to candidates
    reranked_candidates = []

    for candidate, score in zip(candidates, scores):

        result = candidate.copy()

        result["cross_encoder_score"] = float(score)

        reranked_candidates.append(result)

    # Sort by Cross-Encoder score (highest first)
    reranked_candidates.sort(
        key=lambda item: item["cross_encoder_score"],
        reverse=True
    )

    # Select Top 5
    reranked_results = reranked_candidates[:TOP_K]

    return {
        "query": query,
        "strategy": strategy,
        "candidate_count": len(candidates),
        "reranked_candidates": reranked_candidates,
        "reranked_results": reranked_results
    }


# --------------------------------------------------
# 5. DISPLAY RESULTS
# --------------------------------------------------

def display_results(experiment):

    print("\n" + "=" * 90)
    print(f"QUERY: {experiment['query']}")
    print(f"STRATEGY: {experiment['strategy'].upper()}")
    print("=" * 90)

    for rank, result in enumerate(
        experiment["reranked_results"],
        start=1
    ):

        print(f"\nRank: {rank}")

        print(
            f"Cross-Encoder Score: "
            f"{result['cross_encoder_score']:.4f}"
        )

        print(f"Source: {result.get('source_id', 'Unknown')}")
        print(f"Page: {result.get('page', 'Unknown')}")
        print(f"Chunk ID: {result.get('chunk_id', 'Unknown')}")

        print("\nText:")
        print(result["text"][:500])

        print("-" * 90)


# --------------------------------------------------
# 6. MAIN EXECUTION
# --------------------------------------------------

def main():

    experiments = load_hybrid_results()

    all_reranked_results = []

    for number, experiment in enumerate(experiments, start=1):

        print(
            f"\nProcessing experiment "
            f"{number}/{len(experiments)}..."
        )

        reranked = rerank_experiment(experiment)

        all_reranked_results.append(reranked)

        display_results(reranked)

    # Save results separately; do not overwrite hybrid results
    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            all_reranked_results,
            file,
            indent=4,
            ensure_ascii=False
        )

    print("\n" + "=" * 90)
    print("RERANKING COMPLETED SUCCESSFULLY!")
    print("=" * 90)

    print(f"Experiments processed: {len(all_reranked_results)}")
    print(f"Top results per experiment: {TOP_K}")
    print(f"Output saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
