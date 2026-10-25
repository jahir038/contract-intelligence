
from pathlib import Path

import pandas as pd

INPUT_PATH = Path("outputs/llm_comparison.csv")
OUTPUT_PATH = Path("outputs/evaluation_summary_v2.csv")

US_STATES = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California",
    "Colorado", "Connecticut", "Delaware", "Florida", "Georgia",
    "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas",
    "Kentucky", "Louisiana", "Maine", "Maryland", "Massachusetts",
    "Michigan", "Minnesota", "Mississippi", "Missouri", "Montana",
    "Nebraska", "Nevada", "New Hampshire", "New Jersey",
    "New Mexico", "New York", "North Carolina", "North Dakota",
    "Ohio", "Oklahoma", "Oregon", "Pennsylvania", "Rhode Island",
    "South Carolina", "South Dakota", "Tennessee", "Texas", "Utah",
    "Vermont", "Virginia", "Washington", "West Virginia", "Wisconsin",
    "Wyoming",
]


def jurisdiction_key(value):
    """Map common legal wording to a comparable jurisdiction label."""
    text = str(value or "").lower()

    if not text.strip() or text == "nan":
        return ""

    # Handle this dataset's England/Wales reference format.
    if "england" in text and "wales" in text:
        return "england and wales"

    # Handle Ontario references that mention Canadian federal law.
    if "ontario" in text:
        return "ontario, canada"

    # Match US states as complete phrases, not partial words.
    import re

    for state in sorted(US_STATES, key=len, reverse=True):
        if re.search(r"\b" + re.escape(state.lower()) + r"\b", text):
            return state.lower()

    # Conservative fallback: remove common legal boilerplate.
    text = re.sub(
        r"\b(the laws of|laws of|law of|the state of|state of|"
        r"the province of|province of|governed by|and construed "
        r"in accordance with)\b",
        " ",
        text,
    )
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return " ".join(text.split())


def main():
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Cannot find {INPUT_PATH}. Run evaluate_llm.py first."
        )

    df = pd.read_csv(INPUT_PATH).fillna("")

    df["expected_key"] = df["expected"].apply(jurisdiction_key)
    df["baseline_key"] = df["baseline_prediction"].apply(jurisdiction_key)
    df["llm_key"] = df["llm_prediction"].apply(jurisdiction_key)

    df["baseline_semantic_correct"] = (
        (df["expected_key"] != "")
        & (df["baseline_key"] == df["expected_key"])
    )

    df["llm_semantic_correct"] = (
        (df["expected_key"] != "")
        & (df["llm_key"] == df["expected_key"])
    )

    successful = df[df["error"].astype(str).str.strip() == ""]

    summary = pd.DataFrame([{
        "examples": len(df),
        "successful_api_calls": len(successful),
        "baseline_jurisdiction_accuracy": round(
            df["baseline_semantic_correct"].mean(), 3
        ),
        "gemini_jurisdiction_accuracy_all_attempts": round(
            df["llm_semantic_correct"].mean(), 3
        ),
        "gemini_jurisdiction_accuracy_successful_calls": round(
            successful["llm_semantic_correct"].mean(), 3
        ) if not successful.empty else None,
        "evidence_substring_valid_rate": round(
            successful["evidence_valid"].astype(str).str.lower()
            .isin(["true", "1"]).mean(), 3
        ) if not successful.empty else None,
        "average_latency_seconds": round(
            pd.to_numeric(
                successful["latency_seconds"], errors="coerce"
            ).mean(), 2
        ) if not successful.empty else None,
    }])

    df.to_csv("outputs/llm_comparison_analyzed.csv", index=False)
    summary.to_csv(OUTPUT_PATH, index=False)

    print("\n--- Revised jurisdiction evaluation ---")
    print(summary.to_string(index=False))
    print("\nPer-example comparison:")
    print(df[[
        "expected", "llm_prediction",
        "expected_key", "llm_key", "llm_semantic_correct"
    ]].to_string(index=False))
    print(f"\nSaved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
