
import os
import sys
import json
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai


# ============================================================
# 1. PATHS AND IMPORTS
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(ROOT / "src"))

load_dotenv(ROOT / ".env", override=True)

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("GEMINI_API_KEY is missing from .env")

from rag_pipeline import verify_claim_support

client = genai.Client(api_key=API_KEY)

OUTPUT_DIR = ROOT / "evaluation"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "claim_verifier_evaluation.json"


# ============================================================
# 2. MANUALLY LABELLED TEST CASES
# ============================================================

TEST_CASES = [

    # --------------------------------------------------------
    # GROUP 1: SUPPORTED CLAIMS
    # --------------------------------------------------------

    {
        "id": "TEST-01",
        "description": "Direct MFA support",
        "expected": "SUPPORTED",
        "answer": (
            "TEST-01: Enable multi-factor authentication "
            "to add another layer of account security "
            "[Evidence 1, p. 10]."
        ),
        "chunks": [{
            "source_title": "Multifactor Authentication Cheat Sheet",
            "issuer": "OWASP",
            "page": 10,
            "text": (
                "Enable Multi Factor Authentication (MFA) "
                "to add an extra layer of security to your accounts."
            )
        }]
    },

    {
        "id": "TEST-02",
        "description": "Direct phishing support",
        "expected": "SUPPORTED",
        "answer": (
            "TEST-02: Do not trust promotional offers "
            "that look too good to be true [Evidence 1, p. 4]."
        ),
        "chunks": [{
            "source_title": "CERT-In Cyber Security Handbook",
            "issuer": "CERT-In",
            "page": 4,
            "text": (
                "Do not trust promotional offers which look "
                "too good to be true."
            )
        }]
    },

    {
        "id": "TEST-03",
        "description": "Direct malware symptom support",
        "expected": "SUPPORTED",
        "answer": (
            "TEST-03: A sudden drop in device performance "
            "can be a sign of malware [Evidence 1, p. 7]."
        ),
        "chunks": [{
            "source_title": "Cyber Security Awareness Booklet",
            "issuer": "CERT-In",
            "page": 7,
            "text": (
                "A sudden drop in the performance of your device "
                "can be a sign of malware infection."
            )
        }]
    },

    {
        "id": "TEST-04",
        "description": "Direct incident response support",
        "expected": "SUPPORTED",
        "answer": (
            "TEST-04: Incident response includes tracking incident "
            "status and documenting indicators of compromise "
            "[Evidence 1, p. 35]."
        ),
        "chunks": [{
            "source_title": "NIST SP 800-61 Revision 3",
            "issuer": "NIST",
            "page": 35,
            "text": (
                "Track the status of the incident, including a "
                "summary, indicators of compromise, time frames, "
                "and next steps."
            )
        }]
    },

    {
        "id": "TEST-05",
        "description": "Direct account security support",
        "expected": "SUPPORTED",
        "answer": (
            "TEST-05: MFA provides an additional layer of security "
            "for accounts [Evidence 1, p. 10]."
        ),
        "chunks": [{
            "source_title": "Multifactor Authentication Cheat Sheet",
            "issuer": "OWASP",
            "page": 10,
            "text": (
                "Enable Multi Factor Authentication (MFA) "
                "to add an extra layer of security to your accounts."
            )
        }]
    },


    # --------------------------------------------------------
    # GROUP 2: PARTIALLY SUPPORTED CLAIMS
    # --------------------------------------------------------

    {
        "id": "TEST-06",
        "description": "MFA guarantee exaggeration",
        "expected": "PARTIALLY_SUPPORTED",
        "answer": (
            "TEST-06: MFA adds another security layer and "
            "guarantees that accounts cannot be compromised "
            "[Evidence 1, p. 10]."
        ),
        "chunks": [{
            "source_title": "Multifactor Authentication Cheat Sheet",
            "issuer": "OWASP",
            "page": 10,
            "text": (
                "Enable Multi Factor Authentication (MFA) "
                "to add an extra layer of security to your accounts."
            )
        }]
    },

    {
        "id": "TEST-07",
        "description": "Partially supported phishing indicators",
        "expected": "PARTIALLY_SUPPORTED",
        "answer": (
            "TEST-07: Urgency and poor grammar are indicators "
            "of suspicious messages [Evidence 1, p. 4]."
        ),
        "chunks": [{
            "source_title": "CERT-In Cyber Security Handbook",
            "issuer": "CERT-In",
            "page": 4,
            "text": (
                "Never react to messages which show urgency. "
                "Do not trust promotional offers which look "
                "too good to be true."
            )
        }]
    },

    {
        "id": "TEST-08",
        "description": "Incident response scope exaggeration",
        "expected": "PARTIALLY_SUPPORTED",
        "answer": (
            "TEST-08: Incident response involves tracking incident "
            "status and always requires public notification "
            "[Evidence 1, p. 35]."
        ),
        "chunks": [{
            "source_title": "NIST SP 800-61 Revision 3",
            "issuer": "NIST",
            "page": 35,
            "text": (
                "Track the status of the incident, including a "
                "summary, indicators of compromise, time frames, "
                "and next steps."
            )
        }]
    },

    {
        "id": "TEST-09",
        "description": "Password storage overgeneralization",
        "expected": "PARTIALLY_SUPPORTED",
        "answer": (
            "TEST-09: Passwords should generally be stored using "
            "secure hashing, and encryption must never be used "
            "in any circumstance [Evidence 1, p. 1]."
        ),
        "chunks": [{
            "source_title": "Password Storage Cheat Sheet",
            "issuer": "OWASP",
            "page": 1,
            "text": (
                "Passwords should be hashed rather than encrypted "
                "in almost all circumstances."
            )
        }]
    },

    {
        "id": "TEST-10",
        "description": "Recovery process overgeneralization",
        "expected": "PARTIALLY_SUPPORTED",
        "answer": (
            "TEST-10: Incident response includes recovery decisions, "
            "and every incident must immediately trigger full "
            "system restoration [Evidence 1, p. 34]."
        ),
        "chunks": [{
            "source_title": "NIST SP 800-61 Revision 3",
            "issuer": "NIST",
            "page": 34,
            "text": (
                "Incident triage includes prioritization, escalation, "
                "and decisions about initiating recovery based "
                "on risk factors."
            )
        }]
    },


    # --------------------------------------------------------
    # GROUP 3: UNSUPPORTED CLAIMS
    # --------------------------------------------------------

    {
        "id": "TEST-11",
        "description": "Unrelated evidence",
        "expected": "UNSUPPORTED",
        "answer": (
            "TEST-11: Phishing emails always contain "
            "grammatical errors [Evidence 1, p. 10]."
        ),
        "chunks": [{
            "source_title": "Multifactor Authentication Cheat Sheet",
            "issuer": "OWASP",
            "page": 10,
            "text": (
                "Enable Multi Factor Authentication (MFA) "
                "to add an extra layer of security to your accounts."
            )
        }]
    },

    {
        "id": "TEST-12",
        "description": "Unsupported malware claim",
        "expected": "UNSUPPORTED",
        "answer": (
            "TEST-12: Malware always causes a device battery "
            "to explode [Evidence 1, p. 7]."
        ),
        "chunks": [{
            "source_title": "Cyber Security Awareness Booklet",
            "issuer": "CERT-In",
            "page": 7,
            "text": (
                "A sudden drop in the performance of your device "
                "can be a sign of malware infection."
            )
        }]
    },

    {
        "id": "TEST-13",
        "description": "Unsupported MFA claim",
        "expected": "UNSUPPORTED",
        "answer": (
            "TEST-13: MFA eliminates the need for passwords "
            "completely [Evidence 1, p. 10]."
        ),
        "chunks": [{
            "source_title": "Multifactor Authentication Cheat Sheet",
            "issuer": "OWASP",
            "page": 10,
            "text": (
                "Enable Multi Factor Authentication (MFA) "
                "to add an extra layer of security to your accounts."
            )
        }]
    },

    {
        "id": "TEST-14",
        "description": "Unsupported incident response claim",
        "expected": "UNSUPPORTED",
        "answer": (
            "TEST-14: NIST requires every cyber incident "
            "to be resolved within one hour [Evidence 1, p. 35]."
        ),
        "chunks": [{
            "source_title": "NIST SP 800-61 Revision 3",
            "issuer": "NIST",
            "page": 35,
            "text": (
                "Track the status of the incident, including a "
                "summary, indicators of compromise, time frames, "
                "and next steps."
            )
        }]
    },

    {
        "id": "TEST-15",
        "description": "Unsupported password claim",
        "expected": "UNSUPPORTED",
        "answer": (
            "TEST-15: Storing passwords as plain text is "
            "the recommended secure practice [Evidence 1, p. 1]."
        ),
        "chunks": [{
            "source_title": "Password Storage Cheat Sheet",
            "issuer": "OWASP",
            "page": 1,
            "text": (
                "Passwords should be hashed rather than encrypted "
                "in almost all circumstances."
            )
        }]
    },


    # --------------------------------------------------------
    # GROUP 4: MISSING CITATIONS
    # --------------------------------------------------------

    {
        "id": "TEST-16",
        "description": "MFA claim without citation",
        "expected": "MISSING_CITATION",
        "answer": "TEST-16: MFA adds another layer of account security.",
        "chunks": [{
            "source_title": "Multifactor Authentication Cheat Sheet",
            "issuer": "OWASP",
            "page": 10,
            "text": (
                "Enable Multi Factor Authentication (MFA) "
                "to add an extra layer of security to your accounts."
            )
        }]
    },

    {
        "id": "TEST-17",
        "description": "Phishing claim without citation",
        "expected": "MISSING_CITATION",
        "answer": (
            "TEST-17: Users should be cautious of messages "
            "that create urgency."
        ),
        "chunks": [{
            "source_title": "CERT-In Cyber Security Handbook",
            "issuer": "CERT-In",
            "page": 4,
            "text": "Never react to messages which show urgency."
        }]
    },

    {
        "id": "TEST-18",
        "description": "Malware claim without citation",
        "expected": "MISSING_CITATION",
        "answer": (
            "TEST-18: Unexpected pop-ups can be a sign of malware."
        ),
        "chunks": [{
            "source_title": "Cyber Security Awareness Booklet",
            "issuer": "CERT-In",
            "page": 7,
            "text": (
                "Frequent advertisements and pop-ups can be signs "
                "of malware infection."
            )
        }]
    },

    {
        "id": "TEST-19",
        "description": "Password claim without citation",
        "expected": "MISSING_CITATION",
        "answer": (
            "TEST-19: Passwords should be securely hashed before storage."
        ),
        "chunks": [{
            "source_title": "Password Storage Cheat Sheet",
            "issuer": "OWASP",
            "page": 1,
            "text": (
                "Passwords should be hashed rather than encrypted "
                "in almost all circumstances."
            )
        }]
    },

    {
        "id": "TEST-20",
        "description": "Incident response claim without citation",
        "expected": "MISSING_CITATION",
        "answer": (
            "TEST-20: Incident response includes documenting "
            "indicators of compromise."
        ),
        "chunks": [{
            "source_title": "NIST SP 800-61 Revision 3",
            "issuer": "NIST",
            "page": 35,
            "text": (
                "Track the status of the incident, including a "
                "summary, indicators of compromise, time frames, "
                "and next steps."
            )
        }]
    },


    # --------------------------------------------------------
    # GROUP 5: CONTRADICTORY CLAIMS
    # --------------------------------------------------------

    {
        "id": "TEST-21",
        "description": "Contradiction about promotional offers",
        "expected": "UNSUPPORTED",
        "answer": (
            "TEST-21: Users should trust promotional offers "
            "that look too good to be true [Evidence 1, p. 4]."
        ),
        "chunks": [{
            "source_title": "CERT-In Cyber Security Handbook",
            "issuer": "CERT-In",
            "page": 4,
            "text": (
                "Do not trust promotional offers which look "
                "too good to be true."
            )
        }]
    },

    {
        "id": "TEST-22",
        "description": "Contradiction about MFA security",
        "expected": "UNSUPPORTED",
        "answer": (
            "TEST-22: OWASP recommends disabling MFA to improve "
            "account security [Evidence 1, p. 10]."
        ),
        "chunks": [{
            "source_title": "Multifactor Authentication Cheat Sheet",
            "issuer": "OWASP",
            "page": 10,
            "text": (
                "Enable Multi Factor Authentication (MFA) "
                "to add an extra layer of security to your accounts."
            )
        }]
    },

    {
        "id": "TEST-23",
        "description": "Contradiction about password storage",
        "expected": "UNSUPPORTED",
        "answer": (
            "TEST-23: OWASP recommends storing passwords in plain "
            "text rather than hashing them [Evidence 1, p. 1]."
        ),
        "chunks": [{
            "source_title": "Password Storage Cheat Sheet",
            "issuer": "OWASP",
            "page": 1,
            "text": (
                "Passwords should be hashed rather than encrypted "
                "in almost all circumstances."
            )
        }]
    },

    {
        "id": "TEST-24",
        "description": "Contradiction about urgency",
        "expected": "UNSUPPORTED",
        "answer": (
            "TEST-24: CERT-In recommends reacting immediately "
            "to messages that show urgency [Evidence 1, p. 4]."
        ),
        "chunks": [{
            "source_title": "CERT-In Cyber Security Handbook",
            "issuer": "CERT-In",
            "page": 4,
            "text": "Never react to messages which show urgency."
        }]
    },

    {
        "id": "TEST-25",
        "description": "Contradiction about MFA protection",
        "expected": "UNSUPPORTED",
        "answer": (
            "TEST-25: OWASP states that MFA reduces account "
            "security [Evidence 1, p. 10]."
        ),
        "chunks": [{
            "source_title": "Multifactor Authentication Cheat Sheet",
            "issuer": "OWASP",
            "page": 10,
            "text": (
                "Enable Multi Factor Authentication (MFA) "
                "to add an extra layer of security to your accounts."
            )
        }]
    }
]


# ============================================================
# 3. RESULT EXTRACTION
# ============================================================

def normalize_status(value):

    value = str(value or "").strip().upper()

    allowed = {
        "SUPPORTED",
        "PARTIALLY_SUPPORTED",
        "UNSUPPORTED",
        "MISSING_CITATION"
    }

    if value in allowed:
        return value

    return "UNKNOWN"


def find_test_claim(result, test_id):

    claims = result.get("claims", [])

    # Find all claims originating from the original
    # sentence containing this test ID.
    matching_claims = [
        claim
        for claim in claims
        if test_id in str(
            claim.get("original_sentence", "")
        )
    ]

    # Fallback for older verifier outputs.
    if not matching_claims:
        matching_claims = [
            claim
            for claim in claims
            if test_id in str(
                claim.get("claim", claim.get("text", ""))
            )
        ]

    if not matching_claims:
        if len(claims) == 1:
            return claims[0]

        return None

    statuses = [
        normalize_status(claim.get("status"))
        for claim in matching_claims
    ]

    # Aggregate claim classifications into the
    # classification of the original sentence.

    if all(status == "MISSING_CITATION" for status in statuses):
        final_status = "MISSING_CITATION"

    elif "MISSING_CITATION" in statuses:
        final_status = "PARTIALLY_SUPPORTED"

    elif "PARTIALLY_SUPPORTED" in statuses:
        final_status = "PARTIALLY_SUPPORTED"

    elif (
        "SUPPORTED" in statuses
        and "UNSUPPORTED" in statuses
    ):
        final_status = "PARTIALLY_SUPPORTED"

    elif all(status == "SUPPORTED" for status in statuses):
        final_status = "SUPPORTED"

    elif all(status == "UNSUPPORTED" for status in statuses):
        final_status = "UNSUPPORTED"

    else:
        final_status = "UNKNOWN"

    return {
        "claim": " | ".join(
            str(claim.get("claim", ""))
            for claim in matching_claims
        ),
        "status": final_status,
        "subclaims": matching_claims,
        "aggregation_method": "sentence_level_claim_aggregation"
    }



# ============================================================
# 4. EVALUATION
# ============================================================

def main():

    results = []

    print("\n" + "=" * 70)
    print("CYBERSAFE RAG - CLAIM VERIFIER EVALUATION")
    print("=" * 70)

    print("Total test cases:", len(TEST_CASES))

    for number, test in enumerate(TEST_CASES, start=1):

        print(
            f"\nRunning {number}/{len(TEST_CASES)}: "
            f"{test['id']} - {test['description']}"
        )

        start = time.perf_counter()

        try:

            verifier_result = verify_claim_support(
                answer=test["answer"],
                chunks=test["chunks"],
                client=client
            )

            latency = round(
                time.perf_counter() - start,
                2
            )

            if verifier_result.get("status") == "failed":

                predicted = "ERROR"
                claim_data = None

            else:

                claim_data = find_test_claim(
                    verifier_result,
                    test["id"]
                )

                if claim_data is None:
                    predicted = "NO_CLAIM_RETURNED"

                else:
                    predicted = normalize_status(
                        claim_data.get("status")
                    )

            expected = test["expected"]

            passed = predicted == expected

            result = {
                "test_id": test["id"],
                "description": test["description"],
                "expected": expected,
                "predicted": predicted,
                "passed": passed,
                "latency_seconds": latency,
                "claim_result": claim_data,
                "verifier_response": verifier_result
            }

            results.append(result)

            print("Expected:", expected)
            print("Predicted:", predicted)
            print("Result:", "PASS" if passed else "FAIL")
            print("Latency:", latency, "seconds")

        except Exception as error:

            print("ERROR:", str(error))

            results.append({
                "test_id": test["id"],
                "description": test["description"],
                "expected": test["expected"],
                "predicted": "ERROR",
                "passed": False,
                "error": str(error)
            })

    # ========================================================
    # 5. CALCULATE METRICS
    # ========================================================

    total = len(results)

    passed = sum(
        item["passed"] for item in results
    )

    failed = total - passed

    accuracy = passed / total if total else 0

    labels = [
        "SUPPORTED",
        "PARTIALLY_SUPPORTED",
        "UNSUPPORTED",
        "MISSING_CITATION"
    ]

    confusion_matrix = {
        actual: {
            predicted: 0 for predicted in labels
        }
        for actual in labels
    }

    for item in results:

        actual = item["expected"]
        predicted = item["predicted"]

        if actual in confusion_matrix:

            if predicted in confusion_matrix[actual]:
                confusion_matrix[actual][predicted] += 1

    # Calculate per-category accuracy.
    category_metrics = {}

    for label in labels:

        category_results = [
            item for item in results
            if item["expected"] == label
        ]

        category_total = len(category_results)

        category_passed = sum(
            item["passed"] for item in category_results
        )

        category_metrics[label] = {
            "total": category_total,
            "passed": category_passed,
            "failed": category_total - category_passed,
            "accuracy": round(
                category_passed / category_total, 4
            ) if category_total else 0
        }

    # Calculate latency.
    latencies = [
        item["latency_seconds"]
        for item in results
        if "latency_seconds" in item
    ]

    average_latency = (
        round(sum(latencies) / len(latencies), 2)
        if latencies else 0
    )

    # ========================================================
    # 6. CREATE FINAL JSON OUTPUT
    # ========================================================

    summary = {
        "total_tests": total,
        "passed": passed,
        "failed": failed,
        "accuracy": round(accuracy, 4),
        "average_latency_seconds": average_latency,
        "category_metrics": category_metrics,
        "confusion_matrix": confusion_matrix
    }

    output = {
        "summary": summary,
        "results": results
    }

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            output,
            file,
            indent=4,
            ensure_ascii=False
        )

    # ========================================================
    # 7. FINAL REPORT
    # ========================================================

    print("\n" + "=" * 70)
    print("FINAL EVALUATION")
    print("=" * 70)

    print("Total tests:", total)
    print("Passed:", passed)
    print("Failed:", failed)

    print(
        "Accuracy:",
        round(accuracy * 100, 2),
        "%"
    )

    print(
        "Average latency:",
        average_latency,
        "seconds"
    )

    print("\nCategory-wise results:")

    for label, metrics in category_metrics.items():

        print(
            f"{label}: "
            f"{metrics['passed']}/{metrics['total']} "
            f"({metrics['accuracy'] * 100:.2f}%)"
        )

    print("\nConfusion Matrix:")

    print(
        json.dumps(
            confusion_matrix,
            indent=4
        )
    )

    print("\nDetailed results saved to:")
    print(OUTPUT_FILE)

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
