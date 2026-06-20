import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

DB_PATH = Path("data") / "invoices.db"


# ── Setup ─────────────────────────────────────────────────────────────────────

def init_db() -> None:
    """Create the database and tables if they don't already exist.
    Safe to call on every app start — uses IF NOT EXISTS."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = _connect()
    conn.executescript("""
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS invoices (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            saved_at         TEXT    NOT NULL,
            source_filename  TEXT,
            invoice_number   TEXT,
            invoice_date     TEXT,
            vendor_name      TEXT,
            total_amount     TEXT,
            currency         TEXT,
            subtotal         TEXT,
            tax              TEXT
        );

        CREATE TABLE IF NOT EXISTS line_items (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id   INTEGER NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
            description  TEXT,
            quantity     REAL,
            unit_price   REAL,
            total        REAL
        );
    """)
    conn.commit()
    conn.close()


# ── Write operations ──────────────────────────────────────────────────────────

def save_invoice(fields: dict, line_items_df: pd.DataFrame, source_filename: str) -> int:
    """
    Insert one invoice record (header fields + all line items) into the DB.
    Returns the new row's id so the caller can show it to the user.
    """
    conn = _connect()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO invoices
            (saved_at, source_filename, invoice_number, invoice_date,
             vendor_name, total_amount, currency, subtotal, tax)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            source_filename or "",
            fields.get("invoice_number", ""),
            fields.get("invoice_date",   ""),
            fields.get("vendor_name",    ""),
            fields.get("total_amount",   ""),
            fields.get("currency",       ""),
            fields.get("subtotal",       ""),
            fields.get("tax",            ""),
        ),
    )
    invoice_id = cursor.lastrowid

    if line_items_df is not None and not line_items_df.empty:
        for _, row in line_items_df.iterrows():
            cursor.execute(
                """
                INSERT INTO line_items (invoice_id, description, quantity, unit_price, total)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    invoice_id,
                    str(row.get("Description") or ""),
                    _to_float(row.get("Quantity")),
                    _to_float(row.get("Unit Price")),
                    _to_float(row.get("Total")),
                ),
            )

    conn.commit()
    conn.close()
    return invoice_id


def delete_invoice(invoice_id: int) -> None:
    """Delete an invoice and its line items.
    The ON DELETE CASCADE on line_items handles child rows automatically."""
    conn = _connect()
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("DELETE FROM invoices WHERE id = ?", (invoice_id,))
    conn.commit()
    conn.close()


# ── Read operations ───────────────────────────────────────────────────────────

def load_all_invoices() -> pd.DataFrame:
    """Return all invoices as a DataFrame, newest first."""
    conn = _connect()
    df = pd.read_sql_query(
        """
        SELECT id, saved_at, source_filename, invoice_number,
               invoice_date, vendor_name, total_amount, currency
        FROM invoices
        ORDER BY saved_at DESC
        """,
        conn,
    )
    conn.close()
    return df


def search_invoices(query: str) -> pd.DataFrame:
    """Filter invoices by vendor name or invoice number (case-insensitive)."""
    conn = _connect()
    like = f"%{query.lower()}%"
    df = pd.read_sql_query(
        """
        SELECT id, saved_at, source_filename, invoice_number,
               invoice_date, vendor_name, total_amount, currency
        FROM invoices
        WHERE LOWER(vendor_name) LIKE ? OR LOWER(invoice_number) LIKE ?
        ORDER BY saved_at DESC
        """,
        conn,
        params=(like, like),
    )
    conn.close()
    return df


def load_line_items_all() -> pd.DataFrame:
    """Return every saved line item joined with its invoice's vendor, date, and currency.

    Useful for the analytics dashboard — callers can group by description,
    vendor, or month without needing a separate join.
    """
    conn = _connect()
    df = pd.read_sql_query(
        """
        SELECT li.description,
               li.quantity,
               li.unit_price,
               li.total,
               i.vendor_name,
               i.invoice_date,
               i.currency,
               i.saved_at
        FROM   line_items li
        JOIN   invoices   i  ON li.invoice_id = i.id
        ORDER  BY i.saved_at DESC
        """,
        conn,
    )
    conn.close()
    return df


def load_invoice_by_id(invoice_id: int) -> tuple[dict, pd.DataFrame]:
    """
    Load one invoice's fields and line items by primary key.
    Returns (fields_dict, line_items_df).
    """
    conn = _connect()

    row = conn.execute(
        "SELECT * FROM invoices WHERE id = ?", (invoice_id,)
    ).fetchone()

    fields: dict = {}
    if row:
        fields = {
            "invoice_number": row["invoice_number"] or "",
            "invoice_date":   row["invoice_date"]   or "",
            "vendor_name":    row["vendor_name"]    or "",
            "total_amount":   row["total_amount"]   or "",
            "currency":       row["currency"]       or "USD",
            "subtotal":       row["subtotal"]       or "",
            "tax":            row["tax"]            or "",
        }

    rows = conn.execute(
        "SELECT description, quantity, unit_price, total "
        "FROM line_items WHERE invoice_id = ? ORDER BY id",
        (invoice_id,),
    ).fetchall()

    if rows:
        line_items_df = pd.DataFrame(
            [(r["description"], r["quantity"], r["unit_price"], r["total"]) for r in rows],
            columns=["Description", "Quantity", "Unit Price", "Total"],
        )
    else:
        line_items_df = pd.DataFrame(
            columns=["Description", "Quantity", "Unit Price", "Total"]
        )

    conn.close()
    return fields, line_items_df


# ── Internal helpers ──────────────────────────────────────────────────────────

def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _to_float(value) -> float | None:
    """Convert a cell value to float, returning None for missing/NaN."""
    if value is None:
        return None
    try:
        f = float(value)
        return None if pd.isna(f) else f
    except (ValueError, TypeError):
        return None
