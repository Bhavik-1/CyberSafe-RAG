import pickle
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
METADATA_FILE = PROJECT_ROOT / "vector_store" / "fixed_metadata.pkl"

with open(METADATA_FILE, "rb") as f:
    metadata = pickle.load(f)

terms = [
    "incident response",
    "incident tracking",
    "track the status",
    "prioritization",
    "initiate recovery",
    "recovery activities",
    "communication",
    "reporting",
    "lessons learned"
]

matches = []

for chunk in metadata:
    if chunk.get("source_id") != "NIST_800_61R3":
        continue

    text = str(chunk.get("text", ""))
    lower_text = text.lower()

    matched_terms = [
        term for term in terms
        if term in lower_text
    ]

    if matched_terms:
        matches.append((chunk, matched_terms))

print(f"Relevant NIST chunks found: {len(matches)}")

for chunk, matched_terms in matches:
    print("\n" + "=" * 80)
    print("Chunk ID:", chunk.get("chunk_id"))
    print("Page:", chunk.get("page", chunk.get("page_number")))
    print("Matched terms:", ", ".join(matched_terms))
    print("-" * 80)
    print(chunk.get("text", ""))

print("\nNIST EVIDENCE INSPECTION COMPLETED")