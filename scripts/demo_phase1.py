"""Demonstration script for Phase 1 execution of Local Shield DLP."""

from backend.detection.tiers import run_tier0, run_tier1

test_samples = {
    "Valid Visa Card": "Processing payment for card 4111 1111 1111 1111 on file.",
    "Aadhaar Number": "Resident UID verification: 2345 6789 0124.",
    "PAN Card": "Income tax PAN provided is ABCPE1234F.",
    "AWS Access Key": "Deploy key: AKIAIOSFODNN7EXAMPLE.",
    "DB Connection URI": "postgres://admin:s3cretPass@db.internal:5432/production",
    "High-Entropy Secret": "API_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    "Confidential Memo": "NOTICE: This document is CONFIDENTIAL and proprietary.",
    "Email & Phone": "Please reach out to priya@example.com or call +91 98765 43210.",
    "Harmless Text": "Team sync meeting scheduled for 3:00 PM in Conference Room B.",
}


def main():
    print("==========================================================")
    print("   LOCAL SHIELD DLP: PHASE 1 DETERMINISTIC DETECTION")
    print("==========================================================\n")
    for label, sample in test_samples.items():
        t0 = run_tier0(sample)
        t1 = run_tier1(sample)
        print(f"[*] Scenario: {label}")
        print(f"    Text: \"{sample}\"")
        if t0:
            hits = [f"{d.detector} (category={d.category}, conf={d.confidence})" for d in t0]
            print(f"    --> Tier 0 Hit [High Certainty]: {hits}")
        if t1:
            hits = [f"{d.detector} (category={d.category}, conf={d.confidence})" for d in t1]
            print(f"    --> Tier 1 Hit [Heuristic]:      {hits}")
        if not t0 and not t1:
            print("    --> Result: [CLEAN] (No sensitive patterns fired)")
        print()


if __name__ == "__main__":
    main()
