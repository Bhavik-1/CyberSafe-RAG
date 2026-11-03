import json
import pickle
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parents[1]

TEST_FILE = PROJECT_ROOT / "evaluation" / "end_to_end_test_cases.json"
METADATA_FILE = PROJECT_ROOT / "vector_store" / "fixed_metadata.pkl"

# Alternative expressions for the same concepts.
TOPIC_ALIASES = {
    "urgency": [
        "urgency",
        "urgent",
        "immediate action"
    ],
    "suspicious sender": [
        "sender",
        "email address",
        "sender's address",
        "sender domain"
    ],
    "suspicious links": [
        "suspicious link",
        "malicious link",
        "unknown link",
        "shortened url",
        "suspicious url"
    ],
    "attachments": [
        "attachment",
        "attached file",
        "email attachment"
    ],
    "reporting": [
        "report",
        "reporting",
        "law enforcement"
    ],
    "additional security layer": [
        "extra layer of security",
        "additional layer of security",
        "extra layer"
    ],
    "authentication factors": [
        "authentication factor",
        "something you know",
        "something you have",
        "something you are"
    ],
    "account security": [
        "account security",
        "secure your account",
        "protect your account"
    ],
    "password hashing": [
        "hashing",
        "hashed passwords",
        "password hash"
    ],
    "salting": [
        "salt",
        "salting",
        "unique salt"
    ],
    "secure password storage": [
        "password storage",
        "secure storage",
        "stored securely"
    ],
    "incident triage": [
        "incident triage",
        "triage"
    ],
    "prioritization": [
        "prioritization",
        "prioritize",
        "priority"
    ],
    "incident tracking": [
        "track the status of the incident",
        "incident status",
        "tracking incident"
    ],
    "communication": [
        "communication",
        "communicate",
        "notification",
        "reporting"
    ],
    "recovery decisions": [
        "initiate recovery",
        "recovery decisions",
        "decision to initiate recovery"
    ],
    "slow device performance": [
        "sudden drop in performance",
        "device performance",
        "slow performance"
    ],
    "unexpected pop-ups": [
        "pop-up",
        "pop up",
        "advertisements",
        "frequent ads"
    ],
    "unauthorized messages": [
        "messages sent without permission",
        "emails sent without permission",
        "unauthorized emails",
        "unauthorized messages"
    ],
    "browser redirects": [
        "browser redirects",
        "redirected to unknown pages",
        "suspicious pages",
        "unknown pages"
    ],
    "account compromise": [
        "compromised account",
        "account compromise",
        "unauthorized access"
    ],
    "account recovery": [
        "account recovery",
        "recover your account",
        "recovery"
    ],
    "authentication security": [
        "multi-factor authentication",
        "multifactor authentication",
        "authentication",
        "mfa"
    ]
}


with open(TEST_FILE, "r", encoding="utf-8") as f:
    test_cases = json.load(f)

with open(METADATA_FILE, "rb") as f:
    metadata = pickle.load(f)

source_chunks = defaultdict(list)

for chunk in metadata:
    source_id = chunk.get("source_id")

    if source_id:
        source_chunks[source_id].append(chunk)


print("\n" + "=" * 75)
print("CYBERSAFE RAG - SEMANTIC ALIAS COVERAGE CHECK")
print("=" * 75)

for test in test_cases:

    print(f"\n{test['test_id']} - {test['category']}")
    print(f"Question: {test['question']}")

    if not test["answerable"]:
        print("Expected answerability: NO")
        continue

    expected_sources = test["expected_source_ids"]

    combined_text = " ".join(
        str(chunk.get("text", "")).lower()
        for source_id in expected_sources
        for chunk in source_chunks.get(source_id, [])
    )

    print("\nSource availability:")

    for source_id in expected_sources:
        print(
            f"  {source_id}: "
            f"{len(source_chunks.get(source_id, []))} chunks"
        )

    print("\nTopic coverage:")

    found_count = 0

    for topic in test["expected_topics"]:

        aliases = TOPIC_ALIASES.get(topic, [topic])

        matched = [
            alias for alias in aliases
            if alias.lower() in combined_text
        ]

        if matched:
            found_count += 1
            print(f"  FOUND: {topic} -> {matched[0]}")
        else:
            print(f"  NOT FOUND: {topic}")

    total = len(test["expected_topics"])

    coverage = (
        found_count / total * 100
        if total else 0
    )

    print(f"\nPreliminary topic coverage: {coverage:.1f}%")


print("\n" + "=" * 75)
print("COVERAGE CHECK COMPLETED")
print("=" * 75)