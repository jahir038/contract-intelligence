
import ast
import re
from pathlib import Path

import pandas as pd

CSV_PATH = Path("data/master_clauses.csv")
OUTPUT_PATH = Path("outputs/baseline_results.csv")
LIMIT = 100  # Start small; increase after checking the results.

# Starter vocabulary. This is intentionally a simple baseline.
US_STATES = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California",
    "Colorado", "Connecticut", "Delaware", "Florida", "Georgia",
    "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas",
    "Kentucky", "Louisiana", "Maine", "Maryland", "Massachusetts",
    "Michigan", "Minnesota", "Mississippi", "Missouri", "Montana",
    "Nebraska", "Nevada", "New Hampshire", "New Jersey", "New Mexico",
    "New York", "North Carolina", "North Dakota", "Ohio", "Oklahoma",
    "Oregon", "Pennsylvania", "Rhode Island", "South Carolina",
    "South Dakota", "Tennessee", "Texas", "Utah", "Vermont",
    "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming",
]


def to_text(value):
    """Convert a CSV cell into readable text."""
    if pd.isna(value):
        return ""

    if isinstance(value, str):
        try:
            parsed = ast.literal_eval(value)
            if isinstance(parsed, list):
                return " ".join(str(item) for item in parsed)
        except (ValueError, SyntaxError):
            pass

    if isinstance(value, list):
        return " ".join(str(item) for item in value)

    return str(value)


def normalize(value):
    """Normalize text before exact-match comparison."""
    text = to_text(value).lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s]", "", text)
    return text.strip()


def find_columns(df, category):
    """Find the clause and reference-answer columns."""
    if category in df.columns:
        clause_col = category
    else:
        clause_col = next(
            (
                col for col in df.columns
                if category.lower() in col.lower()
                and not col.lower().endswith("-answer")
            ),
            None,
        )

    answer_col = f"{clause_col}-Answer" if clause_col else None

    if clause_col not in df.columns or answer_col not in df.columns:
        print(f"Skipping {category}: matching columns not found.")
        return None, None

    return clause_col, answer_col


def extract_state(clause):
    """Find a US state mentioned in a clause."""
    for state in US_STATES:
        if re.search(rf"\b{re.escape(state)}\b", clause, re.IGNORECASE):
            return state
    return ""


def extract_date(clause):
    """Find a date written in a few common text formats."""
    patterns = [
        r"\b(?:January|February|March|April|May|June|July|August|"
        r"September|October|November|December)\s+\d{1,2},?\s+\d{4}\b",
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
        r"\b\d{4}-\d{2}-\d{2}\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, clause, re.IGNORECASE)
        if match:
            return match.group(0)

    return ""


def extract_termination(clause):
    """Return the first sentence mentioning termination."""
    sentences = re.split(r"(?<=[.!?])\s+", clause)

    for sentence in sentences:
        if re.search(r"\bterminat(?:e|es|ed|ing|ion)\b", sentence, re.IGNORECASE):
            return sentence.strip()

    return ""


def main():
    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found at {CSV_PATH}. Run inspect_cuad.py first."
        )

    df = pd.read_csv(CSV_PATH)
    print(f"Loaded {len(df)} records.")

    # Use the actual CUAD category name for termination.
    available_termination = next(
        (
            col for col in df.columns
            if "termination for convenience" in col.lower()
            and not col.lower().endswith("-answer")
        ),
        None,
    )

    categories = [
        ("Governing Law", extract_state),
        ("Effective Date", extract_date),
    ]

    if available_termination:
        categories.append((available_termination, extract_termination))
    else:
        print("Termination for Convenience columns not found; skipping it.")

    results = []

    for category, extractor in categories:
        clause_col, answer_col = find_columns(df, category)

        if not clause_col:
            continue

        # Evaluate rows with a reference answer, up to LIMIT.
        eligible = df[df[answer_col].notna()].head(LIMIT)

        for row_index, row in eligible.iterrows():
            clause = to_text(row[clause_col])
            expected = to_text(row[answer_col])
            predicted = extractor(clause)

            results.append({
                "row_index": row_index,
                "category": category,
                "clause_text": clause,
                "expected_answer": expected,
                "predicted_answer": predicted,
                "correct_exact_match": (
                    normalize(predicted) == normalize(expected)
                ),
            })

    if not results:
        print("No results generated. Check the dataset column names.")
        return

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    results_df = pd.DataFrame(results)
    results_df.to_csv(OUTPUT_PATH, index=False)

    print("\n=== Baseline evaluation ===")
    print(f"Evaluated predictions: {len(results_df)}")
    print(
        "Exact-match accuracy: "
        f"{results_df['correct_exact_match'].mean():.1%}"
    )

    print("\nResults by category:")
    summary = results_df.groupby("category").agg(
        evaluated=("correct_exact_match", "size"),
        accuracy=("correct_exact_match", "mean"),
    )
    print(summary.to_string())

    print(f"\nDetailed results saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
