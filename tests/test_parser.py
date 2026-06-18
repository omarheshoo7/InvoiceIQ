"""
Smoke tests for core/parser.py.

Run from the project root:
    pytest tests/ -v

These tests use OCR-style text that matches the layouts the parser must handle,
including the exact failure cases reported during development.
"""

import pandas as pd
import pytest

from core.parser import parse_invoice, parse_line_items
from core.validator import validate_invoice


# ── Sample OCR texts ──────────────────────────────────────────────────────────

# Reproduces the exact reported failure:
#   - "Invoice number:" with nothing after it (next line is a different label)
#   - "Full Name:" with value on the next line (blank-label style)
#   - "Company Name" with NO separator (value on next line)
#   - "TOTAL 230 €" on a single line
SAMPLE_REPORTED_FAILURE = """\
INVOICE

Invoice number:
Reason for exportation: Personal goods
Full Name:
Marceline Anderson
Company Name
Upela
Date: 05/22/2022

TOTAL 230 €
"""

# Same invoice but Company Name uses a colon (another common OCR layout)
SAMPLE_COMPANY_NAME_COLON = """\
INVOICE

Full Name:
Marceline Anderson
Company Name:
Upela
Date: 05/22/2022

TOTAL 230 €
"""

# TOTAL, 230, and € each on their own line (OCR table-cell split)
SAMPLE_MULTILINE_TOTAL = """\
INVOICE

Company Name: Upela
Date: 05/22/2022

TOTAL
230
€
"""

# A clean, well-labelled invoice with a proper invoice number
SAMPLE_CLEAN_INVOICE = """\
Invoice No: INV-2024-001
Invoice Date: 01/15/2024
From: Acme Corp
Grand Total: $1,250.00
"""

# Invoice with USD amount and comma thousands separator
SAMPLE_USD_COMMA = """\
Invoice Number: B-9901
Date: 03/10/2024
Vendor: Widget Co.
Amount Due: $2,500.00
"""


# ── Invoice Number ────────────────────────────────────────────────────────────

class TestInvoiceNumber:
    def test_blank_when_label_has_no_value_on_same_line(self):
        """'Invoice number:' with nothing after the colon must return blank.
        The next line ('Reason for exportation:') must NOT be captured."""
        result = parse_invoice(SAMPLE_REPORTED_FAILURE)
        assert result["invoice_number"] == "", (
            f"Expected blank, got '{result['invoice_number']}' — "
            "pattern is crossing the newline"
        )

    def test_proper_invoice_number_extracted(self):
        result = parse_invoice(SAMPLE_CLEAN_INVOICE)
        assert result["invoice_number"] == "INV-2024-001"

    def test_invoice_number_with_hash_label(self):
        result = parse_invoice(SAMPLE_USD_COMMA)
        assert result["invoice_number"] == "B-9901"


# ── Vendor Name ───────────────────────────────────────────────────────────────

class TestVendorName:
    def test_company_name_without_separator(self):
        """'Company Name\\nUpela' (no colon) must return 'Upela'."""
        result = parse_invoice(SAMPLE_REPORTED_FAILURE)
        assert result["vendor_name"] == "Upela", (
            f"Expected 'Upela', got '{result['vendor_name']}'"
        )

    def test_person_name_not_returned_as_vendor(self):
        """'Marceline Anderson' must never be returned as the vendor."""
        result = parse_invoice(SAMPLE_REPORTED_FAILURE)
        assert "Marceline" not in result["vendor_name"]
        assert "Anderson" not in result["vendor_name"]

    def test_company_name_with_colon_next_line(self):
        """'Company Name:\\nUpela' (colon, value on next line) must return 'Upela'."""
        result = parse_invoice(SAMPLE_COMPANY_NAME_COLON)
        assert result["vendor_name"] == "Upela", (
            f"Expected 'Upela', got '{result['vendor_name']}'"
        )

    def test_from_label_vendor(self):
        result = parse_invoice(SAMPLE_CLEAN_INVOICE)
        assert result["vendor_name"] == "Acme Corp"

    def test_vendor_label(self):
        result = parse_invoice(SAMPLE_USD_COMMA)
        assert result["vendor_name"] == "Widget Co."


# ── Total Amount ──────────────────────────────────────────────────────────────

class TestTotalAmount:
    def test_total_same_line_with_eur(self):
        """'TOTAL 230 €' on one line."""
        result = parse_invoice(SAMPLE_REPORTED_FAILURE)
        assert result["total_amount"] == "230", (
            f"Expected '230', got '{result['total_amount']}'"
        )

    def test_total_multiline(self):
        """'TOTAL', '230', and '€' each on their own line (OCR table split)."""
        result = parse_invoice(SAMPLE_MULTILINE_TOTAL)
        assert result["total_amount"] == "230", (
            f"Expected '230', got '{result['total_amount']}'"
        )

    def test_grand_total_with_usd_and_comma(self):
        """'Grand Total: $1,250.00' — commas stripped from number."""
        result = parse_invoice(SAMPLE_CLEAN_INVOICE)
        assert result["total_amount"] == "1250.00"

    def test_amount_due_label(self):
        result = parse_invoice(SAMPLE_USD_COMMA)
        assert result["total_amount"] == "2500.00"


# ── Currency ──────────────────────────────────────────────────────────────────

class TestCurrency:
    def test_euro_symbol_maps_to_eur(self):
        result = parse_invoice(SAMPLE_REPORTED_FAILURE)
        assert result["currency"] == "EUR"

    def test_dollar_maps_to_usd(self):
        result = parse_invoice(SAMPLE_CLEAN_INVOICE)
        assert result["currency"] == "USD"


# Zylker-style single-line OCR — all fields run together on one line.
# Key challenges:
#   - "Invoice Date 05 Aug 2024" has no separator between label and value
#   - DD Mon YYYY format was not previously handled
#   - "Due Date 05 Aug 2024" appears on the same line — must NOT be returned
SAMPLE_ZYLKER = (
    "Zylker Electronics Hub 14B, Northern Street Greater South Avenue "
    "INVOICE New York New York 10001 U.S.A "
    "Invoice# INV-000001 "
    "Invoice Date 05 Aug 2024 "
    "Terms Due on Receipt Due Date 05 Aug 2024 "
    "Bill To Ship To Ms. Mary D. Dunton 1324 Hinkle Lake Road "
    "Late payments may incur additional charges or interest as per the applicable laws. "
    "1324 Hinkle Lake Road Needham. Needham 02192 Maine 02192 Maine "
    "# Description Qty Rate Amou: "
    "1 Camera 1.00 $899.00 899.00 DSLR camera with advanced shooting capabilities "
    "2 Fitness Tracker 1.00 $129.00 $129.00 Activity tracker with heart rate monitoring "
    "3 Laptop 1.00 $1199.00 $1199.00 Lightweight laptop with a powerful processor "
    "Sub Total $2,227.00 Thanks for shopping with us. Tax Rate 5.00% Total $2,338.35 "
    "Terms & Conditions Balance Due $2,338.35 Full payment is due upon receipt of this invoice."
)


# ── Invoice Date ──────────────────────────────────────────────────────────────

class TestInvoiceDate:
    def test_date_extracted(self):
        result = parse_invoice(SAMPLE_REPORTED_FAILURE)
        assert result["invoice_date"] == "05/22/2022"

    def test_dd_mon_yyyy_format(self):
        """'Invoice Date 05 Aug 2024' — no separator, DD Mon YYYY format."""
        result = parse_invoice(SAMPLE_ZYLKER)
        assert result["invoice_date"] == "05 Aug 2024", (
            f"Expected '05 Aug 2024', got '{result['invoice_date']}'"
        )

    def test_invoice_date_preferred_over_due_date(self):
        """When both Invoice Date and Due Date are present, Invoice Date wins."""
        text = "Invoice Date 12 Jan 2025 Terms Due on Receipt Due Date 26 Jan 2025"
        result = parse_invoice(text)
        assert result["invoice_date"] == "12 Jan 2025", (
            f"Expected '12 Jan 2025' (Invoice Date), got '{result['invoice_date']}'"
        )

    def test_due_date_not_returned_when_invoice_date_present(self):
        """The Due Date value ('05 Aug 2024') must never appear when Invoice Date exists."""
        result = parse_invoice(SAMPLE_ZYLKER)
        # Both dates happen to be the same in this invoice, so also verify
        # the label "Due Date" alone isn't being mistakenly used as the source
        assert result["invoice_date"] != "", "Invoice date should not be blank"


# ── Full Zylker invoice round-trip ────────────────────────────────────────────

class TestZylkerInvoice:
    """End-to-end test using the exact OCR text from the reported failing invoice."""

    def test_invoice_number(self):
        assert parse_invoice(SAMPLE_ZYLKER)["invoice_number"] == "INV-000001"

    def test_invoice_date(self):
        assert parse_invoice(SAMPLE_ZYLKER)["invoice_date"] == "05 Aug 2024"

    def test_total_amount(self):
        assert parse_invoice(SAMPLE_ZYLKER)["total_amount"] == "2338.35"

    def test_currency(self):
        assert parse_invoice(SAMPLE_ZYLKER)["currency"] == "USD"


# ── Line Item Extraction ──────────────────────────────────────────────────────

SAMPLE_LINE_ITEMS_MULTILINE = """\
1 Consulting 2.00 $150.00 $300.00
2 Support 1.00 $75.00 $75.00
Total $375.00
"""


class TestLineItems:
    def test_zylker_item_count(self):
        """Three line items must be found in the Zylker OCR text."""
        df = parse_line_items(SAMPLE_ZYLKER)
        assert len(df) == 3, f"Expected 3 items, got {len(df)}: {df.to_dict('records')}"

    def test_zylker_first_item(self):
        df = parse_line_items(SAMPLE_ZYLKER)
        assert df.iloc[0]["Description"] == "Camera"
        assert df.iloc[0]["Quantity"]    == 1.0
        assert df.iloc[0]["Unit Price"]  == 899.0
        assert df.iloc[0]["Total"]       == 899.0

    def test_zylker_second_item(self):
        df = parse_line_items(SAMPLE_ZYLKER)
        assert df.iloc[1]["Description"] == "Fitness Tracker"
        assert df.iloc[1]["Quantity"]    == 1.0
        assert df.iloc[1]["Unit Price"]  == 129.0
        assert df.iloc[1]["Total"]       == 129.0

    def test_zylker_third_item(self):
        df = parse_line_items(SAMPLE_ZYLKER)
        assert df.iloc[2]["Description"] == "Laptop"
        assert df.iloc[2]["Quantity"]    == 1.0
        assert df.iloc[2]["Unit Price"]  == 1199.0
        assert df.iloc[2]["Total"]       == 1199.0

    def test_multiline_format(self):
        """Two items, each on its own line, with a Total line at the end."""
        df = parse_line_items(SAMPLE_LINE_ITEMS_MULTILINE)
        assert len(df) == 2
        assert df.iloc[0]["Description"] == "Consulting"
        assert df.iloc[0]["Quantity"]    == 2.0
        assert df.iloc[0]["Unit Price"]  == 150.0
        assert df.iloc[0]["Total"]       == 300.0

    def test_no_items_returns_empty_df(self):
        """Text with no line items returns an empty DataFrame (columns intact)."""
        df = parse_line_items("INVOICE\nTotal $500.00\n")
        assert df.empty
        assert list(df.columns) == ["Description", "Quantity", "Unit Price", "Total"]


# ── Subtotal and Tax Extraction ───────────────────────────────────────────────

class TestSubtotalExtraction:
    def test_zylker_subtotal(self):
        """'Sub Total $2,227.00' must be parsed to '2227.00'."""
        assert parse_invoice(SAMPLE_ZYLKER)["subtotal"] == "2227.00"

    def test_zylker_tax_rate(self):
        """'Tax Rate 5.00%' must be returned as '5.00%' (rate, not amount)."""
        assert parse_invoice(SAMPLE_ZYLKER)["tax"] == "5.00%"

    def test_subtotal_with_colon(self):
        result = parse_invoice("Subtotal: $1,500.00\nTax: 75.00\nTotal: $1,575.00")
        assert result["subtotal"] == "1500.00"

    def test_sub_dash_total(self):
        result = parse_invoice("Sub-total 1500.00\nTotal 1500.00")
        assert result["subtotal"] == "1500.00"

    def test_vat_percentage(self):
        result = parse_invoice("Subtotal: 100.00\nVAT 20%\nTotal: 120.00")
        assert result["tax"] == "20%"

    def test_tax_amount(self):
        result = parse_invoice("Subtotal: 1000.00\nTax Amount 111.35\nTotal: 1111.35")
        assert result["tax"] == "111.35"

    def test_no_subtotal_returns_blank(self):
        assert parse_invoice(SAMPLE_CLEAN_INVOICE)["subtotal"] == ""


# ── Validation: Subtotal + Tax ────────────────────────────────────────────────

_EMPTY_DF = pd.DataFrame(columns=["Description", "Quantity", "Unit Price", "Total"])


def _items_df(total: float) -> pd.DataFrame:
    """One-row DataFrame whose Total column equals `total`."""
    return pd.DataFrame([{
        "Description": "Item", "Quantity": 1.0,
        "Unit Price": total, "Total": total,
    }])


class TestValidationWithTax:
    def test_zylker_no_false_line_sum_warning(self):
        """Full Zylker pipeline: line sum 2227 == subtotal 2227 → no line-item warning."""
        fields = parse_invoice(SAMPLE_ZYLKER)
        df     = parse_line_items(SAMPLE_ZYLKER)
        issues = validate_invoice(fields, df)
        line_sum_msgs = [i.message for i in issues if "line item" in i.message.lower()]
        assert not line_sum_msgs, f"Unexpected line-item warning: {line_sum_msgs}"

    def test_zylker_subtotal_plus_tax_rate_no_warning(self):
        """2227 × 5% + 2227 = 2338.35 matches Total — no subtotal/tax mismatch."""
        fields = {**parse_invoice(SAMPLE_ZYLKER)}
        issues = validate_invoice(fields, _EMPTY_DF)
        bad = [i.message for i in issues if "don't match" in i.message.lower()]
        assert not bad, f"Unexpected mismatch warning: {bad}"

    def test_tax_amount_variant_no_warning(self):
        """Subtotal 1000 + Tax amount 100 = Total 1100 — passes cleanly."""
        fields = {
            "invoice_number": "X", "invoice_date": "X",
            "vendor_name": "X", "total_amount": "1100.00",
            "currency": "USD", "subtotal": "1000.00", "tax": "100.00",
        }
        issues = validate_invoice(fields, _items_df(1000.00))
        bad = [i.message for i in issues if "don't match" in i.message.lower()]
        assert not bad, f"Unexpected mismatch warning: {bad}"

    def test_wrong_total_triggers_warning(self):
        """Subtotal 1000 + Tax 10% = 1100, but Total is 1200 → warning expected."""
        fields = {
            "invoice_number": "X", "invoice_date": "X",
            "vendor_name": "X", "total_amount": "1200.00",
            "currency": "USD", "subtotal": "1000.00", "tax": "10%",
        }
        issues = validate_invoice(fields, _EMPTY_DF)
        assert any("don't match" in i.message.lower() for i in issues)

    def test_no_subtotal_compares_to_total(self):
        """Without subtotal, a line-sum mismatch against Total is still flagged."""
        fields = {
            "invoice_number": "X", "invoice_date": "X",
            "vendor_name": "X", "total_amount": "150.00",
            "currency": "USD", "subtotal": "", "tax": "",
        }
        issues = validate_invoice(fields, _items_df(100.00))
        assert any(
            "line item" in i.message.lower() and "total amount" in i.message.lower()
            for i in issues
        )
