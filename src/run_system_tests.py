
import sys
import re
import json
import csv
import time
import argparse
from pathlib import Path
from datetime import datetime, timezone

import rag_pipeline as rag


# ============================================================
# 1. CONFIGURATION
# ============================================================

ROOT = Path(__file__).resolve().parents[1]
EVALUATION_DIR = ROOT / "evaluation"

TEST_CASES_FILE = EVALUATION_DIR / "system_test_cases.json"

JSON_OUTPUT = EVALUATION_DIR / "system_test_results.json"
CSV_OUTPUT = EVALUATION_DIR / "system_test_results.csv"
SUMMARY_OUTPUT = EVALUATION_DIR / "system_test_summary.json"

DEFAULT_STRATEGY = "fixed"

# Small delay between requests.
REQUEST_DELAY = 2

ABSTENTION_PHRASES = [
    "insufficient evidence",
    "evidence is insufficient",
    "not enough evidence",
    "cannot determine from the provided evidence",
    "cannot provide exact",
    "does not provide enough information",
    "not supported by the available evidence",
    "i don't have enough information",
    "i cannot verify",
    "the available documents do not",
    "the retrieved evidence does not",
]


# ============================================================
# 2. LOAD TEST CASES
# ============================================================

def load_test_cases():

    if not TEST_CASES_FILE.exists():
        raise FileNotFoundError(
            f"Test cases not found: {TEST_CASES_FILE}"
        )

    with open(TEST_CASES_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    test_cases = data.get("test_cases", [])

    if not test_cases:
        raise ValueError("No test cases found.")

    ids = [test["id"] for test in test_cases]

    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate test case IDs found.")

    required_fields = [
        "id",
        "category",
        "query",
        "expected_behavior",
        "expected_abstention",
    ]

    for test in test_cases:
        for field in required_fields:
            if field not in test:
                raise ValueError(
                    f"{test.get('id', 'Unknown')} is missing {field}"
                )

    return data, test_cases


# ============================================================
# 3. ABSTENTION DETECTION
# ============================================================

def detect_abstention(answer):

    text = answer.lower()

    return any(
        phrase in text
        for phrase in ABSTENTION_PHRASES
    )


# ============================================================
# 4. CITATION VALIDATION
# ============================================================

def validate_citations(answer, evidence):

    pattern = re.compile(
        r"\[Evidence\s+(\d+)\s*,\s*p\.?\s*(\d+)\]",
        re.IGNORECASE
    )

    matches = pattern.findall(answer)

    valid = []
    invalid = []

    for evidence_number, page_number in matches:

        number = int(evidence_number)
        page = int(page_number)

        if number < 1 or number > len(evidence):
            invalid.append({
                "citation": f"Evidence {number}, page {page}",
                "reason": "Evidence number does not exist"
            })
            continue

        referenced_chunk = evidence[number - 1]

        actual_page = referenced_chunk.get("page")

        if str(actual_page) != str(page):
            invalid.append({
                "citation": f"Evidence {number}, page {page}",
                "reason": f"Actual page is {actual_page}"
            })
            continue

        valid.append({
            "evidence_number": number,
            "page": page,
            "source_id": referenced_chunk.get("source_id"),
            "source_title": referenced_chunk.get("source_title")
        })

    return {
        "total": len(matches),
        "valid_count": len(valid),
        "invalid_count": len(invalid),
        "valid": valid,
        "invalid": invalid,
        "accuracy": (
            round(len(valid) / len(matches), 4)
            if matches else None
        )
    }


# ============================================================
# 5. EVALUATE ONE TEST
# ============================================================

def evaluate_test(test, pipeline_result):

    answer = pipeline_result.get("answer", "")

    evidence = pipeline_result.get("results", [])

    generation_status = pipeline_result.get(
        "status", "not_generated"
    )

    expected_abstention = test["expected_abstention"]

    detected_abstention = detect_abstention(answer)

    citation_result = validate_citations(
        answer,
        evidence
    )

    abstention_correct = (
        expected_abstention == detected_abstention
    )

    generation_success = generation_status == "success"

    citations_valid = (
        citation_result["invalid_count"] == 0
    )

    # A test passes only when generation succeeded,
    # expected abstention behaviour was observed,
    # and every citation reference is structurally valid.
    # Semantic correctness still requires human review.

    passed = (
        generation_success
        and abstention_correct
        and citations_valid
        and bool(answer.strip())
    )

    if not generation_success:
        status = "ERROR"

    elif not abstention_correct:
        status = "REVIEW"

    elif not citations_valid:
        status = "REVIEW"

    elif passed:
        status = "PASSED - MANUAL REVIEW REQUIRED"

    else:
        status = "REVIEW"

    return {
        "test_id": test["id"],
        "category": test["category"],
        "query": test["query"],
        "expected_behavior": test["expected_behavior"],
        "expected_abstention": expected_abstention,
        "detected_abstention": detected_abstention,
        "abstention_correct": abstention_correct,
        "generation_status": generation_status,
        "generation_success": generation_success,
        "citation_total": citation_result["total"],
        "valid_citations": citation_result["valid_count"],
        "invalid_citations": citation_result["invalid_count"],
        "citation_accuracy": citation_result["accuracy"],
        "citation_details": citation_result,
        "evidence": evidence,
        "answer": answer,
        "retrieval_time_seconds": round(
            pipeline_result.get("total_time", 0)
            - pipeline_result.get("api_latency", 0),
            2
        ),
        "generation_latency_seconds": pipeline_result.get(
            "api_latency", 0
        ),
        "total_time_seconds": pipeline_result.get(
            "total_time", 0
        ),
        "status": status,
        "passed": passed,
        "manual_review_required": True
    }


# ============================================================
# 6. SAVE RESULTS
# ============================================================

def save_results(results, strategy):

    EVALUATION_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    passed = sum(
        1 for result in results
        if result["passed"]
    )

    errors = sum(
        1 for result in results
        if result["generation_status"] != "success"
    )

    summary = {
        "project": "CyberSafe RAG",
        "evaluation_type": "Automated system testing",
        "strategy": strategy,
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "total_tests": len(results),
        "passed_tests": passed,
        "failed_or_review_tests": len(results) - passed,
        "generation_errors": errors,
        "pass_rate": round(
            passed / len(results) * 100, 2
        ) if results else 0,
        "average_generation_latency_seconds": round(
            sum(
                r["generation_latency_seconds"]
                for r in results
            ) / len(results),
            2
        ) if results else 0,
        "average_total_time_seconds": round(
            sum(
                r["total_time_seconds"]
                for r in results
            ) / len(results),
            2
        ) if results else 0,
        "notes": [
            "Automated abstention detection uses predefined phrases.",
            "Citation validation checks evidence numbers and page references, not semantic support.",
            "A passed test still requires manual factual and faithfulness review.",
            "A REVIEW result is not automatically a system failure."
        ],
        "results": results
    }

    with open(
        JSON_OUTPUT,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            {
                "summary": summary,
                "results": results
            },
            file,
            indent=4,
            ensure_ascii=False
        )

    csv_fields = [
        "test_id",
        "category",
        "status",
        "passed",
        "generation_status",
        "expected_abstention",
        "detected_abstention",
        "abstention_correct",
        "citation_total",
        "valid_citations",
        "invalid_citations",
        "citation_accuracy",
        "retrieval_time_seconds",
        "generation_latency_seconds",
        "total_time_seconds",
        "manual_review_required"
    ]

    with open(
        CSV_OUTPUT,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=csv_fields
        )

        writer.writeheader()

        for result in results:

            writer.writerow({
                field: result.get(field)
                for field in csv_fields
            })

    with open(
        SUMMARY_OUTPUT,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            summary,
            file,
            indent=4,
            ensure_ascii=False
        )

    print("\n" + "=" * 65)
    print("SYSTEM TEST SUMMARY")
    print("=" * 65)

    print("Total tests:", summary["total_tests"])
    print("Passed:", summary["passed_tests"])
    print("Failed / Review:", summary["failed_or_review_tests"])
    print("Generation errors:", summary["generation_errors"])
    print("Pass rate:", f'{summary["pass_rate"]}%')

    print(
        "Average generation latency:",
        summary["average_generation_latency_seconds"],
        "seconds"
    )

    print("\nFiles saved:")
    print(JSON_OUTPUT)
    print(CSV_OUTPUT)
    print(SUMMARY_OUTPUT)


# ============================================================
# 7. MAIN TEST RUNNER
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description="CyberSafe RAG automated system tests"
    )

    parser.add_argument(
        "--strategy",
        choices=["fixed", "recursive"],
        default=DEFAULT_STRATEGY
    )

    parser.add_argument(
        "--start",
        type=int,
        default=1,
        help="Start from test number"
    )

    parser.add_argument(
        "--end",
        type=int,
        default=None,
        help="End at test number"
    )

    args = parser.parse_args()

    _, all_tests = load_test_cases()

    end = args.end or len(all_tests)

    if args.start < 1 or end > len(all_tests) or args.start > end:
        raise ValueError("Invalid test range.")

    selected_tests = all_tests[
        args.start - 1:end
    ]

    print("\n" + "=" * 65)
    print("CYBERSAFE RAG - AUTOMATED SYSTEM TESTING")
    print("=" * 65)

    print("Strategy:", args.strategy)
    print("Selected tests:", len(selected_tests))

    print("\nLoading models and retrieval components...")

    embedding_model, reranker = rag.load_models()

    components = rag.prepare_retrieval(
        args.strategy,
        embedding_model
    )

    if not rag.API_KEY:
        raise ValueError(
            "GEMINI_API_KEY missing from project .env"
        )

    from google import genai

    client = genai.Client(
        api_key=rag.API_KEY
    )

    print("\nAll components loaded successfully.")

    all_results = []

    for number, test in enumerate(
        selected_tests,
        start=args.start
    ):

        print("\n" + "=" * 65)
        print(
            f"TEST {number}/{len(all_tests)}: "
            f"{test['id']} - {test['category']}"
        )
        print("=" * 65)

        print("Question:", test["query"])

        start_time = time.perf_counter()

        try:

            pipeline_result = rag.run_query(
                test["query"],
                components,
                reranker,
                client
            )

            evaluated = evaluate_test(
                test,
                pipeline_result
            )

        except Exception as error:

            evaluated = {
                "test_id": test["id"],
                "category": test["category"],
                "query": test["query"],
                "answer": "",
                "evidence": [],
                "status": "ERROR",
                "passed": False,
                "generation_status": "exception",
                "error": str(error),
                "total_time_seconds": round(
                    time.perf_counter() - start_time,
                    2
                ),
                "manual_review_required": True
            }

        all_results.append(evaluated)

        print("\nTEST STATUS:", evaluated["status"])

        if "generation_latency_seconds" in evaluated:
            print(
                "Generation latency:",
                evaluated["generation_latency_seconds"],
                "seconds"
            )

        if "citation_accuracy" in evaluated:
            print(
                "Citation accuracy:",
                evaluated["citation_accuracy"]
            )

        print(
            "Abstention expected:",
            test["expected_abstention"]
        )

        if "detected_abstention" in evaluated:
            print(
                "Abstention detected:",
                evaluated["detected_abstention"]
            )

        if evaluated["generation_status"] == "rate_limited":
            print("\nStopping: Gemini API rate limit reached.")
            break

        if number < end:
            print(
                f"\nWaiting {REQUEST_DELAY} seconds..."
            )
            time.sleep(REQUEST_DELAY)

        # Save progress after each test.
        save_results(
            all_results,
            args.strategy
        )

    print("\nAutomated testing completed.")


if __name__ == "__main__":
    main()
