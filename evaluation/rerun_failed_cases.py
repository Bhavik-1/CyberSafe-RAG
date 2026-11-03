
import json
import time
import requests
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

TEST_FILE = PROJECT_ROOT / "evaluation" / "end_to_end_test_cases.json"
OUTPUT_FILE = PROJECT_ROOT / "evaluation" / "end_to_end_retest_results.json"

API_URL = "http://127.0.0.1:8000/api/chat"

TARGET_IDS = {
    "E2E-01",
    "E2E-02",
    "E2E-03",
    "E2E-04",
    "E2E-05",
    "E2E-06",
    "E2E-07",
    "E2E-08"
}


def run_retest():
    with open(TEST_FILE, "r", encoding="utf-8") as f:
        all_tests = json.load(f)

    test_cases = [
        test for test in all_tests
        if test["test_id"] in TARGET_IDS
    ]

    if not test_cases:
        print("No matching test cases found.")
        return

    results = []

    for test in test_cases:
        print("\n" + "=" * 70)
        print(f"Running {test['test_id']}: {test['category']}")
        print("=" * 70)

        start = time.perf_counter()

        try:
            response = requests.post(
                API_URL,
                json={"message": test["question"]},
                timeout=300
            )
            response.raise_for_status()

            data = response.json()
            elapsed = time.perf_counter() - start

            result = {
                "test_id": test["test_id"],
                "category": test["category"],
                "question": test["question"],
                "answerable": test["answerable"],
                "answer": data.get("answer", ""),
                "evidence": data.get("evidence", []),
                "citation_validation": data.get(
                    "citation_validation", {}
                ),
                "claim_verification": data.get(
                    "claim_verification", {}
                ),
                "latency_seconds": round(elapsed, 2),
                "cache_hit": data.get("cache_hit", False),
                "status": data.get("status", "unknown"),
                "error": None
            }

            validation = result["citation_validation"]
            claim_verification = result["claim_verification"]

            print("API status:", result["status"])
            print("Latency:", result["latency_seconds"], "seconds")
            print("Cache hit:", result["cache_hit"])
            print("Citation valid:", validation.get("valid"))
            print("Citation errors:", validation.get("errors", []))
            print("Claim verification status:", claim_verification.get("status"))
            print("Claims checked:", claim_verification.get("claim_count"))

            print("\nANSWER:\n")
            print(result["answer"])

        except Exception as error:
            result = {
                "test_id": test["test_id"],
                "category": test["category"],
                "question": test["question"],
                "answerable": test["answerable"],
                "answer": "",
                "evidence": [],
                "citation_validation": {},
                "claim_verification": {},
                "latency_seconds": None,
                "cache_hit": False,
                "status": "failed",
                "error": str(error)
            }

            print("ERROR:", error)

        results.append(result)

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=4, ensure_ascii=False)

    print("\n" + "=" * 70)
    print("END-TO-END REGRESSION SUMMARY")
    print("=" * 70)

    print("Total cases:", len(results))
    print(
        "API successful:",
        sum(r["status"] == "success" for r in results)
    )
    print(
        "Citation validation passed:",
        sum(
            r["citation_validation"].get("valid") is True
            for r in results
        )
    )
    print(
        "Claim verification available:",
        sum(
            bool(r["claim_verification"])
            for r in results
        )
    )

    print("Results saved to:", OUTPUT_FILE)


if __name__ == "__main__":
    run_retest()
