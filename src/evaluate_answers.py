
import json
import re
import csv
from pathlib import Path
from collections import Counter


# --------------------------------------------------
# 1. PATHS
# --------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent

GROUND_TRUTH_FILE = ROOT / "evaluation" / "answer_ground_truth.json"
GENERATION_FILE = ROOT / "evaluation" / "generation_results.json"
RERANKED_FILE = ROOT / "evaluation" / "reranked_results.json"

OUTPUT_JSON = ROOT / "evaluation" / "answer_metrics.json"
OUTPUT_CSV = ROOT / "evaluation" / "answer_metrics.csv"
DETAILS_CSV = ROOT / "evaluation" / "answer_point_details.csv"

STRATEGY = "fixed"


# --------------------------------------------------
# 2. LOAD FILES
# --------------------------------------------------

def load_json(path):

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


# --------------------------------------------------
# 3. TEXT PROCESSING
# --------------------------------------------------

STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were",
    "to", "of", "in", "on", "for", "and", "or",
    "with", "by", "from", "that", "this", "it",
    "as", "be", "using", "use", "should", "must",
    "can", "could", "your", "you", "their", "they",
    "do", "not", "if", "when", "such", "than",
    "into", "about", "also", "may", "has", "have"
}


def tokenize(text):

    words = re.findall(r"[a-zA-Z0-9]+", text.lower())

    return [
        word for word in words
        if word not in STOPWORDS and len(word) > 1
    ]


# --------------------------------------------------
# 4. EXPECTED POINT COVERAGE
# --------------------------------------------------

def calculate_point_coverage(answer, expected_points):

    answer_tokens = set(tokenize(answer))

    point_results = []

    for point in expected_points:

        point_tokens = set(tokenize(point))

        if not point_tokens:
            continue

        matched = point_tokens.intersection(answer_tokens)

        coverage = len(matched) / len(point_tokens)

        # Heuristic threshold, not semantic verification.
        covered = coverage >= 0.40

        point_results.append({
            "expected_point": point,
            "coverage": round(coverage, 3),
            "covered": covered,
            "matched_terms": sorted(matched)
        })

    total = len(point_results)

    covered_count = sum(
        item["covered"] for item in point_results
    )

    score = (
        covered_count / total
        if total else 0
    )

    return {
        "score": round(score, 3),
        "covered_points": covered_count,
        "total_points": total,
        "details": point_results
    }


# --------------------------------------------------
# 5. ABSTENTION EVALUATION
# --------------------------------------------------

ABSTENTION_PHRASES = [
    "insufficient evidence",
    "evidence is insufficient",
    "does not contain enough evidence",
    "does not provide enough information",
    "information is missing",
    "cannot provide a complete",
    "not enough evidence",
    "not contain a complete",
    "unable to provide a complete"
]


def detect_abstention(answer):

    answer_lower = answer.lower()

    return any(
        phrase in answer_lower
        for phrase in ABSTENTION_PHRASES
    )


def evaluate_abstention(answer, must_abstain):

    detected = detect_abstention(answer)

    if must_abstain:
        correct = detected
    else:
        correct = not detected

    return {
        "expected_abstention": must_abstain,
        "detected_abstention": detected,
        "correct": correct
    }


# --------------------------------------------------
# 6. CITATION VALIDATION
# --------------------------------------------------

CITATION_PATTERN = re.compile(
    r"\[Evidence\s+(\d+),\s*p\.?\s*(\d+)\]",
    re.IGNORECASE
)


def evaluate_citations(answer, chunks):

    citations = CITATION_PATTERN.findall(answer)

    valid_count = 0
    invalid_count = 0

    citation_details = []

    for evidence_number, cited_page in citations:

        evidence_number = int(evidence_number)
        cited_page = str(cited_page)

        valid = False
        reason = ""

        if evidence_number < 1 or evidence_number > len(chunks):

            reason = "Evidence number does not exist"

        else:

            chunk = chunks[evidence_number - 1]

            actual_page = str(chunk.get("page", ""))

            if actual_page == cited_page:

                valid = True
                reason = "Evidence number and page match"

            else:

                reason = (
                    f"Page mismatch: retrieved page is "
                    f"{actual_page}"
                )

        if valid:
            valid_count += 1
        else:
            invalid_count += 1

        citation_details.append({
            "evidence_number": evidence_number,
            "cited_page": cited_page,
            "valid": valid,
            "reason": reason
        })

    total = len(citations)

    accuracy = (
        valid_count / total
        if total else 0
    )

    return {
        "total_citations": total,
        "valid_citations": valid_count,
        "invalid_citations": invalid_count,
        "citation_accuracy": round(accuracy, 3),
        "details": citation_details
    }


# --------------------------------------------------
# 7. MAIN EVALUATION
# --------------------------------------------------

def main():

    ground_truth = load_json(GROUND_TRUTH_FILE)

    generation_data = load_json(GENERATION_FILE)

    reranked_data = load_json(RERANKED_FILE)

    generation_results = generation_data["results"]

    evaluation_results = []
    point_details = []

    for reference in ground_truth:

        query = reference["query"]

        expected_points = reference["expected_points"]

        must_abstain = reference.get(
            "must_abstain", False
        )

        generated = next(
            (
                item for item in generation_results
                if item.get("query") == query
            ),
            None
        )

        retrieved = next(
            (
                item for item in reranked_data
                if item.get("query") == query
                and item.get("strategy") == STRATEGY
            ),
            None
        )

        if generated is None:
            print(f"Missing generation result: {query}")
            continue

        if generated.get("status") != "success":
            print(f"Generation unsuccessful: {query}")
            continue

        if retrieved is None:
            print(f"Missing retrieval result: {query}")
            continue

        answer = generated.get("answer", "")

        chunks = retrieved.get(
            "reranked_results", []
        )[:5]

        # Evaluate expected-point coverage.
        coverage = calculate_point_coverage(
            answer,
            expected_points
        )

        # Evaluate citations.
        citations = evaluate_citations(
            answer,
            chunks
        )

        # Evaluate abstention.
        abstention = evaluate_abstention(
            answer,
            must_abstain
        )

        latency = generated.get(
            "api_latency", 0
        )

        result = {
            "query": query,
            "point_coverage": coverage["score"],
            "covered_points": coverage["covered_points"],
            "total_points": coverage["total_points"],
            "citation_accuracy": citations["citation_accuracy"],
            "valid_citations": citations["valid_citations"],
            "invalid_citations": citations["invalid_citations"],
            "total_citations": citations["total_citations"],
            "expected_abstention": abstention["expected_abstention"],
            "detected_abstention": abstention["detected_abstention"],
            "abstention_correct": abstention["correct"],
            "latency_seconds": latency
        }

        evaluation_results.append(result)

        for detail in coverage["details"]:

            point_details.append({
                "query": query,
                **detail
            })

    # --------------------------------------------------
    # 8. OVERALL METRICS
    # --------------------------------------------------

    total_questions = len(evaluation_results)

    if total_questions == 0:
        print("No questions could be evaluated.")
        return

    average_coverage = sum(
        x["point_coverage"] for x in evaluation_results
    ) / total_questions

    average_citation_accuracy = sum(
        x["citation_accuracy"] for x in evaluation_results
    ) / total_questions

    abstention_accuracy = sum(
        x["abstention_correct"] for x in evaluation_results
    ) / total_questions

    average_latency = sum(
        x["latency_seconds"] for x in evaluation_results
    ) / total_questions

    total_citations = sum(
        x["total_citations"] for x in evaluation_results
    )

    valid_citations = sum(
        x["valid_citations"] for x in evaluation_results
    )

    overall_citation_accuracy = (
        valid_citations / total_citations
        if total_citations else 0
    )

    summary = {
        "total_questions": total_questions,
        "average_point_coverage": round(average_coverage, 3),
        "average_question_citation_accuracy": round(
            average_citation_accuracy, 3
        ),
        "overall_citation_accuracy": round(
            overall_citation_accuracy, 3
        ),
        "abstention_accuracy": round(abstention_accuracy, 3),
        "average_generation_latency_seconds": round(
            average_latency, 2
        ),
        "total_citations": total_citations,
        "valid_citations": valid_citations
    }

    # --------------------------------------------------
    # 9. SAVE JSON
    # --------------------------------------------------

    output = {
        "evaluation_type": "Automated heuristic evaluation",
        "notes": [
            "Point coverage uses lexical token overlap.",
            "Citation validation checks evidence index and page.",
            "Citation validity does not prove semantic support.",
            "Abstention detection uses predefined text patterns.",
            "Faithfulness and semantic correctness require manual review."
        ],
        "summary": summary,
        "question_results": evaluation_results
    }

    with open(OUTPUT_JSON, "w", encoding="utf-8") as file:

        json.dump(
            output,
            file,
            indent=4,
            ensure_ascii=False
        )

    # --------------------------------------------------
    # 10. SAVE QUESTION METRICS CSV
    # --------------------------------------------------

    with open(
        OUTPUT_CSV,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=evaluation_results[0].keys()
        )

        writer.writeheader()
        writer.writerows(evaluation_results)

    # --------------------------------------------------
    # 11. SAVE POINT DETAILS CSV
    # --------------------------------------------------

    with open(
        DETAILS_CSV,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        fields = [
            "query",
            "expected_point",
            "coverage",
            "covered",
            "matched_terms"
        ]

        writer = csv.DictWriter(
            file,
            fieldnames=fields
        )

        writer.writeheader()

        for item in point_details:

            row = item.copy()

            row["matched_terms"] = ", ".join(
                row["matched_terms"]
            )

            writer.writerow(row)

    # --------------------------------------------------
    # 12. PRINT RESULTS
    # --------------------------------------------------

    print("\n" + "=" * 75)
    print("CYBERSAFE RAG - ANSWER EVALUATION")
    print("=" * 75)

    for index, result in enumerate(
        evaluation_results, start=1
    ):

        print(f"\nQUESTION {index}: {result['query']}")

        print(
            f"Point coverage: "
            f"{result['covered_points']}/"
            f"{result['total_points']} "
            f"({result['point_coverage']:.2%})"
        )

        print(
            f"Citation accuracy: "
            f"{result['citation_accuracy']:.2%}"
        )

        print(
            f"Abstention correct: "
            f"{result['abstention_correct']}"
        )

        print(
            f"Latency: "
            f"{result['latency_seconds']} seconds"
        )

    print("\n" + "=" * 75)
    print("OVERALL EVALUATION SUMMARY")
    print("=" * 75)

    print(f"Questions evaluated: {summary['total_questions']}")
    print(f"Average point coverage: {summary['average_point_coverage']:.2%}")
    print(f"Average question citation accuracy: {summary['average_question_citation_accuracy']:.2%}")
    print(f"Overall citation accuracy: {summary['overall_citation_accuracy']:.2%}")
    print(f"Abstention accuracy: {summary['abstention_accuracy']:.2%}")
    print(f"Average generation latency: {summary['average_generation_latency_seconds']} sec")

    print("\nFILES GENERATED:")
    print(OUTPUT_JSON)
    print(OUTPUT_CSV)
    print(DETAILS_CSV)

    print("\nANSWER EVALUATION COMPLETED")


if __name__ == "__main__":
    main()
