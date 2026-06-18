from dataclasses import dataclass

import pandas as pd

TOLERANCE = 0.01  # 1-cent tolerance for float comparisons


@dataclass
class ValidationIssue:
    level: str    # "error" | "warning"
    message: str


def validate_invoice(fields: dict, line_items_df: pd.DataFrame) -> list[ValidationIssue]:
    """
    Run all validation checks against the current invoice data.
    Returns a list of ValidationIssue objects (may be empty if everything looks good).
    Never raises — all errors are caught and reported as issues.
    """
    issues: list[ValidationIssue] = []

    _check_required_fields(fields, issues)
    _check_total_amount(fields, issues)
    _check_subtotal_tax(fields, issues)
    _check_line_item_row_totals(line_items_df, issues)
    _check_line_items_sum_vs_total(fields, line_items_df, issues)
    _check_empty_line_items(line_items_df, issues)

    return issues


# ── Individual checks ─────────────────────────────────────────────────────────

def _check_required_fields(fields: dict, issues: list[ValidationIssue]) -> None:
    required = [
        ("invoice_number", "Invoice Number"),
        ("invoice_date",   "Invoice Date"),
        ("vendor_name",    "Vendor Name"),
        ("total_amount",   "Total Amount"),
    ]
    for key, label in required:
        if not fields.get(key, "").strip():
            issues.append(ValidationIssue("warning", f"{label} is missing."))


def _check_total_amount(fields: dict, issues: list[ValidationIssue]) -> None:
    total_str = fields.get("total_amount", "").strip()
    if not total_str:
        return  # Already caught by _check_required_fields

    try:
        total = float(total_str.replace(",", ""))
    except ValueError:
        issues.append(ValidationIssue(
            "error",
            f"Total Amount '{total_str}' is not a valid number.",
        ))
        return

    if total < 0:
        issues.append(ValidationIssue(
            "error",
            f"Total Amount is negative ({total_str}). Please verify.",
        ))
    elif total == 0:
        issues.append(ValidationIssue(
            "warning",
            "Total Amount is zero — is this intentional?",
        ))


def _check_subtotal_tax(fields: dict, issues: list[ValidationIssue]) -> None:
    """Validate Subtotal + Tax ≈ Total when all three are available.

    Tax may be stored as an amount ("111.35") or a rate ("5.00%").
    When it is a rate, the expected tax amount is derived from Subtotal × rate.
    """
    subtotal_str = fields.get("subtotal", "").strip()
    tax_str      = fields.get("tax", "").strip()
    total_str    = fields.get("total_amount", "").strip()

    if not (subtotal_str and tax_str and total_str):
        return

    try:
        subtotal = float(subtotal_str.replace(",", ""))
        total    = float(total_str.replace(",", ""))
    except ValueError:
        return

    # Determine the tax amount — either direct value or derived from a percentage rate
    if tax_str.endswith("%"):
        try:
            rate       = float(tax_str.rstrip("%").strip()) / 100
            tax_amount = subtotal * rate
        except ValueError:
            return
    else:
        try:
            tax_amount = float(tax_str.replace(",", ""))
        except ValueError:
            return

    expected = subtotal + tax_amount
    if abs(expected - total) > TOLERANCE:
        issues.append(ValidationIssue(
            "warning",
            f"Subtotal ({subtotal_str}) + Tax ({tax_str}) = {expected:.2f}, "
            f"but Total Amount is {total_str}. They don't match.",
        ))


def _check_line_item_row_totals(df: pd.DataFrame, issues: list[ValidationIssue]) -> None:
    """Each row: Quantity × Unit Price should equal the Total column."""
    if df is None or df.empty:
        return

    for row_num, (_, row) in enumerate(df.iterrows(), start=1):
        qty   = row.get("Quantity")
        price = row.get("Unit Price")
        total = row.get("Total")

        # Skip if any of the three values is missing
        if pd.isna(qty) or pd.isna(price) or pd.isna(total):
            continue

        try:
            expected = float(qty) * float(price)
            actual   = float(total)
        except (ValueError, TypeError):
            continue

        if abs(expected - actual) > TOLERANCE:
            issues.append(ValidationIssue(
                "warning",
                f"Line item {row_num}: {qty} × {price:.2f} = {expected:.2f}, "
                f"but the Total column shows {actual:.2f}.",
            ))


def _check_line_items_sum_vs_total(
    fields: dict, df: pd.DataFrame, issues: list[ValidationIssue]
) -> None:
    """Line item sum should match the Subtotal (when present) or the Invoice Total.

    When a Subtotal field is filled, tax has already been excluded from the line
    items — so comparing the sum to the grand Total would always trigger a false
    warning.  In that case we compare against Subtotal instead and return early.
    """
    if df is None or df.empty:
        return

    line_totals = pd.to_numeric(df.get("Total", pd.Series(dtype=float)), errors="coerce")
    line_sum    = line_totals.sum()

    if line_sum == 0:
        return  # Nothing entered — nothing to compare

    subtotal_str = fields.get("subtotal", "").strip()

    if subtotal_str:
        # Subtotal is the correct anchor when tax is separate from line items
        try:
            subtotal = float(subtotal_str.replace(",", ""))
        except ValueError:
            return
        if abs(line_sum - subtotal) > TOLERANCE:
            issues.append(ValidationIssue(
                "warning",
                f"Sum of line item Totals ({line_sum:.2f}) does not match "
                f"Subtotal ({subtotal_str}).",
            ))
        return  # Don't also check against grand total

    # No subtotal — fall back to comparing against the grand total
    total_str = fields.get("total_amount", "").strip()
    if not total_str:
        return

    try:
        invoice_total = float(total_str.replace(",", ""))
    except ValueError:
        return

    if abs(line_sum - invoice_total) > TOLERANCE:
        issues.append(ValidationIssue(
            "warning",
            f"Sum of line item Totals ({line_sum:.2f}) does not match "
            f"Invoice Total Amount ({total_str}).",
        ))


def _check_empty_line_items(df: pd.DataFrame, issues: list[ValidationIssue]) -> None:
    """Flag rows that are completely empty or only partially filled."""
    if df is None or df.empty:
        return

    fully_empty_count = 0

    for row_num, (_, row) in enumerate(df.iterrows(), start=1):
        desc      = str(row.get("Description") or "").strip()
        has_nums  = any(
            pd.notna(row.get(col)) and row.get(col) != 0
            for col in ["Quantity", "Unit Price", "Total"]
        )

        if not desc and not has_nums:
            fully_empty_count += 1
            continue

        # Has numeric data but is missing a description
        if not desc and has_nums:
            issues.append(ValidationIssue(
                "warning",
                f"Line item {row_num} has values but no description.",
            ))

    if fully_empty_count > 0:
        issues.append(ValidationIssue(
            "warning",
            f"{fully_empty_count} completely empty row(s) found in line items. "
            "Remove them before exporting for a clean file.",
        ))
