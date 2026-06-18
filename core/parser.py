import re

# Default empty result so the UI always gets a complete dict
EMPTY_FIELDS: dict[str, str] = {
    "invoice_number": "",
    "invoice_date":   "",
    "vendor_name":    "",
    "total_amount":   "",
    "currency":       "USD",
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
    }


# ── Individual field extractors ───────────────────────────────────────────────

def _find_invoice_number(text: str) -> str:
    patterns = [
        r"invoice\s*(?:no|num|number|#)?\s*[:#.\-]?\s*([A-Z0-9][A-Z0-9\-/]{1,20})",
        r"inv\s*[:#.\-]?\s*([A-Z0-9][A-Z0-9\-/]{1,20})",
        r"#\s*([A-Z0-9\-]{4,20})",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            value = m.group(1).strip()
            if len(value) >= 2:
                return value
    return ""


def _find_date(text: str) -> str:
    patterns = [
        # Labelled date first (most reliable)
        r"(?:invoice\s+)?date\s*[:#.\-]?\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})",
        r"(?:invoice\s+)?date\s*[:#.\-]?\s*(\w+\s+\d{1,2},?\s*\d{4})",
        r"dated?\s*[:#.\-]?\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})",
        # Bare date as fallback
        r"(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return ""


def _find_vendor(text: str) -> str:
    patterns = [
        r"(?:from|bill\s*from|vendor|company|issued\s*by|seller|supplier)\s*[:#.\-]?\s*([^\n]{3,60})",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()

    # Fallback: first non-trivial line that doesn't look like a keyword header
    skip_words = {"invoice", "receipt", "statement", "page", "www", "http", "date", "no.", "#"}
    for line in text.splitlines():
        line = line.strip()
        if len(line) >= 3 and not any(w in line.lower() for w in skip_words):
            return line
    return ""


def _find_total(text: str) -> str:
    # Matches "Total", "Grand Total", "Amount Due", "Balance Due", "Total Due"
    # then an optional currency symbol/code, then digits
    pattern = (
        r"(?:grand\s+total|total\s+amount|amount\s+due|balance\s+due|total\s+due|total)"
        r"\s*[:#.\-]?\s*(?:[A-Z$€£¥]{0,3}\s*)?([\d,]+\.?\d{0,2})"
    )
    matches = re.findall(pattern, text, re.IGNORECASE)
    if matches:
        # Take the last match — grand totals usually appear at the bottom
        return matches[-1].replace(",", "").strip()
    return ""


def _find_currency(text: str) -> str:
    if re.search(r"\bUSD\b|\$", text):
        return "USD"
    if re.search(r"\bEUR\b|€", text):
        return "EUR"
    if re.search(r"\bGBP\b|£", text):
        return "GBP"
    if re.search(r"\bJPY\b|¥", text):
        return "JPY"
    return "USD"
