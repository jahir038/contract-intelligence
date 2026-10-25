# Contract Intelligence — Explainable Contract Clause Extraction

A deployed **FastAPI + Gemini** prototype that extracts selected information from contracts and returns the answer with supporting source text. The project uses examples from **CUAD (Contract Understanding Atticus Dataset)** to compare a simple rule-based baseline with LLM-based extraction.

> **Status:** Working portfolio MVP / research prototype. **Not** a production legal-review system or legal advice.

## What it does

- Upload a text-based PDF or `.txt` contract through a browser interface.
- Select a clause category: **Governing Law**, **Effective Date**, or **Termination for Convenience**.
- Extract a concise answer and evidence using the Gemini API.
- Return structured output, including extraction status and an evidence-substring check.
- Compare a baseline against LLM extraction on a small CUAD evaluation sample.

**Live demo:**  `https://contract-intelligence-2uts.onrender.com`
**API documentation:** `https://contract-intelligence-2uts.onrender.com/docs`

## Architecture

```text
Browser (upload / select clause)
       |
       v
FastAPI web app (app.py)
       |-- /upload: validate file -> extract PDF or text
       |-- /extract: validate input -> request extraction
       v
LLM extraction (llm_extractor.py)
       |
       v
Gemini API (external model hosting)
       |
       v
Structured answer + supporting evidence + status
```

The application is hosted on **Render**; **Gemini inference runs through Google's API**, not on the Render instance. FastAPI is served using **Uvicorn (ASGI)**.

## Repository guide

| File                            | Purpose                                                                            |
| ------------------------------- | ---------------------------------------------------------------------------------- |
| `app.py`                      | FastAPI routes and browser UI; file validation and text extraction                 |
| `llm_extractor.py`            | Gemini request, output parsing, evidence check, latency measurement                |
| `pipeline.py`                 | Rule-based baseline extraction                                                     |
| `inspect_cuad.py`             | Obtain and inspect the CUAD-derived clause data                                    |
| `evaluate_llm.py`             | Run a small baseline-vs-LLM evaluation                                             |
| `analyze_evaluation.py`       | Normalize jurisdictions and analyze saved predictions without additional API calls |
| `pyproject.toml`, `uv.lock` | Python dependency definitions and lockfile                                         |

The downloaded dataset, generated evaluation outputs, `.env`, and private project notes are intentionally excluded from version control.

## Local setup

Prerequisites: Python compatible with `pyproject.toml`, [uv](https://docs.astral.sh/uv/), and a Gemini API key.

```bash
# Clone your own repository
 git clone https://github.com/<YOUR_USERNAME>/contract-intelligence.git
 cd contract-intelligence

# Install the project's locked dependencies
 uv sync --locked
```

Create a local `.env` file (never commit it):

```dotenv
GEMINI_API_KEY=your_api_key_here
```

Start the application:

```bash
uv run uvicorn app:app --reload
```

Open `http://127.0.0.1:8000/` for the UI or `http://127.0.0.1:8000/docs` for the API documentation. Upload a **synthetic/non-confidential** PDF or text contract and select a clause to extract.

### Reproduce the evaluation

```bash
uv run python inspect_cuad.py
uv run python pipeline.py
uv run python evaluate_llm.py
uv run python analyze_evaluation.py
```

The scripts use local data and output directories; inspect the script-level paths and model configuration before running. The LLM evaluation makes external API calls, can be slow, and may incur charges. Results can change across model versions and API responses. For an exact replication, pin the model version and record the evaluation sample IDs, prompts, settings, and execution date.

## Pilot evaluation

A **10-example Governing Law** pilot produced the following results after jurisdiction normalization:

| Metric                                              | Observed result |
| --------------------------------------------------- | --------------: |
| CUAD examples attempted                             |              10 |
| Successful Gemini API calls                         |          9 / 10 |
| Rule-based baseline jurisdiction accuracy           |    8 / 10 (80%) |
| Gemini jurisdiction accuracy, all attempts          |    9 / 10 (90%) |
| Gemini jurisdiction accuracy, successful calls only |    9 / 9 (100%) |
| Evidence substring-valid rate, successful calls     |            100% |
| Average Gemini latency                              | ~107.92 seconds |

**Interpretation:** This is a very small, single-clause pilot, not a statistically reliable benchmark. Initial strict string matching understated model performance because valid jurisdiction answers were phrased differently; the follow-up analysis normalized jurisdiction names. The substring evidence check only verifies that returned text appears in the source—it **does not** prove semantic correctness, completeness, or legal validity. One API attempt failed or returned no usable answer. Latency is a major limitation.

## Deployment on Render

Create a **Web Service** connected to the repository's `main` branch:

```text
Runtime:       Python
Build command: pip install uv && uv sync --locked
Start command: uv run uvicorn app:app --host 0.0.0.0 --port $PORT
```

Set `GEMINI_API_KEY` in **Render Environment Variables** rather than committing credentials. Confirm the deployed root URL and `/docs` route. Automatic deployments can rebuild after pushes to `main` when enabled.

## Safety and current limitations

- **Prototype only:** no legal advice, no human review workflow, and no guarantee of extraction correctness.
- **Sensitive data:** do not upload confidential or personal contracts to the public demo; text is sent to an external model API.
- **No OCR:** scanned/image-only PDFs are not supported by the current extraction path.
- **Input limits:** PDF/TXT only, maximum upload size 10 MB, and extracted text capped at 30,000 characters.
- **Scope:** three supported clause categories; pilot evaluation currently covers only Governing Law.
- **Performance:** external LLM inference is slow in the measured pilot; optimize before promising interactive production SLAs.
- **Security and cost:** public prototype has no authentication or robust per-user rate limiting; add access control, quotas, monitoring, and spending safeguards before broader exposure.
- **Evidence validation:** literal substring checks are not factual-grounding verification.

## Next steps (not yet implemented)

Larger stratified evaluation, precision/recall for clause detection, robust structured-output validation, retry/timeouts, caching, latency/cost dashboards, OCR for scanned PDFs, access control, and human-in-the-loop review.

## Technologies

Python · FastAPI · Uvicorn · Gemini API (`google-genai`) · `pypdf` · `uv` · Git/GitHub · Render · CUAD

## Dataset attribution

CUAD (Contract Understanding Atticus Dataset) is a public contract-review research dataset. Consult the original dataset documentation and license/usage terms before redistributing any source documents or data. This repository excludes the downloaded dataset by default.
