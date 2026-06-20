import pandas as pd
import plotly.express as px
import streamlit as st

from core.database import init_db, load_all_invoices, load_line_items_all

st.set_page_config(
    page_title="InvoiceIQ – Analytics",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Analytics Dashboard")
st.caption("Spending trends and summaries based on your saved invoices.")

# Ensure DB tables exist (no-op if already created)
init_db()


# ── Load invoices ─────────────────────────────────────────────────────────────

df = load_all_invoices()

if len(df) < 2:
    st.info(
        "Not enough data yet — save at least **2 invoices** to unlock charts and KPIs.  \n"
        "Upload an invoice on the **main page**, fill in the fields, then click "
        "**Save to History**."
    )
    st.stop()


# ── Data preparation ──────────────────────────────────────────────────────────

# Convert total_amount (stored as string) to float; non-numeric rows become NaN
df["amount"] = pd.to_numeric(df["total_amount"], errors="coerce")


# ── Currency label ────────────────────────────────────────────────────────────

unique_currencies = df["currency"].replace("", None).dropna().unique().tolist()

if not unique_currencies:
    currency_lbl = "—"
    is_mixed     = False
elif len(unique_currencies) == 1:
    currency_lbl = unique_currencies[0].upper()
    is_mixed     = False
else:
    currency_lbl = "mixed"
    is_mixed     = True

_MIXED_NOTE = "Sum across all saved currencies — no currency conversion is applied."


# ── KPI helpers ───────────────────────────────────────────────────────────────

def _fmt_amount(value: float) -> str:
    """Format a numeric amount with currency prefix when unambiguous."""
    if pd.isna(value):
        return "—"
    if is_mixed or currency_lbl == "—":
        return f"{value:,.2f}"
    return f"{currency_lbl} {value:,.2f}"


# ── KPI cards ─────────────────────────────────────────────────────────────────

total_sum   = df["amount"].sum(skipna=True)
inv_count   = len(df)
unique_vend = df["vendor_name"].replace("", None).nunique()
avg_invoice = df["amount"].mean(skipna=True)

k1, k2, k3, k4 = st.columns(4)

k1.metric(
    "Total Invoiced",
    _fmt_amount(total_sum),
    help=_MIXED_NOTE if is_mixed else None,
)
k2.metric("Invoice Count",  str(inv_count))
k3.metric("Unique Vendors", str(unique_vend))
k4.metric(
    "Average Invoice",
    _fmt_amount(avg_invoice),
    help=_MIXED_NOTE if is_mixed else None,
)

st.divider()


# ── Shared chart style ────────────────────────────────────────────────────────

_BAR_COLOR = "#4C9BE8"
_CHART_MARGIN = dict(t=10, b=10, l=0, r=0)
_Y_AXIS_LABEL = f"Amount ({currency_lbl})"


# ── Date parser (used for Chart 1) ────────────────────────────────────────────

def _parse_dates(source: pd.DataFrame) -> pd.Series:
    """Parse invoice_date strings to datetime; fall back to saved_at when blank."""
    dates    = pd.to_datetime(source["invoice_date"], errors="coerce", dayfirst=False)
    fallback = pd.to_datetime(source["saved_at"],     errors="coerce")
    return dates.fillna(fallback)


# ── Chart 1 — Monthly Spending ────────────────────────────────────────────────

st.subheader("Monthly Spending")

df["date_parsed"] = _parse_dates(df)

monthly = (
    df.dropna(subset=["date_parsed", "amount"])
    .assign(month=lambda d: d["date_parsed"].dt.to_period("M").dt.to_timestamp())
    .groupby("month", as_index=False)["amount"]
    .sum()
    .rename(columns={"amount": "Total", "month": "Month"})
    .sort_values("Month")
)

if monthly.empty:
    st.caption(
        "No parseable dates — make sure the **Invoice Date** field is filled in "
        "before saving invoices."
    )
else:
    fig1 = px.bar(
        monthly,
        x="Month",
        y="Total",
        labels={"Total": _Y_AXIS_LABEL, "Month": ""},
        color_discrete_sequence=[_BAR_COLOR],
    )
    fig1.update_layout(margin=_CHART_MARGIN)
    st.plotly_chart(fig1, use_container_width=True)

st.divider()


# ── Charts 2 & 3 — side by side ───────────────────────────────────────────────

col_vendors, col_currency = st.columns(2)


# Chart 2 — Top Vendors (horizontal bar) ──────────────────────────────────────

with col_vendors:
    st.subheader("Top Vendors")

    vendors_df = (
        df.dropna(subset=["amount"])
        .assign(vendor=lambda d: d["vendor_name"].replace("", "Unknown"))
        .groupby("vendor", as_index=False)["amount"]
        .sum()
        .sort_values("amount", ascending=False)
        .head(10)
        .rename(columns={"amount": "Total", "vendor": "Vendor"})
    )

    if vendors_df.empty:
        st.caption("No vendor data available yet.")
    else:
        fig2 = px.bar(
            vendors_df,
            x="Total",
            y="Vendor",
            orientation="h",
            labels={"Total": _Y_AXIS_LABEL, "Vendor": ""},
            color_discrete_sequence=[_BAR_COLOR],
        )
        fig2.update_layout(
            yaxis=dict(autorange="reversed"),
            margin=_CHART_MARGIN,
        )
        st.plotly_chart(fig2, use_container_width=True)


# Chart 3 — Currency Breakdown (donut) ────────────────────────────────────────

with col_currency:
    st.subheader("Currency Breakdown")

    curr_counts = df["currency"].replace("", "Unknown").value_counts().reset_index()
    curr_counts.columns = ["Currency", "Count"]

    fig3 = px.pie(
        curr_counts,
        names="Currency",
        values="Count",
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig3.update_layout(margin=_CHART_MARGIN)
    st.plotly_chart(fig3, use_container_width=True)


st.divider()


# ── Chart 4 — Top Line Items by Spend ────────────────────────────────────────

st.subheader("Top Line Items by Spend")

items_df = load_line_items_all()

if items_df.empty:
    st.caption(
        "No line item data yet — line items are saved when you click "
        "**Save to History** on the main page."
    )
else:
    items_df["total"] = pd.to_numeric(items_df["total"], errors="coerce")

    top_items = (
        items_df.dropna(subset=["total"])
        .groupby("description", as_index=False)["total"]
        .sum()
        .sort_values("total", ascending=False)
        .head(10)
        .rename(columns={"total": "Total Spend", "description": "Item"})
    )

    if top_items.empty:
        st.caption("No line item totals available.")
    else:
        fig4 = px.bar(
            top_items,
            x="Item",
            y="Total Spend",
            labels={"Total Spend": _Y_AXIS_LABEL, "Item": ""},
            color_discrete_sequence=[_BAR_COLOR],
        )
        fig4.update_layout(margin=_CHART_MARGIN)
        st.plotly_chart(fig4, use_container_width=True)
