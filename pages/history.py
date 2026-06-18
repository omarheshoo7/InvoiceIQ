import pandas as pd
import streamlit as st

from core.database import (
    delete_invoice,
    init_db,
    load_all_invoices,
    load_invoice_by_id,
    search_invoices,
)

st.set_page_config(
    page_title="InvoiceIQ – History",
    page_icon="🗂",
    layout="wide",
)

st.title("🗂 Invoice History")
st.caption("All invoices saved to your local database. Search, re-open, or delete records below.")

# Ensure DB tables exist (no-op if already created)
init_db()

# Session state used only by this page
st.session_state.setdefault("delete_confirm_id", None)


# ── Search bar ────────────────────────────────────────────────────────────────
query = st.text_input(
    "Search",
    placeholder="Filter by vendor name or invoice number…",
    label_visibility="collapsed",
)

df = search_invoices(query.strip()) if query.strip() else load_all_invoices()


# ── Empty state ───────────────────────────────────────────────────────────────
if df.empty:
    st.info(
        "No invoices saved yet. "
        "Upload and extract an invoice on the main page, then click **Save to History**."
    )
    st.stop()

st.caption(f"{len(df)} invoice(s) found.")
st.divider()


# ── Table header ──────────────────────────────────────────────────────────────
COLS = [0.4, 2.2, 1.6, 1.4, 1.2, 0.8, 1.8, 0.9, 0.5]
headers = ["ID", "Vendor", "Invoice No.", "Date", "Total", "Currency", "Saved At", "", ""]

header_cols = st.columns(COLS)
for col, label in zip(header_cols, headers):
    col.markdown(f"**{label}**")

st.divider()


# ── One row per invoice ───────────────────────────────────────────────────────
for _, row in df.iterrows():
    inv_id = int(row["id"])
    cols   = st.columns(COLS)

    cols[0].write(str(inv_id))
    cols[1].write(row["vendor_name"]    or "—")
    cols[2].write(row["invoice_number"] or "—")
    cols[3].write(row["invoice_date"]   or "—")
    cols[4].write(row["total_amount"]   or "—")
    cols[5].write(row["currency"]       or "—")
    cols[6].write(row["saved_at"])

    # ── Re-open button ────────────────────────────────────────────────────────
    if cols[7].button("↩ Open", key=f"open_{inv_id}"):
        fields, items_df = load_invoice_by_id(inv_id)

        # Pre-fill session state so app.py renders the form with this data
        st.session_state.fields              = fields
        st.session_state.line_items          = items_df
        st.session_state.raw_text            = "(Loaded from history — original OCR text not available.)"
        st.session_state.loaded_from_history = True
        st.session_state.current_file        = f"history_{inv_id}"
        st.session_state.source_filename     = row.get("source_filename") or "unknown"

        st.switch_page("app.py")

    # ── Delete button (opens confirmation) ────────────────────────────────────
    if cols[8].button("🗑", key=f"del_{inv_id}", help="Delete this record"):
        st.session_state.delete_confirm_id = inv_id
        st.rerun()


# ── Delete confirmation dialog ────────────────────────────────────────────────
confirm_id = st.session_state.delete_confirm_id
if confirm_id is not None:
    st.divider()
    st.warning(
        f"Delete invoice record **#{confirm_id}**? "
        "This also removes its line items and cannot be undone."
    )
    yes_col, no_col, _ = st.columns([1, 1, 5])

    if yes_col.button("Yes, delete", type="primary", key="confirm_yes"):
        delete_invoice(confirm_id)
        st.session_state.delete_confirm_id = None
        st.toast(f"Record #{confirm_id} deleted.")
        st.rerun()

    if no_col.button("Cancel", key="confirm_no"):
        st.session_state.delete_confirm_id = None
        st.rerun()
