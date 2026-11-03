import json
from pathlib import Path

from src.rag_pipeline import validate_citations

RESULTS_FILE = Path("evaluation/end_to_end_retest_results.json")

results = json.loads(
    RESULTS_FILE.read_text(encoding="utf-8")
)

print("\nUPDATED CITATION VALIDATION")
print("=" * 65)

passed = 0

for result in results:
    chunks = [
        {
            "source_title": item["title"],
            "issuer": item["issuer"],
            "page": item["page"]
        }
        for item in result.get("evidence", [])
    ]

    validation = validate_citations(
        result.get("answer", ""),
        chunks
    )

    result["citation_validation"] = validation

    if validation["valid"]:
        passed += 1

    print(f"\n{result['test_id']}: {result['category']}")
    print("Valid:", validation["valid"])
    print("Citation count:", validation["citation_count"])
    print("Errors:", validation["errors"])

print("\n" + "=" * 65)
print(f"Passed: {passed}/{len(results)}")

RESULTS_FILE.write_text(
    json.dumps(results, indent=2, ensure_ascii=False),
    encoding="utf-8"
)

print("\nUpdated saved results.")