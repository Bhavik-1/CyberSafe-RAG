from src.rag_pipeline import (
    rebuild_sources_section,
    validate_citations
)

chunks = [
    {
        "source_title": "Authentication Cheat Sheet",
        "issuer": "OWASP",
        "page": 21
    },
    {
        "source_title": "Multifactor Authentication Cheat Sheet",
        "issuer": "OWASP",
        "page": 5
    }
]

# Test 1: Correct citations and duplicate citation
answer_1 = """
Answer:
Use MFA to protect accounts [Evidence 1, p. 21].
It adds another layer of security [Evidence 2, p. 5].
MFA is recommended for account security [Evidence 2, p. 5].

Sources:
- Wrong Source | Unknown | Page 99
"""

result_1 = rebuild_sources_section(answer_1, chunks)
validation_1 = validate_citations(result_1, chunks)

print("\nTEST 1: Correct citations")
print(result_1)
print("Validation:", validation_1)


# Test 2: Incorrect page must not be silently corrected
answer_2 = """
Answer:
Use MFA to protect accounts [Evidence 1, p. 99].

Sources:
- Authentication Cheat Sheet | OWASP | Page 21
"""

result_2 = rebuild_sources_section(answer_2, chunks)
validation_2 = validate_citations(result_2, chunks)

print("\nTEST 2: Incorrect page")
print(result_2)
print("Validation:", validation_2)


# Test 3: No citations
answer_3 = """
Answer:
MFA can improve account security.

Sources:
- Wrong Source | Unknown | Page 99
"""

result_3 = rebuild_sources_section(answer_3, chunks)
validation_3 = validate_citations(result_3, chunks)

print("\nTEST 3: Missing citations")
print(result_3)
print("Validation:", validation_3)