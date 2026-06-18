import re

import pandas as pd

EMPTY_FIELDS: dict[str, str] = {
    "invoice_number": "",
    "invoice_date":   "",
    "vendor_name":    "",
    "total_amount":   "",
    "currency":       "USD",
    "subtotal":       "",
    "tax":            "",
}


def parse_invoice(text: str) -> dict[str, str]:
    """
    Parse raw invoice text with regex and return a dict of fields.
    All values are strings; empty string means "not found".
    """
    return {
        "invoice_number": _find_invoice_number(text),
        "invoice_date":   _find_date(text),
        "vendor_name":    _find_vendor(text),
        "total_amount":   _find_total(text),
        "currency":       _find_currency(text),
        "subtotal":       _find_subtotal(text),
        "tax":            _find_tax(text),
    }


# ── Individual field extractors ───────────────────────────────────────────────

def _find_invoice_number(text: str) -> str:
    # [^\S\n]* after the separator means "any horizontal whitespace, but NOT a newline".
    # This keeps the capture group on the same line as the label, preventing the
    # pattern from jumping to the next line when the value is blank, e.g.:
    #   "Invoice number:\nReason for exportation:" → should return ""
    patterns = [
        r"invoice\s*(?:no|num|number)\s*[:#.\-][^\S\n]*([A-Z0-9][A-Z0-9\-/]{0,30})",
        r"invoice\s*#[^\S\n]*([A-Z0-9][A-Z0-9\-/]{0,30})",
        r"\bINV\s*[:#\-][^\S\n]*([A-Z0-9][A-Z0-9\-/]{0,30})",
        r"(?<!\w)#[^\S\n]*([A-Z0-9]{4,20})",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            value = m.group(1).strip()
            if len(value) >= 1:
                return value
    return ""


def _find_date(text: str) -> str:
    # Step 1 — try all "Invoice Date" patterns first.
    # This guarantees Invoice Date is returned even when Due Date also
    # appears later in the same line (common in single-line OCR output).
    invoice_date_patterns = [
        # "Invoice Date 05 Aug 2024" — no separator, DD Mon YYYY
        # This is the format produced by many digital-PDF invoices (e.g. Zylker).
        r"invoice\s+date\s*[:#.\-]?\s*(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})",
        # "Invoice Date: 05/22/2022" — with separator, numeric MM/DD/YYYY
        r"invoice\s+date\s*[:#.\-]?\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})",
        # "Invoice Date: August 05, 2024" — written month, Mon DD YYYY
        r"invoice\s+date\s*[:#.\-]?\s*([A-Za-z]{3,9}\s+\d{1,2},?\s*\d{4})",
    ]
    for pattern in invoice_date_patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()

    # Step 2 — generic "Date" patterns that explicitly skip "Due Date" context.
    # re.finditer lets us inspect what comes before each match and reject it
    # when "due" appears within 5 characters before the word "date".
    generic_date_patterns = [
        r"\bdate\s*[:#.\-]?\s*(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})",
        r"\bdate\s*[:#.\-]?\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})",
        r"\bdated?\s*[:#.\-]\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})",
    ]
    for pattern in generic_date_patterns:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            preceding = text[max(0, m.start() - 5): m.start()].lower()
            if "due" not in preceding:
                return m.group(1).strip()

    # Step 3 — bare numeric date, last resort
    m = re.search(r"(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})", text)
    if m:
        return m.group(1).strip()

    return ""


def _find_vendor(text: str) -> str:
    # Patterns are ordered from most specific to least specific.
    #
    # Three "Company Name" variants are listed to cover all common OCR layouts:
    #   • "Company Name: Upela"    — label and value on the same line
    #   • "Company Name:\nUpela"   — separator at end of label line, value on next
    #   • "Company Name\nUpela"    — no separator at all, value on the next line
    #
    # The first pattern already handles both the same-line AND the next-line-with-
    # separator case because \s* after the colon matches a newline character.
    # The third pattern explicitly handles the no-separator next-line case.
    patterns = [
        # Same line or next-line via \s* crossing the newline
        r"company\s+name\s*[:#.\-]\s*([^\n]{2,60})",
        # No separator: "Company Name\nUpela"
        r"company\s+name[^\S\n]*\n[^\S\n]*([^\n]{2,60})",
        # "Bill From: Upela" or "From: Upela"
        r"(?:bill\s+from|from)\s*[:#.\-]\s*([^\n]{3,60})",
        # "FROM" on its own line; vendor name on the next non-empty line
        r"(?:^|\n)[^\S\n]*from[^\S\n]*\n[^\S\n]*([^\n]{3,60})",
        # "Vendor:", "Seller:", "Supplier:", "Issued by:"
        r"(?:vendor|seller|supplier|issued\s+by)\s*[:#.\-]\s*([^\n]{3,60})",
        # "Company: Upela"
        r"\bcompany\s*[:#]\s*([^\n]{3,60})",
    ]

    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if m:
            value = m.group(1).strip()
            # Reject captured values that themselves look like bare labels ("Name:", "Address:")
            if value and not re.match(r'^[A-Za-z\s]{1,20}\s*:', value) and len(value) >= 2:
                return value

    # ── Fallback: scan lines, skipping field labels and their values ──────────
    # When a line is a blank label ("Label:") with nothing after the colon, the
    # value is on the NEXT line. We must skip that next line too, or we risk
    # returning a personal name (e.g., "Marceline Anderson" after "Full Name:").
    skip_words = {
        "invoice", "receipt", "statement", "page", "www", "http",
        "date", "no.", "#", "name", "full", "email", "address",
        "tel", "phone", "fax", "from", "to", "bill", "attn",
    }
    skip_next = False

    for line in text.splitlines():
        stripped = line.strip()

        if not stripped:
            skip_next = False
            continue

        # Previous line was a blank label — this line is its value, skip it
        if skip_next:
            skip_next = False
            continue

        lower = stripped.lower()

        # "Label:" with nothing after the colon → mark the next line to be skipped
        if re.match(r'^[A-Za-z][\w\s]{0,24}\s*:\s*$', stripped):
            skip_next = True
            continue

        # "Label: value" on the same line → skip only this line
        if re.match(r'^[A-Za-z][\w\s]{0,24}\s*:\s*\S', stripped):
            continue

        if any(w in lower for w in skip_words):
            continue

        if len(stripped) >= 3:
            return stripped

    return ""


def _find_total(text: str) -> str:
    # Line-by-line scanner, reading from the bottom up.
    #
    # Scanning bottom-up means we find the grand total (usually at the end
    # of the document) before any "Total" column headers earlier in the page.
    #
    # For each matching line we first try to extract a number from that same
    # line; if there is none (the OCR split the row across lines), we look at
    # the following 1-3 lines. This handles all known OCR layouts:
    #   "TOTAL 230 €"       → number on same line
    #   "TOTAL\n230\n€"     → number on the next line
    #   "TOTAL:\n\n230"     → number two lines below
    lines = text.splitlines()

    total_label = re.compile(
        r"(?:grand\s+total|total\s+amount|amount\s+due|balance\s+due|total\s+due|\btotal\b)",
        re.IGNORECASE,
    )
    number_re = re.compile(r"([\d,]+\.?\d{0,2})")

    for i in range(len(lines) - 1, -1, -1):
        if not total_label.search(lines[i]):
            continue

        # Try the same line first
        nums = number_re.findall(lines[i])
        if nums:
            return nums[-1].replace(",", "")

        # Look ahead up to 3 lines for the number
        for j in range(1, 4):
            if i + j < len(lines):
                m = number_re.search(lines[i + j].strip())
                if m:
                    return m.group(1).replace(",", "")

    return ""


# ── Line item extraction ──────────────────────────────────────────────────────

# Each token must satisfy:
#   • Item number: 1–2 digits NOT preceded by another digit (avoids 1324, 10001…)
#   • Description: starts with a letter, only letters/spaces, lazy 1–50 chars
#     (digits in descriptions are excluded intentionally — they cause false matches)
#   • Quantity: integer or decimal
#   • Unit price and total: MUST have exactly 2 decimal places (.NN) — this is
#     the strong false-positive filter; bare integers like "10001" never match.
_ITEM_PATTERN = re.compile(
    r"(?<!\d)(\d{1,2})"            # item number
    r"\s+"
    r"([A-Za-z][A-Za-z\s]{1,50}?)" # description (letters/spaces only, lazy)
    r"\s+"
    r"(\d+(?:\.\d{1,4})?)"         # quantity
    r"\s+"
    r"[$€£¥]?"                     # optional currency before unit price
    r"([\d,]+\.\d{2})"             # unit price (exactly 2 decimal places)
    r"\s+"
    r"[$€£¥]?"                     # optional currency before total
    r"([\d,]+\.\d{2})",            # total (exactly 2 decimal places)
    re.MULTILINE,
)


def parse_line_items(text: str) -> pd.DataFrame:
    """Extract line items from invoice text.

    Returns a DataFrame with columns: Description, Quantity, Unit Price, Total.
    If no items are detected the DataFrame is empty (columns present, no rows).
    """
    rows = []
    for m in _ITEM_PATTERN.finditer(text):
        desc = m.group(2).strip()
        if len(desc) < 2:
            continue
        rows.append({
            "Description": desc,
            "Quantity":    float(m.group(3)),
            "Unit Price":  float(m.group(4).replace(",", "")),
            "Total":       float(m.group(5).replace(",", "")),
        })
    if not rows:
        return pd.DataFrame(columns=["Description", "Quantity", "Unit Price", "Total"])
    return pd.DataFrame(rows)


def _find_subtotal(text: str) -> str:
    # Matches "Sub Total", "Subtotal", "Sub-total" with optional separator and currency symbol.
    m = re.search(
        r"sub[\s\-]*total\s*[:#]?\s*[$€£¥]?([\d,]+\.?\d{0,2})",
        text, re.IGNORECASE,
    )
    if m:
        return m.group(1).strip().replace(",", "")
    return ""


def _find_tax(text: str) -> str:
    # Priority: percentage rates first (unambiguous), then named-amount variants,
    # then a bare "Tax X" amount last (broadest, most likely to false-match).
    # A rate is returned as "X%" so the validator can distinguish it from an amount.

    # 1. "Tax Rate 5.00%"
    m = re.search(r"tax\s+rate\s*[:#]?\s*([\d.]+)\s*%", text, re.IGNORECASE)
    if m:
        return m.group(1).strip() + "%"

    # 2. "VAT 14%" or "VAT Rate 14%"
    m = re.search(r"\bvat\b\s*(?:rate)?\s*[:#]?\s*([\d.]+)\s*%", text, re.IGNORECASE)
    if m:
        return m.group(1).strip() + "%"

    # 3. "Tax Amount 111.35" or "Tax: 111.35" or "Tax 111.35" (not followed by %)
    m = re.search(
        r"\btax\s*(?:amount)?\s*[:#]?\s*[$€£¥]?([\d,]+\.?\d{0,2})(?!\s*%)",
        text, re.IGNORECASE,
    )
    if m:
        return m.group(1).strip().replace(",", "")

    # 4. "VAT Amount 111.35"
    m = re.search(
        r"\bvat\s+amount\s*[:#]?\s*[$€£¥]?([\d,]+\.?\d{0,2})(?!\s*%)",
        text, re.IGNORECASE,
    )
    if m:
        return m.group(1).strip().replace(",", "")

    return ""


def _find_currency(text: str) -> str:
    # ISO codes are checked before symbols to reduce ambiguity.
    # EUR/€ is checked before USD/$ because "$" appears in many non-financial
    # contexts (code, comments) and is more likely to be a false positive.
    if re.search(r"\bEGP\b", text):
        return "EGP"
    if re.search(r"\bEUR\b|€", text):
        return "EUR"
    if re.search(r"\bGBP\b|£", text):
        return "GBP"
    if re.search(r"\bJPY\b|¥", text):
        return "JPY"
    if re.search(r"\bUSD\b|\$", text):
        return "USD"
    return "USD"
