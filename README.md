# InvoiceIQ — Invoice-to-Excel Extractor

> A Python + Streamlit portfolio project that extracts structured data from invoice PDFs and images, lets you correct it, exports a styled Excel file, and visualises spending trends on an analytics dashboard.

Built milestone-by-milestone: regex parsing → validation → SQLite history → analytics → polish.

---

## Screenshots

Screenshots will be added after the first deployment. The `screenshots/` folder is reserved for them.

| Upload & Extract | Review & Correct | Analytics Dashboard |
|:---:|:---:|:---:|
| *(coming soon)* | *(coming soon)* | *(coming soon)* |

---

## Key Features

- **Upload PDF or image** — digital PDF (native text extraction) or scanned PDF/image (OCR via pytesseract)
- **Auto-extract fields** — Invoice Number, Date, Vendor, Subtotal, Tax, Total, Currency, and Line Items
- **Editable form** — fix any misread field before exporting; line items are editable in an interactive table
- **Non-blocking validation** — warns about missing fields, math mismatches, and suspicious totals without blocking export
- **One-click Excel export** — styled `.xlsx` with a header block and a formatted line items table
- **SQLite history** — save, search, re-open, and delete past invoices; local-only, no cloud required
- **Analytics dashboard** — KPI cards, monthly spending trend, top vendors, currency breakdown, and top line items

---

## Demo Workflow

1. **Upload** — drag a PDF or image onto the file uploader on the main page
2. **Extract** — the app auto-extracts all fields and line items (digital PDFs use native text; scanned files use OCR)
3. **Review** — check the extracted fields in the editable form; correct anything that was misread
4. **Validate** — the Validation panel highlights any issues (e.g. "Subtotal + Tax ≠ Total")
5. **Export** — click **Generate Excel File** and download the styled `.xlsx`
6. **Save** — click **Save to History** to store the invoice in the local SQLite database
7. **Analyse** — open the **Analytics** page to see KPI cards and spending charts across all saved invoices

---

## Tech Stack

| Layer | Library / Tool | Purpose |
|-------|---------------|---------|
| UI | Streamlit (multipage) | Pages, form widgets, interactive tables |
| PDF extraction | PyMuPDF (`fitz`) | Native text from digital PDFs |
| OCR | pytesseract + Pillow | Text from scanned PDFs and images |
| Parsing | Python `re` (regex) | Field and line-item extraction |
| Data | pandas | DataFrames, aggregations |
| Excel export | openpyxl | Styled `.xlsx` generation |
| Database | SQLite (stdlib `sqlite3`) | Local invoice history with foreign-key cascades |
| Charts | Plotly Express | Interactive spending charts |

---

## Project Structure

```
InvoiceIQ/
├── app.py               # Main Streamlit page (upload → extract → correct → export → save)
├── requirements.txt     # Runtime dependencies
├── requirements-dev.txt # Dev/test dependencies (pytest)
├── .gitignore
│
├── core/
│   ├── extractor.py     # PDF/image → raw text (PyMuPDF + pytesseract fallback)
│   ├── parser.py        # Raw text → structured fields and line items (regex)
│   ├── validator.py     # Fields + line items → list of validation warnings
│   ├── exporter.py      # Fields + line items → styled Excel file
│   └── database.py      # SQLite helpers (save, load, search, delete)
│
├── pages/
│   ├── history.py       # History page — browse, search, re-open, delete saved invoices
│   └── analytics.py     # Analytics page — KPI cards and spending charts
│
├── tests/
│   └── test_parser.py   # 49 pytest tests covering parser and validator
│
├── screenshots/         # App screenshots (for README and portfolio)
│
└── data/
    ├── uploads/         # Temporary upload folder (gitignored)
    └── invoices.db      # Local SQLite database (gitignored)
```

---

## Setup

### 1 — Install the Tesseract OCR binary

> **Important:** `pytesseract` is only a Python wrapper. You must install the Tesseract binary at the OS level first — `pip install pytesseract` alone is not enough.

| OS | Command |
|----|---------|
| macOS | `brew install tesseract` |
| Ubuntu / Debian | `sudo apt install tesseract-ocr` |
| Windows | Download the installer from [UB-Mannheim](https://github.com/UB-Mannheim/tesseract/wiki), run it, then add the install folder (e.g. `C:\Program Files\Tesseract-OCR`) to your `PATH` |

Verify: run `tesseract --version` — you should see `tesseract 5.x.x`.

### 2 — Create a virtual environment and install Python dependencies

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3 — Run the app

```bash
streamlit run app.py
```

The app opens at `http://localhost:8501`. The SQLite database and uploads folder are created automatically on first run.

### 4 — Run the tests

```bash
pip install -r requirements-dev.txt   # installs pytest (one-time)
pytest tests/ -v
```

49 tests cover invoice field extraction (number, date, vendor, total, subtotal, tax, currency) and line-item parsing across two invoice layouts (Zylker-style and QTY-first).

---

## Deploying to Streamlit Cloud

The app can be deployed to [Streamlit Community Cloud](https://streamlit.io/cloud) with one important caveat.

**Tesseract must be installed on the server.** Add a `packages.txt` file at the repo root containing:

```
tesseract-ocr
```

Streamlit Cloud reads `packages.txt` and installs APT packages before starting the app. Without this file, OCR will fail with `TesseractNotFoundError` for scanned PDFs and images. Digital PDFs (native text via PyMuPDF) continue to work regardless.

**Database persistence:** `data/invoices.db` is gitignored and created fresh on each deploy. The SQLite file is **ephemeral** on Streamlit Cloud — it resets whenever the app restarts. For persistent history in a deployed app, swap SQLite for a hosted database (e.g. Supabase, PlanetScale).

---

## Current Limitations

- **Regex parsing only** — works well for common invoice layouts; unusual or highly irregular formats may require manual field correction
- **English field labels** — the parser matches labels like "Invoice Number", "Date", "Total" in English; other languages are not supported
- **Ephemeral history on the cloud** — SQLite is a local file; history is lost between Streamlit Cloud restarts (see deployment note above)
- **No multi-page deduplication** — very long invoices with repeated header rows across pages may produce duplicate line items

---

## Future Improvements

- **LLM-assisted parsing** — use Claude or GPT as a fallback for invoices the regex parser cannot handle
- **Multi-language support** — detect and match field labels in French, Arabic, German, and other languages
- **Hosted database** — replace SQLite with Supabase or PostgreSQL for persistent, multi-user history
- **Bulk upload** — process a folder of invoices at once and export a combined summary spreadsheet
- **Email integration** — pull invoice attachments directly from Gmail or Outlook via API
- **CSV export** — add a second download option alongside Excel

---

## CV / Portfolio Bullet Points

Copy-paste ready for a resume or LinkedIn:

- Built **InvoiceIQ**, a Python + Streamlit app that extracts structured data from invoice PDFs using PyMuPDF and pytesseract OCR, then exports styled Excel files via openpyxl
- Designed a **dual-pattern regex parser** handling multiple invoice table layouts; built a non-blocking validation layer that checks field presence, math consistency (Subtotal + Tax = Total), and suspicious totals
- Implemented a **SQLite history module** (save, search, re-open, delete with cascade) and an **analytics dashboard** with KPI cards and Plotly charts for monthly spend, top vendors, currency split, and line-item summaries
- Wrote a **49-test pytest suite** covering all parser branches and validation rules; structured the project for GitHub with `.gitignore`, `requirements.txt`, and a full portfolio README

---

## Troubleshooting

### `TesseractNotFoundError` when uploading a scanned PDF or image

1. **Is Tesseract installed?** Run `tesseract --version`. If not found, follow Setup step 1 above.
2. **macOS / Linux** — run `which tesseract` to confirm the binary is on your PATH.
3. **Windows** — after installing, add the Tesseract folder to your `PATH` environment variable and restart your terminal (or VS Code).
4. If Tesseract is installed in a non-standard location, add this line at the top of `core/extractor.py`:
   ```python
   pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
   ```

### OCR extracts garbled text

Upload a higher-resolution scan (300 DPI or above). The extractor renders scanned PDFs at 2× zoom automatically; for images, make sure they are not blurry or heavily compressed.

### Parser extracts wrong values

The regex parser works well for standard layouts. Use the manual correction form to fix any misread field before exporting — no re-upload is needed.

---

## Roadmap

| Milestone | Goal | Status |
|-----------|------|--------|
| 1 | Upload → OCR/parse → manual correct → export Excel | ✅ Done |
| 2 | Validation layer — missing fields, math checks, warnings | ✅ Done |
| 3 | SQLite history — save, browse, re-open, delete | ✅ Done |
| 4 | Analytics dashboard — KPI cards, spending trends, vendor summaries | ✅ Done |
| 5 | Polish, screenshots, deployment preparation | ✅ Done |
| 6 | Optional — LLM-assisted parsing (Claude / GPT) for higher accuracy | Future |
