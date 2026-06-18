# InvoiceIQ — Invoice-to-Excel AI Extractor

A Python + Streamlit app that extracts structured data from invoice PDFs and images, lets you correct it manually, and exports a clean Excel file.

## Features

### Milestone 1 — MVP
- Upload PDF (digital or scanned) or image (PNG/JPG)
- Extract text via **PyMuPDF** (digital PDFs) or **pytesseract OCR** (scanned/images)
- Parse key fields with regex: Invoice Number, Date, Vendor, Total, Currency
- Manual correction form — fix any misread values
- Editable line-items table (add/remove rows)
- One-click export to a styled `.xlsx` Excel file

### Milestone 2 — Validation Layer
- Flags missing required fields (Invoice Number, Date, Vendor, Total)
- Detects invalid or negative Total Amount
- Checks Subtotal + Tax = Total when both are provided
- Validates each line item: Quantity × Unit Price should equal its Total
- Compares the sum of all line item Totals against the Invoice Total
- Warns about empty or partially filled line item rows
- Non-blocking — warnings are shown but export is never prevented

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
│   ├── validator.py    # validation checks → list of warnings/errors
│   └── exporter.py     # fields + line items → Excel
│
└── data/
    └── uploads/        # temp upload folder (gitignored)
```

## Setup

### 1 — Install the Tesseract OCR binary

> **Important:** `pytesseract` is only a Python wrapper. It will not work unless the actual **Tesseract binary** is installed at the operating-system level first. Installing `pytesseract` via `pip` alone is not enough.

| OS | Command |
|----|---------|
| macOS | `brew install tesseract` |
| Ubuntu / Debian | `sudo apt install tesseract-ocr` |
| Windows | Download the installer from [UB-Mannheim](https://github.com/UB-Mannheim/tesseract/wiki), run it, then add the install folder (e.g. `C:\Program Files\Tesseract-OCR`) to your system `PATH` |

Verify the installation worked by running `tesseract --version` in your terminal. You should see a version number like `tesseract 5.x.x`.

### 2 — Create a virtual environment & install Python dependencies

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

## Troubleshooting

### `TesseractNotFoundError` when uploading a scanned PDF or image

This error means Python cannot find the Tesseract binary. Check the following:

1. **Is Tesseract installed?** Run `tesseract --version` in your terminal. If the command is not found, go back to Setup step 1.
2. **macOS / Linux** — Make sure the `brew` or `apt` install completed without errors. Try `which tesseract` to confirm the path.
3. **Windows** — After installing, add the Tesseract folder to your `PATH` environment variable and restart your terminal (or VS Code). The default install path is `C:\Program Files\Tesseract-OCR`.
4. If Tesseract is installed in a non-standard location, tell `pytesseract` where to find it by adding this line at the top of `core/extractor.py`:
   ```python
   pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
   ```

### OCR extracts garbled text

- Try uploading a higher-resolution scan (300 DPI or above).
- The extractor automatically renders scanned PDFs at 2× zoom to improve accuracy. For images, make sure they are not blurry or heavily compressed.

### Parser extracts wrong values

The regex parser works well for common invoice layouts. For unusual formats, use the manual correction form in the app to fix any misread fields before exporting.

## Roadmap

| Milestone | Goal |
|-----------|------|
| ✅ 1 | Upload → OCR/parse → manual correct → export Excel |
| ✅ 2 | Validation layer (missing fields, suspicious values, warnings) |
| 3 | SQLite history — save/browse past extractions |
| 4 | Plotly dashboard — spending trends, vendor summaries |
| 5 | Optional AI parser (Claude/GPT) for higher accuracy |
