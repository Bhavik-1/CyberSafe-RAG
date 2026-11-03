
import json
import csv
from pathlib import Path
from collections import defaultdict


# --------------------------------------------------
# 1. CONFIGURATION
# --------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
EVALUATION_DIR = ROOT / "evaluation"

GROUND_TRUTH_FILE = EVALUATION_DIR / "ground_truth.json"
HYBRID_FILE = EVALUATION_DIR / "hybrid_results.json"
RERANKED_FILE = EVALUATION_DIR / "reranked_results.json"

OUTPUT_CSV = EVALUATION_DIR / "retrieval_metrics.csv"
SUMMARY_CSV = EVALUATION_DIR / "retrieval_summary.csv"
OUTPUT_JSON = EVALUATION_DIR / "retrieval_metrics.json"

TOP_K = 5

METHODS = [
    "Dense",
    "BM25",
    "Hybrid RRF",
    "Hybrid + Cross-Encoder"
]


# --------------------------------------------------
# 2. LOAD JSON FILES
# --------------------------------------------------

def load_json(path):

    if not path.exists():
        raise FileNotFoundError(
            f"File not found: {path}"
        )

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


# --------------------------------------------------
# 3. CALCULATE EVALUATION METRICS
# --------------------------------------------------

def precision_at_k(retrieved_ids, relevant_ids, k=TOP_K):

    top_results = retrieved_ids[:k]

    if not top_results:
        return 0.0

    relevant_count = sum(
        1 for chunk_id in top_results
        if chunk_id in relevant_ids
    )

    return relevant_count / k


def recall_at_k(retrieved_ids, relevant_ids, k=TOP_K):

    if not relevant_ids:
        return 0.0

    top_results = retrieved_ids[:k]

    relevant_count = sum(
        1 for chunk_id in top_results
        if chunk_id in relevant_ids
    )

    return relevant_count / len(relevant_ids)


def mean_reciprocal_rank(retrieved_ids, relevant_ids):

    for rank, chunk_id in enumerate(retrieved_ids, start=1):

        if chunk_id in relevant_ids:
            return 1.0 / rank

    return 0.0


def ndcg_at_k(retrieved_ids, relevant_ids, k=TOP_K):

    top_results = retrieved_ids[:k]

    dcg = 0.0

    for rank, chunk_id in enumerate(top_results, start=1):

        relevance = 1 if chunk_id in relevant_ids else 0

        dcg += relevance / __import__("math").log2(rank + 1)

    ideal_relevant_count = min(len(relevant_ids), k)

    if ideal_relevant_count == 0:
        return 0.0

    ideal_dcg = sum(
        1 / __import__("math").log2(rank + 1)
        for rank in range(1, ideal_relevant_count + 1)
    )

    return dcg / ideal_dcg


# --------------------------------------------------
# 4. PREPARE GROUND TRUTH
# --------------------------------------------------

def get_relevant_ids(ground_truth, query, strategy):

    for item in ground_truth:

        if item["query"] == query:

            marker = f"_{strategy.upper()}_"

            relevant_ids = [
                chunk_id
                for chunk_id in item["relevant_chunk_ids"]
                if marker in chunk_id
            ]

            return set(relevant_ids)

    raise ValueError(
        f"Ground truth missing for query: {query}"
    )


# --------------------------------------------------
# 5. EXTRACT RETRIEVED CHUNK IDS
# --------------------------------------------------

def extract_ids(results):

    return [
        item["chunk_id"]
        for item in results
        if "chunk_id" in item
    ]


# --------------------------------------------------
# 6. EVALUATE ONE EXPERIMENT
# --------------------------------------------------

def evaluate_method(
    query,
    strategy,
    method,
    retrieved_results,
    relevant_ids
):

    retrieved_ids = extract_ids(retrieved_results)

    metrics = {
        "precision_at_5": precision_at_k(
            retrieved_ids, relevant_ids
        ),
        "recall_at_5": recall_at_k(
            retrieved_ids, relevant_ids
        ),
        "mrr": mean_reciprocal_rank(
            retrieved_ids, relevant_ids
        ),
        "ndcg_at_5": ndcg_at_k(
            retrieved_ids, relevant_ids
        )
    }

    return {
        "query": query,
        "strategy": strategy,
        "method": method,
        "relevant_chunk_count": len(relevant_ids),
        "retrieved_chunk_count": len(retrieved_ids),
        **metrics
    }


# --------------------------------------------------
# 7. MAIN EVALUATION
# --------------------------------------------------

def main():

    print("\nLoading evaluation files...")

    ground_truth = load_json(GROUND_TRUTH_FILE)
    hybrid_data = load_json(HYBRID_FILE)
    reranked_data = load_json(RERANKED_FILE)

    print("All files loaded successfully.")

    # Map reranked experiments by query and strategy
    reranked_lookup = {
        (item["query"], item["strategy"]): item
        for item in reranked_data
    }

    all_results = []

    # Evaluate each query and chunking strategy
    for experiment in hybrid_data:

        query = experiment["query"]
        strategy = experiment["strategy"]

        print(
            f"\nEvaluating: {query}"
            f"\nStrategy: {strategy}"
        )

        relevant_ids = get_relevant_ids(
            ground_truth,
            query,
            strategy
        )

        if not relevant_ids:
            raise ValueError(
                f"No relevant labels for {query} ({strategy}). "
                "Check ground_truth.json."
            )

        reranked_experiment = reranked_lookup.get(
            (query, strategy)
        )

        if reranked_experiment is None:
            raise ValueError(
                f"Missing reranked results for {query} ({strategy})"
            )

        # Four retrieval approaches
        method_results = {
            "Dense": experiment["dense_results"][:TOP_K],

            "BM25": experiment["bm25_results"][:TOP_K],

            "Hybrid RRF": experiment["hybrid_results"][:TOP_K],

            "Hybrid + Cross-Encoder":
                reranked_experiment["reranked_results"][:TOP_K]
        }

        for method, retrieved_results in method_results.items():

            result = evaluate_method(
                query,
                strategy,
                method,
                retrieved_results,
                relevant_ids
            )

            all_results.append(result)

            print(
                f"{method:25s} "
                f"P@5={result['precision_at_5']:.3f} "
                f"R@5={result['recall_at_5']:.3f} "
                f"MRR={result['mrr']:.3f} "
                f"NDCG@5={result['ndcg_at_5']:.3f}"
            )

    # --------------------------------------------------
    # 8. CALCULATE AVERAGE METRICS
    # --------------------------------------------------

    summary = []

    grouped = defaultdict(list)

    for result in all_results:

        key = (result["strategy"], result["method"])

        grouped[key].append(result)

    metric_names = [
        "precision_at_5",
        "recall_at_5",
        "mrr",
        "ndcg_at_5"
    ]

    for (strategy, method), results in grouped.items():

        row = {
            "strategy": strategy,
            "method": method,
            "query_count": len(results)
        }

        for metric in metric_names:

            row[metric] = sum(
                result[metric] for result in results
            ) / len(results)

        summary.append(row)

    # --------------------------------------------------
    # 9. SAVE DETAILED RESULTS
    # --------------------------------------------------

    with open(OUTPUT_JSON, "w", encoding="utf-8") as file:

        json.dump(
            all_results,
            file,
            indent=4,
            ensure_ascii=False
        )

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as file:

        writer = csv.DictWriter(
            file,
            fieldnames=all_results[0].keys()
        )

        writer.writeheader()
        writer.writerows(all_results)

    with open(SUMMARY_CSV, "w", newline="", encoding="utf-8") as file:

        writer = csv.DictWriter(
            file,
            fieldnames=summary[0].keys()
        )

        writer.writeheader()
        writer.writerows(summary)

    # --------------------------------------------------
    # 10. DISPLAY FINAL SUMMARY
    # --------------------------------------------------

    print("\n" + "=" * 100)
    print("RETRIEVAL EVALUATION SUMMARY")
    print("=" * 100)

    print(
        f"{'Strategy':12s} "
        f"{'Method':27s} "
        f"{'P@5':8s} "
        f"{'R@5':8s} "
        f"{'MRR':8s} "
        f"{'NDCG@5':8s}"
    )

    print("-" * 100)

    for row in summary:

        print(
            f"{row['strategy']:12s} "
            f"{row['method']:27s} "
            f"{row['precision_at_5']:.3f}   "
            f"{row['recall_at_5']:.3f}   "
            f"{row['mrr']:.3f}   "
            f"{row['ndcg_at_5']:.3f}"
        )

    print("\nEvaluation completed successfully!")

    print(f"Detailed JSON: {OUTPUT_JSON}")
    print(f"Detailed CSV:  {OUTPUT_CSV}")
    print(f"Summary CSV:   {SUMMARY_CSV}")


if __name__ == "__main__":
    main()
