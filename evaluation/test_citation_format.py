
from src.rag_pipeline import validate_citations

chunks = [
    {
        "source_title": "Password Storage Cheat Sheet",
        "issuer": "OWASP",
        "page": 2
    }
]

test_cases = [
    ("Correct format", "[Evidence 1, p. 2]", True),
    ("Missing comma space", "[Evidence 1,p. 2]", False),
    ("Missing page space", "[Evidence 1, p.2]", False),
    ("Missing Evidence space", "[Evidence1, p. 2]", False),
    ("Multiple spaces", "[Evidence  1, p. 2]", False),
]

print("\nSTRICT CITATION FORMAT TEST")
print("=" * 60)

passed = 0

for name, citation, expected in test_cases:
    answer = f"""
Answer:
This is a test claim {citation}.

Sources:
- Password Storage Cheat Sheet | OWASP | Page 2
"""

    result = validate_citations(answer, chunks)
    actual = result["valid"]

    success = actual == expected
    passed += success

    print(f"\n{name}")
    print("Citation:", citation)
    print("Expected valid:", expected)
    print("Actual valid:", actual)
    print("Result:", "PASS" if success else "FAIL")

    if result["errors"]:
        print("Errors:", result["errors"])

print("\n" + "=" * 60)
print(f"Passed: {passed}/{len(test_cases)}")
