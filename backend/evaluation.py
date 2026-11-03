
import csv
import json
from pathlib import Path
from statistics import mean

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/api/evaluation", tags=["Evaluation"])

ROOT_DIR = Path(__file__).resolve().parent.parent
EVALUATION_DIR = ROOT_DIR / "evaluation"

RATING_COLUMNS = {
    "factual_correctness": "factual_correctness_1_to_5",
    "faithfulness": "faithfulness_1_to_5",
    "citation_support": "citation_support_1_to_5",
    "answer_relevance": "answer_relevance_1_to_5",
    "clarity": "clarity_1_to_5",
}


def read_csv_file(filename: str) -> list[dict]:
    path = EVALUATION_DIR / filename

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Evaluation file not found: {filename}",
        )

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def read_json_file(filename: str) -> dict | list:
    path = EVALUATION_DIR / filename

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Evaluation file not found: {filename}",
        )

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Invalid JSON in {filename}: {exc}",
        )


def to_number(value):
    try:
        if value is None or str(value).strip() == "":
            return None
        return float(value)
    except (ValueError, TypeError):
        return None


def average(values: list[float]) -> float | None:
    return round(mean(values), 3) if values else None


def get_manual_review_data() -> dict:
    rows = read_csv_file("manual_review.csv")

    rating_values = {
        key: []
        for key in RATING_COLUMNS
    }

    reviewed_rows = []

    for row in rows:
        ratings = {}

        for key, column in RATING_COLUMNS.items():
            value = to_number(row.get(column))
            ratings[key] = value

            if value is not None:
                rating_values[key].append(value)

        valid_ratings = [
            value for value in ratings.values()
            if value is not None
        ]

        reviewed_rows.append({
            "question": row.get("question", ""),
            "ratings": ratings,
            "average_score": average(valid_ratings),
            "unsupported_claims": row.get(
                "unsupported_claims_yes_no", ""
            ),
            "abstention_appropriate": row.get(
                "abstention_appropriate_yes_no", ""
            ),
            "review_comments": row.get("review_comments", ""),
        })

    averages = {
        key: average(values)
        for key, values in rating_values.items()
    }

    all_scores = [
        score
        for values in rating_values.values()
        for score in values
    ]

    return {
        "total_questions": len(rows),
        "reviewed_questions": sum(
            1 for row in reviewed_rows
            if any(value is not None for value in row["ratings"].values())
        ),
        "criteria_averages": averages,
        "overall_average": average(all_scores),
        "rows": reviewed_rows,
        "scale": "1 to 5",
    }


@router.get("/dashboard")
def get_evaluation_dashboard():
    retrieval_summary = read_csv_file("retrieval_summary.csv")
    retrieval_details = read_csv_file("retrieval_metrics.csv")
    answer_data = read_json_file("answer_metrics.json")
    manual_data = get_manual_review_data()

    # Convert retrieval metrics into numeric values.
    for row in retrieval_summary:
        for key in (
            "query_count",
            "precision_at_5",
            "recall_at_5",
            "mrr",
            "ndcg_at_5",
        ):
            row[key] = to_number(row.get(key))

    for row in retrieval_details:
        for key in (
            "relevant_chunk_count",
            "retrieved_chunk_count",
            "precision_at_5",
            "recall_at_5",
            "mrr",
            "ndcg_at_5",
        ):
            row[key] = to_number(row.get(key))

    answer_summary = answer_data.get("summary", {})
    answer_questions = answer_data.get("question_results", [])

    return {
        "retrieval": {
            "summary": retrieval_summary,
            "details": retrieval_details,
        },
        "automated_answers": {
            "evaluation_type": answer_data.get("evaluation_type"),
            "notes": answer_data.get("notes", []),
            "summary": answer_summary,
            "questions": answer_questions,
        },
        "manual_review": manual_data,
    }


@router.get("/retrieval")
def get_retrieval_metrics(
    strategy: str = Query("fixed", pattern="^(fixed|recursive)$"),
):
    rows = read_csv_file("retrieval_metrics.csv")

    filtered = [
        row for row in rows
        if row.get("strategy") == strategy
    ]

    if not filtered:
        raise HTTPException(
            status_code=404,
            detail=f"No retrieval results found for strategy: {strategy}",
        )

    return {
        "strategy": strategy,
        "results": filtered,
    }


@router.get("/health")
def evaluation_health():
    required_files = [
        "retrieval_summary.csv",
        "retrieval_metrics.csv",
        "answer_metrics.json",
        "manual_review.csv",
    ]

    return {
        "status": "available",
        "files": {
            filename: (EVALUATION_DIR / filename).exists()
            for filename in required_files
        },
    }
