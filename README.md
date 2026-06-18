# InvoiceIQ — Invoice-to-Excel AI Extractor

A Python + Streamlit app that extracts structured data from invoice PDFs and images, lets you correct it manually, and exports a clean Excel file.

## Features (Milestone 1 — MVP)

- Upload PDF (digital or scanned) or image (PNG/JPG)
- Extract text via **PyMuPDF** (digital PDFs) or **pytesseract OCR** (scanned/images)
- Parse key fields with regex: Invoice Number, Date, Vendor, Total, Currency
- Manual correction form — fix any misread values
- Editable line-items table (add/remove rows)
- One-click export to a styled `.xlsx` Excel file

## Tech Stack

| Layer | Library |
|-------|---------|
| UI | Streamlit |
| PDF extraction | PyMuPDF (`fitz`) |
| OCR | pytesseract + Pillow |
| Data | pandas |
| Excel export | openpyxl |

## Project Structure

```
InvoiceIQ/
├── app.py              # Streamlit UI
├── requirements.txt
├── .gitignore
│
├── core/
│   ├── extractor.py    # PDF/image → raw text
│   ├── parser.py       # raw text → structured fields (regex)
│   └── exporter.py     # fields + line items → Excel
│
└── data/
    └── uploads/        # temp upload folder (gitignored)
```

## Setup

### 1 — Install Tesseract (required for OCR)

| OS | Command |
|----|---------|
| macOS | `brew install tesseract` |
| Ubuntu/Debian | `sudo apt install tesseract-ocr` |
| Windows | Download installer from [UB-Mannheim](https://github.com/UB-Mannheim/tesseract/wiki) |

### 2 — Create a virtual environment & install dependencies

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3 — Run the app

```bash
streamlit run app.py
```

The app opens at `http://localhost:8501`.

## Roadmap

| Milestone | Goal |
|-----------|------|
| ✅ 1 | Upload → OCR/parse → manual correct → export Excel |
| 2 | Validation layer (missing fields, suspicious values, warnings) |
| 3 | SQLite history — save/browse past extractions |
| 4 | Plotly dashboard — spending trends, vendor summaries |
| 5 | Optional AI parser (Claude/GPT) for higher accuracy |
