"""Print entropy for your own sample tokens so you can pick a threshold.

Usage (from the project root, venv active):
    python -m scripts.entropy_report
"""

from backend.detection.entropy_detector import shannon_entropy


def load(path: str) -> list[str]:
    with open(path, encoding="utf-8") as f:
        return [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]


def main() -> None:
    secrets = load("tests/eval/entropy_secrets.txt")
    benign = load("tests/eval/entropy_benign.txt")

    for label, items in (("SECRETS", secrets), ("BENIGN", benign)):
        print(f"\n== {label} ==")
        for s in sorted(items, key=shannon_entropy):
            print(f"{shannon_entropy(s):5.2f}  len={len(s):3d}  {s[:60]}")

    lowest_secret = min(shannon_entropy(s) for s in secrets)
    highest_benign = max(shannon_entropy(s) for s in benign)
    print(
        f"\nlowest secret = {lowest_secret:.2f}, highest benign = {highest_benign:.2f}"
    )
    if lowest_secret > highest_benign:
        print(
            f"Cleanly separable. Try threshold ~ {(lowest_secret + highest_benign) / 2:.2f}"
        )
    else:
        print(
            "Classes overlap: pick a threshold by your tolerance for false positives vs misses,"
        )
        print("or raise min_length. Entropy is a Tier 1 hint, not proof.")


if __name__ == "__main__":
    main()
