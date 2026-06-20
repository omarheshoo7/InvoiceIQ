# InvoiceIQ — Invoice-to-Excel AI Extractor

A Python + Streamlit app that extracts structured data from invoice PDFs and images, lets you correct it manually, exports a clean Excel file, and visualises spending trends on an analytics dashboard.

**Key features:**
- Upload PDF (digital or scanned) or image → auto-extract Invoice Number, Date, Vendor, Subtotal, Tax, Total, and Line Items
- Manual correction form — fix any misread fields before exporting
- Non-blocking validation warnings (missing fields, math errors, suspicious totals)
- One-click export to a styled `.xlsx` Excel file
- SQLite invoice history — save, search, and re-open past invoices
- Analytics dashboard — spending trends, vendor summaries, and KPI cards

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

### Milestone 3 — SQLite Invoice History
- Explicit **Save to History** button — saves only when you choose, preventing duplicates
- Local SQLite database (`data/invoices.db`) stores invoice fields + line items
- **History page** — browse all saved invoices in a table, newest first
- **Search / filter** — real-time filtering by vendor name or invoice number
- **Re-open** — click any record to reload its fields and line items back into the main form, ready to edit and re-export
- **Delete** — remove a record with a confirmation step; line items are removed automatically

### Milestone 4 — Analytics Dashboard
- **Total Invoiced** KPI — sum of all saved invoice totals
- **Invoice Count** KPI — total number of saved invoices
- **Unique Vendors** KPI — count of distinct vendor names
- **Average Invoice** KPI — mean invoice value across all records
- **Monthly Spending** bar chart — total spend grouped by invoice month, with `saved_at` as a fallback when Invoice Date is blank
- **Top Vendors** horizontal bar chart — top 10 vendors ranked by total spend
- **Currency Breakdown** donut chart — invoice count split by currency
- **Top Line Items** bar chart — top 10 most-billed line item descriptions by total spend
- Mixed-currency invoices handled gracefully — KPIs note when totals span multiple currencies
- Requires at least 2 saved invoices; shows a friendly prompt otherwise

## Tech Stack

| Layer | Library |
|-------|---------|
| UI | Streamlit (multipage) |
| PDF extraction | PyMuPDF (`fitz`) |
| OCR | pytesseract + Pillow |
| Data | pandas |
| Excel export | openpyxl |
| Database | SQLite (stdlib `sqlite3`) |
| Charts | Plotly Express |

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
│   ├── exporter.py     # fields + line items → Excel
│   └── database.py     # SQLite read/write helpers
│
├── pages/
│   ├── history.py      # Streamlit History page
│   └── analytics.py    # Streamlit Analytics Dashboard
│
├── tests/
│   └── test_parser.py  # pytest smoke tests for the parser
│
└── data/
    ├── uploads/        # temp upload folder (gitignored)
    └── invoices.db     # local SQLite database (gitignored)
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
| ✅ 3 | SQLite history — save, browse, re-open, delete past invoices |
| ✅ 4 | Analytics dashboard — KPI cards, spending trends, vendor summaries |
| 5 | Optional AI parser (Claude/GPT) for higher accuracy |
