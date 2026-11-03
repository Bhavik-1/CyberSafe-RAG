
from pathlib import Path
import pymupdf
import json
import csv
import re

# Project root
ROOT = Path(__file__).resolve().parents[1]

OUTPUT_DIR = ROOT / "data" / "processed" / "extracted"
LOW_TEXT_REPORT = ROOT / "data" / "processed" / "low_text_pages.csv"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Only the eight core PDFs for the first version
DOCUMENTS = [
    {
        "source_id": "CERTIN_2023",
        "path": "data/raw/cert_in/CSA_Booklet.pdf",
        "title": "Cyber Security Awareness Booklet",
        "issuer": "CERT-In",
        "category": "phishing"
    },
    {
        "source_id": "CERTIN_2024",
        "path": "data/raw/cert_in/CERT-In-NCSAM-Book_20241001.pdf",
        "title": "Cyber Security Handbook",
        "issuer": "CERT-In",
        "category": "cyber_hygiene"
    },
    {
        "source_id": "CERTIN_2025",
        "path": "data/raw/cert_in/CSH_Booklet25.pdf",
        "title": "Digital Safety Compass Handbook",
        "issuer": "CERT-In",
        "category": "online_scams"
    },
    {
        "source_id": "NIST_800_61R3",
        "path": "data/raw/nist/NIST.SP.800-61r3.pdf",
        "title": "Incident Response Recommendations",
        "issuer": "NIST",
        "category": "incident_response"
    },
    {
        "source_id": "OWASP_AUTH",
        "path": "data/raw/owasp/authentication.pdf",
        "title": "Authentication Cheat Sheet",
        "issuer": "OWASP",
        "category": "authentication"
    },
    {
        "source_id": "OWASP_MFA",
        "path": "data/raw/owasp/mfa.pdf",
        "title": "Multifactor Authentication Cheat Sheet",
        "issuer": "OWASP",
        "category": "mfa"
    },
    {
        "source_id": "OWASP_PASSWORD",
        "path": "data/raw/owasp/password_storage.pdf",
        "title": "Password Storage Cheat Sheet",
        "issuer": "OWASP",
        "category": "password_security"
    },
    {
        "source_id": "OWASP_SESSION",
        "path": "data/raw/owasp/session_management.pdf",
        "title": "Session Management Cheat Sheet",
        "issuer": "OWASP",
        "category": "session_security"
    }
]


def clean_whitespace(text):
    """Normalize whitespace without removing meaningful content."""
    text = text.replace("\x00", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_document(document):
    pdf_path = ROOT / document["path"]

    if not pdf_path.exists():
        print(f"[MISSING] {pdf_path}")
        return [], []

    records = []
    low_text_pages = []

    try:
        pdf = pymupdf.open(pdf_path)

        for page_number, page in enumerate(pdf, start=1):
            raw_text = page.get_text("text")
            text = clean_whitespace(raw_text)

            # Flag pages with little or no extractable text.
            # These may be scanned, decorative or blank pages.
            character_count = len(re.sub(r"\s", "", text))

            if character_count < 40:
                low_text_pages.append({
                    "source_id": document["source_id"],
                    "file": str(pdf_path.relative_to(ROOT)),
                    "page": page_number,
                    "characters": character_count
                })
                continue

            records.append({
                "source_id": document["source_id"],
                "source_title": document["title"],
                "issuer": document["issuer"],
                "category": document["category"],
                "page": page_number,
                "text": text
            })

        pdf.close()

        output_path = OUTPUT_DIR / f"{document['source_id']}.jsonl"

        with output_path.open("w", encoding="utf-8") as file:
            for record in records:
                file.write(
                    json.dumps(record, ensure_ascii=False) + "\n"
                )

        print(f"\nProcessed: {document['title']}")
        print(f"Pages extracted: {len(records)}")
        print(f"Low-text pages: {len(low_text_pages)}")
        print(f"Output: {output_path}")

    except Exception as error:
        print(f"[ERROR] {document['source_id']}: {error}")

    return records, low_text_pages


def main():
    all_low_text_pages = []
    total_extracted = 0

    for document in DOCUMENTS:
        records, low_text = extract_document(document)

        total_extracted += len(records)
        all_low_text_pages.extend(low_text)

    with LOW_TEXT_REPORT.open(
        "w", newline="", encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "source_id", "file", "page", "characters"
            ]
        )
        writer.writeheader()
        writer.writerows(all_low_text_pages)

    print("\n========== EXTRACTION SUMMARY ==========")
    print(f"Documents processed: {len(DOCUMENTS)}")
    print(f"Total extracted pages: {total_extracted}")
    print(f"Pages requiring manual review: {len(all_low_text_pages)}")
    print(f"Low-text report: {LOW_TEXT_REPORT}")


if __name__ == "__main__":
    main()
