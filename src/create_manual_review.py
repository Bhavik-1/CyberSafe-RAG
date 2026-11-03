
import json
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

GENERATION_FILE = ROOT / "evaluation" / "generation_results.json"
GROUND_TRUTH_FILE = ROOT / "evaluation" / "answer_ground_truth.json"

OUTPUT_FILE = ROOT / "evaluation" / "manual_review.csv"


def main():

    with open(GENERATION_FILE, "r", encoding="utf-8") as f:
        generation = json.load(f)

    with open(GROUND_TRUTH_FILE, "r", encoding="utf-8") as f:
        ground_truth = json.load(f)

    rows = []

    for reference in ground_truth:

        query = reference["query"]

        generated = next(
            (
                item for item in generation["results"]
                if item.get("query") == query
                and item.get("status") == "success"
            ),
            None
        )

        if generated is None:
            continue

        rows.append({
            "question": query,
            "expected_points": " | ".join(
                reference["expected_points"]
            ),
            "generated_answer": generated["answer"],
            "factual_correctness_1_to_5": "",
            "faithfulness_1_to_5": "",
            "citation_support_1_to_5": "",
            "answer_relevance_1_to_5": "",
            "clarity_1_to_5": "",
            "unsupported_claims_yes_no": "",
            "abstention_appropriate_yes_no": "",
            "review_comments": ""
        })

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    fields = list(rows[0].keys()) if rows else []

    with open(
        OUTPUT_FILE,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fields
        )

        writer.writeheader()
        writer.writerows(rows)

    print("MANUAL EVALUATION SHEET CREATED")
    print("Questions:", len(rows))
    print("File:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
