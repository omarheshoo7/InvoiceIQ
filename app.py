import pandas as pd
import streamlit as st

from core.database import init_db, save_invoice
from core.extractor import extract_text
from core.exporter import export_to_excel
from core.parser import parse_invoice, parse_line_items
from core.validator import validate_invoice

st.set_page_config(
    page_title="InvoiceIQ",
    page_icon="📄",
    layout="wide",
)

st.title("📄 InvoiceIQ — Invoice-to-Excel Extractor")
st.caption("Upload a PDF or image · auto-extract fields and line items · correct if needed · export to Excel · save to history.")

# Ensure DB and tables exist on every page load (no-op if already created)
init_db()


# ── Session state ─────────────────────────────────────────────────────────────
for key, default in [
    ("current_file",          None),
    ("raw_text",              None),
    ("fields",                None),
    ("line_items",            None),
    ("loaded_from_history",   False),
    ("source_filename",       ""),
]:
    if key not in st.session_state:
        st.session_state[key] = default


# ── Upload ────────────────────────────────────────────────────────────────────
uploaded_file = st.file_uploader(
    "Upload Invoice",
    type=["pdf", "png", "jpg", "jpeg"],
    help="Supports digital PDFs, scanned PDFs, and images (PNG/JPG).",
)

# Allow the page to proceed either from a fresh upload OR from history re-open
if uploaded_file is None and not st.session_state.loaded_from_history:
    st.info("Upload an invoice file to get started, or re-open one from the **History** page.")
    st.stop()


# ── Handle fresh upload ───────────────────────────────────────────────────────
if uploaded_file is not None:
    # When a new (different) file is uploaded, reset all extracted state
    file_id = f"{uploaded_file.name}_{uploaded_file.size}"
    if st.session_state.current_file != file_id:
        st.session_state.current_file        = file_id
        st.session_state.raw_text            = None
        st.session_state.fields              = None
        st.session_state.line_items          = None
        st.session_state.loaded_from_history = False
        st.session_state.source_filename     = uploaded_file.name

    file_bytes = uploaded_file.read()

    if st.session_state.raw_text is None:
        with st.spinner("Extracting text from invoice…"):
            try:
                raw_text, method = extract_text(file_bytes, uploaded_file.name)
            except ValueError as e:
                st.error(str(e))
                st.stop()
            except Exception as e:
                st.error(f"Extraction failed: {e}")
                st.stop()

        st.session_state.raw_text = raw_text
        parsed = parse_invoice(raw_text)
        st.session_state.fields     = parsed
        st.session_state.line_items = parse_line_items(raw_text)
        method_label = "native PDF text" if method == "pdf_native" else "OCR (pytesseract)"
        st.success(f"Extracted using **{method_label}**.")


# ── Raw text / history banner ─────────────────────────────────────────────────
if st.session_state.loaded_from_history:
    st.info(
        "Reopened from history — original OCR text is not available. "
        "Edit any fields below and re-export as needed."
    )
else:
    with st.expander("View raw extracted text"):
        st.text_area(
            "",
            st.session_state.raw_text,
            height=180,
            disabled=True,
            label_visibility="collapsed",
        )

st.divider()


# ── Invoice fields form ───────────────────────────────────────────────────────
st.subheader("Invoice Fields")
st.caption("Correct any misread values before exporting.")

f = st.session_state.fields
col1, col2 = st.columns(2)

with col1:
    f["invoice_number"] = st.text_input("Invoice Number", value=f.get("invoice_number", ""))
    f["invoice_date"]   = st.text_input("Invoice Date",   value=f.get("invoice_date",   ""))
    f["vendor_name"]    = st.text_input("Vendor Name",    value=f.get("vendor_name",    ""))

with col2:
    f["total_amount"] = st.text_input("Total Amount", value=f.get("total_amount", ""))
    currency_options  = ["USD", "EUR", "GBP", "JPY", "EGP", "Other"]
    saved_currency    = f.get("currency", "USD")
    default_idx       = currency_options.index(saved_currency) if saved_currency in currency_options else 0
    f["currency"]     = st.selectbox("Currency", options=currency_options, index=default_idx)
    f["subtotal"]     = st.text_input("Subtotal (optional)",  value=f.get("subtotal", ""))
    f["tax"]          = st.text_input("Tax / VAT (optional)", value=f.get("tax",      ""))

st.divider()


# ── Line items ────────────────────────────────────────────────────────────────
st.subheader("Line Items")
st.caption("Add or edit rows. Leave empty if the invoice has no line items.")

edited_df = st.data_editor(
    st.session_state.line_items,
    use_container_width=True,
    num_rows="dynamic",
    column_config={
        "Description": st.column_config.TextColumn("Description", width="large"),
        "Quantity":    st.column_config.NumberColumn("Quantity",   min_value=0, step=1),
        "Unit Price":  st.column_config.NumberColumn("Unit Price", min_value=0, format="%.2f"),
        "Total":       st.column_config.NumberColumn("Total",      min_value=0, format="%.2f"),
    },
)
st.session_state.line_items = edited_df

st.divider()


# ── Validation ────────────────────────────────────────────────────────────────
st.subheader("Validation")

issues = validate_invoice(st.session_state.fields, st.session_state.line_items)

if not issues:
    st.success("All checks passed — no issues found.")
else:
    errors   = [i for i in issues if i.level == "error"]
    warnings = [i for i in issues if i.level == "warning"]

    if errors:
        st.error(f"**{len(errors)} error(s) found** — please review before exporting.")
        for issue in errors:
            st.error(f"- {issue.message}")

    if warnings:
        st.warning(f"**{len(warnings)} warning(s)** — you can still export, but please review.")
        for issue in warnings:
            st.warning(f"- {issue.message}")

st.divider()


# ── Export ────────────────────────────────────────────────────────────────────
st.subheader("Export")
st.caption("Generates a styled `.xlsx` file containing the invoice fields and the full line items table.")

if st.button("Generate Excel File", type="primary"):
    with st.spinner("Building Excel file…"):
        excel_bytes = export_to_excel(st.session_state.fields, st.session_state.line_items)

    inv_num  = st.session_state.fields.get("invoice_number") or "export"
    filename = f"invoice_{inv_num}.xlsx"

    st.download_button(
        label     = "⬇ Download Excel",
        data      = excel_bytes,
        file_name = filename,
        mime      = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

st.divider()


# ── Save to History ───────────────────────────────────────────────────────────
st.subheader("Save to History")
st.caption(
    "Save this invoice to your local database so you can retrieve it later "
    "from the **History** page. You control when to save — click once per invoice."
)

if st.button("Save to History"):
    record_id = save_invoice(
        fields          = st.session_state.fields,
        line_items_df   = st.session_state.line_items,
        source_filename = st.session_state.get("source_filename", "unknown"),
    )
    st.toast(f"Invoice saved to history (record #{record_id}).", icon="✅")
