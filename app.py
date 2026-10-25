
import io
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from pypdf import PdfReader

from llm_extractor import extract_clause

app = FastAPI(
    title="Contract Intelligence",
    description="Extract structured information from contract text.",
    version="0.2.0",
)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


class ExtractionRequest(BaseModel):
    clause_type: Literal[
        "Governing Law",
        "Effective Date",
        "Termination for Convenience",
    ]
    clause_text: str = Field(min_length=10, max_length=30000)


@app.get("/", response_class=HTMLResponse)
def home():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Contract Intelligence</title>
<style>
body {
    font-family: Arial, sans-serif;
    max-width: 850px;
    margin: 40px auto;
    padding: 0 20px;
    background: #f5f7fa;
    color: #202938;
}
h1 { margin-bottom: 8px; }
.subtitle { color: #596579; margin-bottom: 28px; }
.panel {
    background: white;
    padding: 24px;
    border-radius: 12px;
    border: 1px solid #e0e5ec;
    margin-bottom: 20px;
}
label {
    display: block;
    font-weight: bold;
    margin: 16px 0 8px;
}
select, textarea, input[type=file] {
    width: 100%;
    box-sizing: border-box;
    padding: 12px;
    border: 1px solid #cbd2dc;
    border-radius: 7px;
    font: inherit;
}
textarea { min-height: 190px; resize: vertical; }
button {
    margin-top: 12px;
    padding: 12px 20px;
    border: 0;
    border-radius: 7px;
    background: #2459a9;
    color: white;
    font-size: 15px;
    cursor: pointer;
}
button:disabled { opacity: 0.6; cursor: wait; }
.result-value { font-size: 22px; font-weight: bold; }
.evidence {
    background: #f5f7fa;
    padding: 14px;
    border-radius: 7px;
    line-height: 1.6;
    white-space: pre-wrap;
}
.muted { color: #596579; }
.error { color: #b42318; }
.hidden { display: none; }
</style>
</head>
<body>
<h1>Contract Intelligence</h1>
<p class="subtitle">
Upload a contract or paste text to extract key information using AI.
</p>

<section class="panel">
    <h2>1. Load a document</h2>
    <p class="muted">Supported formats: PDF and TXT. Maximum size: 10 MB.</p>
    <label for="document">Choose a contract file</label>
    <input id="document" type="file" accept=".pdf,.txt">
    <button id="load-button" type="button">Load document text</button>
    <p id="upload-status" class="muted"></p>
</section>

<section class="panel">
    <h2>2. Extract information</h2>
    <form id="extract-form">
        <label for="clause-type">Information to extract</label>
        <select id="clause-type">
            <option>Governing Law</option>
            <option>Effective Date</option>
            <option>Termination for Convenience</option>
        </select>

        <label for="clause-text">Contract text</label>
        <textarea id="clause-text"
            placeholder="Load a document above or paste a clause here..."
            required minlength="10" maxlength="30000"></textarea>

        <button id="extract-button" type="submit">
            Extract information
        </button>
    </form>
</section>

<section id="result" class="panel hidden">
    <h2>Extraction result</h2>
    <p class="muted">Extracted answer</p>
    <p id="answer" class="result-value"></p>

    <p class="muted">Supporting evidence</p>
    <div id="evidence" class="evidence"></div>

    <p id="status" class="muted"></p>
    <p id="latency" class="muted"></p>
    <p id="warning" class="error"></p>
</section>

<script>
const loadButton = document.getElementById("load-button");
const fileInput = document.getElementById("document");
const textArea = document.getElementById("clause-text");

loadButton.addEventListener("click", async () => {
    const file = fileInput.files[0];
    const uploadStatus = document.getElementById("upload-status");

    if (!file) {
        uploadStatus.textContent = "Please choose a PDF or TXT file first.";
        return;
    }

    loadButton.disabled = true;
    loadButton.textContent = "Reading document...";
    uploadStatus.textContent = "";

    try {
        const formData = new FormData();
        formData.append("file", file);

        const response = await fetch("/upload", {
            method: "POST",
            body: formData
        });
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Could not read the document.");
        }

        textArea.value = data.text;
        uploadStatus.textContent =
            "Loaded " + data.filename + ". Extracted " +
            data.character_count + " characters. Review the text below.";
    } catch (error) {
        uploadStatus.textContent = error.message;
    } finally {
        loadButton.disabled = false;
        loadButton.textContent = "Load document text";
    }
});

document.getElementById("extract-form").addEventListener(
    "submit", async (event) => {
        event.preventDefault();

        const button = document.getElementById("extract-button");
        const resultPanel = document.getElementById("result");

        button.disabled = true;
        button.textContent = "Processing...";
        resultPanel.classList.remove("hidden");

        document.getElementById("answer").textContent = "";
        document.getElementById("evidence").textContent = "";
        document.getElementById("status").textContent =
            "Waiting for the AI response...";
        document.getElementById("latency").textContent = "";
        document.getElementById("warning").textContent = "";

        try {
            const response = await fetch("/extract", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({
                    clause_type:
                        document.getElementById("clause-type").value,
                    clause_text: textArea.value.trim()
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || "The request failed.");
            }

            document.getElementById("answer").textContent =
                data.answer || "No answer found";
            document.getElementById("evidence").textContent =
                data.evidence || "No evidence returned";
            document.getElementById("status").textContent =
                "Status: " + (data.status || "unknown");
            document.getElementById("latency").textContent =
                "Processing time: " +
                (data.latency_seconds ?? "unavailable") + " seconds";

            if (!data.evidence_valid) {
                document.getElementById("warning").textContent =
                    "Warning: Evidence was not verified as an exact " +
                    "excerpt of the supplied text.";
            }
        } catch (error) {
            document.getElementById("status").textContent =
                "Request failed.";
            document.getElementById("warning").textContent = error.message;
        } finally {
            button.disabled = false;
            button.textContent = "Extract information";
        }
    }
);
</script>
</body>
</html>
"""


@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    filename = Path(file.filename or "").name
    extension = Path(filename).suffix.lower()

    if extension not in {".pdf", ".txt"}:
        raise HTTPException(
            status_code=400,
            detail="Only PDF and TXT files are supported.",
        )

    contents = await file.read(MAX_FILE_SIZE + 1)

    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File exceeds the 10 MB limit.",
        )

    if not contents:
        raise HTTPException(status_code=400, detail="The file is empty.")

    try:
        if extension == ".txt":
            text = contents.decode("utf-8-sig")
        else:
            reader = PdfReader(io.BytesIO(contents))

            if reader.is_encrypted:
                raise HTTPException(
                    status_code=400,
                    detail="Password-protected PDFs are not supported.",
                )

            text = "\n\n".join(
                page.extract_text() or "" for page in reader.pages
            )

    except HTTPException:
        raise
    except Exception as exc:
        print(f"Document reading failed: {type(exc).__name__}: {exc}")
        raise HTTPException(
            status_code=400,
            detail="Could not read this file. Check that it is a valid PDF or TXT file.",
        ) from exc

    text = text.strip()

    if len(text) < 10:
        raise HTTPException(
            status_code=422,
            detail=(
                "No usable text was extracted. The PDF may be scanned or image-only; "
                "OCR is not implemented yet."
            ),
        )

    if len(text) > 30000:
        raise HTTPException(
            status_code=413,
            detail=(
                "The document contains more than 30,000 characters. "
                "For this MVP, upload a shorter document or paste a relevant clause."
            ),
        )

    return {
        "filename": filename,
        "character_count": len(text),
        "text": text,
    }


@app.post("/extract")
def extract(request: ExtractionRequest):
    try:
        return extract_clause(
            clause_text=request.clause_text,
            clause_type=request.clause_type,
        )
    except Exception as exc:
        print(f"Extraction failed: {type(exc).__name__}: {exc}")
        raise HTTPException(
            status_code=502,
            detail="Extraction failed. Check the server logs.",
        ) from exc
