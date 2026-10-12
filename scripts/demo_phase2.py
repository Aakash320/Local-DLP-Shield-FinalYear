"""Live demonstration of Tier 2 LLM Text Classifier (Phase 2)."""

import time
from backend.detection.llm_detector import classify
from backend.detection.tiers import run_tier0, run_tier1

SAMPLES = [
    (
        "Confidential Strategy",
        "Project Falcon Q3 internal financial forecast: operating revenue expected to grow 45%. Do not share outside executive team.",
    ),
    (
        "Internal Credentials & Tokens",
        "Here is the temporary auth token for production cluster: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.prod_9941",
    ),
    (
        "Employee Salary Data",
        "CONFIDENTIAL HR Records: Priya Sharma - Senior Engineer - Base salary: 28,00,000 INR per annum.",
    ),
    (
        "Benign Conversation",
        "Hey everyone, don't forget the team lunch at 12:30 PM in the cafeteria today!",
    ),
    (
        "Benign Public Code",
        "def quick_sort(arr):\n    if len(arr) <= 1: return arr\n    return quick_sort([x for x in arr[1:] if x < arr[0]]) + [arr[0]] + quick_sort([x for x in arr[1:] if x >= arr[0]])",
    ),
]


def main():
    print("==================================================================")
    print("   LOCAL SHIELD DLP: PHASE 2 LOCAL LLM CLASSIFIER (TIER 2)")
    print("==================================================================\n")
    for title, text in SAMPLES:
        print(f"[*] Scenario: {title}")
        print(f"    Snippet: \"{text[:80]}{'...' if len(text) > 80 else ''}\"")
        
        # Tier 0 & Tier 1 quick scan
        t0 = run_tier0(text)
        t1 = run_tier1(text)
        if t0:
            print(f"    [Tier 0 Hits]: {[d.detector for d in t0]}")
        if t1:
            print(f"    [Tier 1 Hits]: {[d.detector for d in t1]}")
            
        # Tier 2 LLM Classification
        start = time.perf_counter()
        verdict = classify(text)
        latency = time.perf_counter() - start
        
        status = "[BLOCKED / SENSITIVE]" if verdict.is_sensitive else "[ALLOWED / BENIGN]"
        print(f"    [Tier 2 LLM]: {status}")
        print(f"      Category:   {verdict.category}")
        print(f"      Confidence: {verdict.confidence:.2f}")
        print(f"      Reason:     {verdict.reason}")
        print(f"      Latency:    {latency:.2f}s")
        print()


if __name__ == "__main__":
    main()
