import pandas as pd
import streamlit as st

from core.extractor import extract_text
from core.exporter import export_to_excel
from core.parser import parse_invoice

st.set_page_config(
    page_title="InvoiceIQ",
    page_icon="📄",
    layout="wide",
)

st.title("📄 InvoiceIQ — Invoice-to-Excel Extractor")
st.caption("Upload an invoice PDF or image · review extracted fields · export clean Excel.")


# ── Session state ─────────────────────────────────────────────────────────────
for key, default in [
    ("current_file", None),
    ("raw_text",     None),
    ("fields",       None),
    ("line_items",   None),
]:
    if key not in st.session_state:
        st.session_state[key] = default


# ── Upload ────────────────────────────────────────────────────────────────────
uploaded_file = st.file_uploader(
    "Upload Invoice",
    type=["pdf", "png", "jpg", "jpeg"],
    help="Supports digital PDFs, scanned PDFs, and images (PNG/JPG).",
)

if uploaded_file is None:
    st.info("Upload an invoice file to get started.")
    st.stop()

# Reset state whenever a different file is loaded
file_id = f"{uploaded_file.name}_{uploaded_file.size}"
if st.session_state.current_file != file_id:
    st.session_state.current_file = file_id
    st.session_state.raw_text     = None
    st.session_state.fields       = None
    st.session_state.line_items   = None

file_bytes = uploaded_file.read()


# ── Extract text ──────────────────────────────────────────────────────────────
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
    st.session_state.fields   = parse_invoice(raw_text)
    st.session_state.line_items = pd.DataFrame(
        columns=["Description", "Quantity", "Unit Price", "Total"]
    )
    method_label = "native PDF text" if method == "pdf_native" else "OCR (pytesseract)"
    st.success(f"Extracted using **{method_label}**.")

with st.expander("View raw extracted text"):
    st.text_area("", st.session_state.raw_text, height=180, disabled=True, label_visibility="collapsed")

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
    currency_options  = ["USD", "EUR", "GBP", "JPY", "Other"]
    saved_currency    = f.get("currency", "USD")
    default_idx       = currency_options.index(saved_currency) if saved_currency in currency_options else 0
    f["currency"]     = st.selectbox("Currency", options=currency_options, index=default_idx)

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


# ── Export ────────────────────────────────────────────────────────────────────
st.subheader("Export")

if st.button("Generate Excel File", type="primary", use_container_width=False):
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
