
import json
import time
import requests
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

TEST_FILE = PROJECT_ROOT / "evaluation" / "end_to_end_test_cases.json"
OUTPUT_FILE = PROJECT_ROOT / "evaluation" / "end_to_end_results.json"

API_URL = "http://127.0.0.1:8000/api/chat"


def run_evaluation():
    with open(TEST_FILE, "r", encoding="utf-8") as f:
        test_cases = json.load(f)

    results = []

    print("\n" + "=" * 70)
    print("CYBERSAFE RAG - END-TO-END EVALUATION")
    print("=" * 70)

    for index, test in enumerate(test_cases, start=1):
        test_id = test["test_id"]
        question = test["question"]

        print(f"\n[{index}/{len(test_cases)}] {test_id}")
        print("Question:", question)

        start = time.perf_counter()

        try:
            response = requests.post(
                API_URL,
                json={"message": question},
                timeout=300
            )

            elapsed = time.perf_counter() - start

            response.raise_for_status()
            data = response.json()

            result = {
                "test_id": test_id,
                "category": test["category"],
                "question": question,
                "answerable": test["answerable"],
                "answer": data.get("answer", ""),
                "evidence": data.get("evidence", []),
                "citation_validation": data.get(
                    "citation_validation", {}
                ),
                "latency_seconds": round(elapsed, 2),
                "api_latency": data.get("latency", 0),
                "cache_hit": data.get("cache_hit", False),
                "status": data.get("status", "unknown"),
                "error": None
            }

            print("Status:", result["status"])
            print("Evidence retrieved:", len(result["evidence"]))
            print("Latency:", result["latency_seconds"], "seconds")
            print("Citation validation:",
                  result["citation_validation"].get("valid", "Unavailable"))

        except Exception as error:
            result = {
                "test_id": test_id,
                "category": test["category"],
                "question": question,
                "answerable": test["answerable"],
                "answer": "",
                "evidence": [],
                "citation_validation": {},
                "latency_seconds": None,
                "api_latency": None,
                "cache_hit": False,
                "status": "failed",
                "error": str(error)
            }

            print("ERROR:", error)

        results.append(result)

        # Save after every test so completed results aren't lost.
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=4, ensure_ascii=False)

    successful = sum(
        1 for item in results
        if item["status"] == "success"
    )

    print("\n" + "=" * 70)
    print("EVALUATION COMPLETED")
    print("=" * 70)
    print("Total test cases:", len(results))
    print("Successful:", successful)
    print("Failed:", len(results) - successful)
    print("Results saved to:", OUTPUT_FILE)


if __name__ == "__main__":
    run_evaluation()
