
import time
from pathlib import Path

import pandas as pd

from pipeline import (
    CSV_PATH,
    extract_state,
    find_columns,
    normalize,
    to_text,
)
from llm_extractor import extract_clause


OUTPUT_PATH = Path("outputs/llm_comparison.csv")
SUMMARY_PATH = Path("outputs/evaluation_summary.csv")
LIMIT = 10


def normalize_law_answer(value):
    """Normalize common variations such as 'State of Nevada'."""
    text = normalize(value)
    text = text.removeprefix("state of ")
    return text.strip()


def main():
    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found at {CSV_PATH}. Run inspect_cuad.py first."
        )

    df = pd.read_csv(CSV_PATH)
    clause_col, answer_col = find_columns(df, "Governing Law")

    # Select a fixed, reproducible sample with known reference answers.
    sample = df[df[answer_col].notna()].head(LIMIT)

    if sample.empty:
        raise ValueError("No rows with reference answers were found.")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    results = []

    print(f"Evaluating {len(sample)} Governing Law examples.")
    print("Each example makes a Gemini API call; this may take several minutes.")

    for index, (_, row) in enumerate(sample.iterrows(), start=1):
        clause_text = to_text(row[clause_col])
        expected = to_text(row[answer_col])

        if not clause_text.strip() or not expected.strip():
            continue

        baseline_prediction = extract_state(clause_text)
        baseline_correct = (
            normalize_law_answer(baseline_prediction)
            == normalize_law_answer(expected)
        )

        print(f"[{index}/{len(sample)}] Calling Gemini...")

        started = time.perf_counter()

        try:
            llm_result = extract_clause(
                clause_text=clause_text,
                clause_type="Governing Law",
            )
            llm_seconds = round(time.perf_counter() - started, 3)

            llm_prediction = llm_result.get("answer", "")
            evidence = llm_result.get("evidence", "")
            evidence_valid = bool(evidence) and evidence in clause_text

            llm_correct = (
                normalize_law_answer(llm_prediction)
                == normalize_law_answer(expected)
            )

            error = ""

        except Exception as exc:
            llm_seconds = round(time.perf_counter() - started, 3)
            llm_prediction = ""
            evidence = ""
            evidence_valid = False
            llm_correct = False
            error = f"{type(exc).__name__}: {exc}"

        results.append({
            "example_id": index,
            "clause_type": "Governing Law",
            "expected": expected,
            "baseline_prediction": baseline_prediction,
            "baseline_correct": baseline_correct,
            "llm_prediction": llm_prediction,
            "llm_correct": llm_correct,
            "evidence": evidence,
            "evidence_valid": evidence_valid,
            "latency_seconds": llm_seconds,
            "error": error,
        })

        print(
            f"  Expected: {expected} | "
            f"Baseline: {baseline_prediction} | "
            f"Gemini: {llm_prediction or '[no answer]'}"
        )

    results_df = pd.DataFrame(results)
    results_df.to_csv(OUTPUT_PATH, index=False)

    if results_df.empty:
        raise ValueError("No evaluation results were produced.")

    successful = results_df[results_df["error"] == ""]
    summary = {
        "category": "Governing Law",
        "examples_attempted": len(results_df),
        "successful_api_calls": len(successful),
        "failed_api_calls": len(results_df) - len(successful),
        "baseline_accuracy": round(
            results_df["baseline_correct"].mean(), 3
        ),
        "gemini_accuracy_all_attempts": round(
            results_df["llm_correct"].mean(), 3
        ),
        "gemini_accuracy_successful_calls": (
            round(successful["llm_correct"].mean(), 3)
            if not successful.empty else None
        ),
        "evidence_valid_rate_successful_calls": (
            round(successful["evidence_valid"].mean(), 3)
            if not successful.empty else None
        ),
        "average_latency_seconds": (
            round(successful["latency_seconds"].mean(), 3)
            if not successful.empty else None
        ),
    }

    pd.DataFrame([summary]).to_csv(SUMMARY_PATH, index=False)

    print("\n--- Evaluation Summary ---")
    for metric, value in summary.items():
        print(f"{metric}: {value}")

    print(f"\nDetailed results: {OUTPUT_PATH}")
    print(f"Summary report:   {SUMMARY_PATH}")


if __name__ == "__main__":
    main()