
from pathlib import Path
import json
import re
import unicodedata
import csv

ROOT = Path(__file__).resolve().parents[1]

INPUT_DIR = ROOT / "data" / "processed" / "extracted"
OUTPUT_DIR = ROOT / "data" / "processed" / "cleaned"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def clean_text(text):
    # Normalize Unicode characters
    text = unicodedata.normalize("NFKC", text)

    # Replace invisible formatting characters with spaces
    # This preserves word boundaries in extracted PDF text.
    text = re.sub(
    r"[\u200b-\u200f\u202a-\u202e\u2060\ufeff]",
    " ",
    text
   )

    # Remove soft hyphens
    text = text.replace("\u00ad", "")

    # Join words broken by PDF line wrapping
    text = re.sub(
        r"(?<=\w)-\s*\n\s*(?=\w)",
        "",
        text
    )

    # Normalize spaces
    text = re.sub(r"[ \t]+", " ", text)

    # Remove unnecessary spaces around line breaks
    text = re.sub(r" *\n *", "\n", text)

    # Retain paragraph boundaries
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def process_file(file_path):
    output_path = OUTPUT_DIR / file_path.name

    records_processed = 0
    duplicates = 0
    seen_text = set()

    with file_path.open("r", encoding="utf-8") as source:
        with output_path.open("w", encoding="utf-8") as output:

            for line in source:

                record = json.loads(line)

                original_text = record.get("text", "")
                cleaned = clean_text(original_text)

                if not cleaned:
                    continue

                # Detect exact duplicate page content.
                # Do not delete it automatically.
                duplicate = cleaned in seen_text
                duplicates += int(duplicate)
                seen_text.add(cleaned)

                record["text"] = cleaned
                record["char_count"] = len(cleaned)
                record["is_duplicate_page"] = duplicate

                output.write(
                    json.dumps(record, ensure_ascii=False) + "\n"
                )

                records_processed += 1

    return records_processed, duplicates


def main():
    total_records = 0
    report = []

    for file_path in sorted(INPUT_DIR.glob("*.jsonl")):

        count, duplicates = process_file(file_path)

        total_records += count

        report.append({
            "document": file_path.name,
            "records": count,
            "duplicate_pages": duplicates
        })

        print(
            f"{file_path.name}: "
            f"{count} records, "
            f"{duplicates} duplicate pages"
        )

    report_path = OUTPUT_DIR / "cleaning_report.csv"

    with report_path.open(
        "w", newline="", encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=[
                "document",
                "records",
                "duplicate_pages"
            ]
        )

        writer.writeheader()
        writer.writerows(report)

    print("\n========== CLEANING SUMMARY ==========")
    print("Total records:", total_records)
    print("Cleaned files:", len(report))
    print("Report:", report_path)


if __name__ == "__main__":
    main()
