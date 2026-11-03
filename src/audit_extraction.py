
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
EXTRACTED_DIR = ROOT / "data" / "processed" / "extracted"

total_pages = 0
total_chars = 0

print("=" * 65)
print("CYBERSAFE - EXTRACTION QUALITY AUDIT")
print("=" * 65)

for file_path in sorted(EXTRACTED_DIR.glob("*.jsonl")):

    records = []

    with file_path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                print(f"[INVALID JSON] {file_path.name}: line {line_number}")

    if not records:
        print(f"[EMPTY] {file_path.name}")
        continue

    empty_text = sum(
        1 for r in records if not r.get("text", "").strip()
    )

    characters = sum(
        len(r.get("text", "")) for r in records
    )

    total_pages += len(records)
    total_chars += characters

    pages = [r["page"] for r in records]

    print(f"\nDocument: {file_path.name}")
    print(f"Pages: {len(records)}")
    print(f"Page range: {min(pages)} - {max(pages)}")
    print(f"Characters: {characters}")
    print(f"Empty records: {empty_text}")
    print("Preview:")
    print(records[0]["text"][:250])

    if empty_text:
        print("[WARNING] Empty text found!")

print("\n" + "=" * 65)
print("TOTAL PAGES:", total_pages)
print("TOTAL CHARACTERS:", total_chars)
print("=" * 65)
