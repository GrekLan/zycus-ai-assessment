#!/usr/bin/env python
# run_eval.py
"""Standalone evaluation runner.
Usage: python run_eval.py [--output eval_report.md] [--threshold 0.75] [--verbose]"""

import argparse
import os
import sys
from dotenv import load_dotenv
import google.generativeai as genai


def main():
    parser = argparse.ArgumentParser(description="Run evaluation harness for Zycus AI Assessment")
    parser.add_argument("--output", default="eval_report.md", help="Output path for evaluation report")
    parser.add_argument("--threshold", type=float, default=0.75, help="Minimum pass rate threshold")
    parser.add_argument("--verbose", action="store_true", help="Print detailed results")
    args = parser.parse_args()

    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not set. Copy .env.example to .env and add your key.")
        sys.exit(1)

    genai.configure(api_key=api_key)

    # Build KB index
    from src.kb_index import build_index
    build_index(api_key)

    # Run evaluation
    from src.evaluation import run_evaluation, generate_report
    results = run_evaluation()
    report = generate_report(results, args.output)

    # Check threshold
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    pass_rate = passed / max(total, 1)

    print(f"\n{'='*60}")
    print(f"FINAL: {passed}/{total} tests passed ({pass_rate*100:.1f}%)")
    print(f"Threshold: {args.threshold*100:.0f}%")
    print(f"{'='*60}")

    if pass_rate < args.threshold:
        print(f"FAIL: Pass rate {pass_rate*100:.1f}% below threshold {args.threshold*100:.0f}%")
        sys.exit(1)
    else:
        print(f"PASS: All criteria met.")
        sys.exit(0)


if __name__ == "__main__":
    main()
