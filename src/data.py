"""Small, auditable data-access layer for the Kartify teaching app."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "orders.db"


def connect_read_only(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Open SQLite through a read-only URI and return rows as dictionaries."""
    uri = f"file:{db_path.as_posix()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def list_customer_orders(customer_id: int, db_path: Path = DB_PATH) -> list[dict[str, Any]]:
    """Return orders belonging to one customer, newest first."""
    sql = """
        SELECT order_id, order_date, status, delivery_date, total_amount
        FROM orders
        WHERE customer_id = ?
        ORDER BY order_date DESC
    """
    with connect_read_only(db_path) as connection:
        rows = connection.execute(sql, (customer_id,)).fetchall()
    return [dict(row) for row in rows]


def get_order(order_id: str, db_path: Path = DB_PATH) -> dict[str, Any] | None:
    """Return a fully joined order record, or None when it does not exist."""
    order_sql = """
        SELECT o.order_id, o.order_date, o.status, o.delivery_date,
               o.total_amount, o.shipping_address, o.payment_method,
               o.customer_id, c.name AS customer_name, c.email AS customer_email
        FROM orders AS o
        JOIN customers AS c ON c.customer_id = o.customer_id
        WHERE o.order_id = ?
    """
    item_sql = """
        SELECT oi.product_id, p.name, p.category, p.return_policy,
               p.warranty_period, oi.quantity, oi.price_at_purchase
        FROM order_items AS oi
        JOIN products AS p ON p.product_id = oi.product_id
        WHERE oi.order_id = ?
        ORDER BY p.name
    """
    with connect_read_only(db_path) as connection:
        row = connection.execute(order_sql, (order_id,)).fetchone()
        if row is None:
            return None
        items = [dict(item) for item in connection.execute(item_sql, (order_id,)).fetchall()]
    result = dict(row)
    result["items"] = items
    return result


def customer_owns_order(customer_id: int, order_id: str, db_path: Path = DB_PATH) -> bool:
    """Authorization check: the supplied customer may only see their own order."""
    sql = "SELECT 1 FROM orders WHERE customer_id = ? AND order_id = ?"
    with connect_read_only(db_path) as connection:
        return connection.execute(sql, (customer_id, order_id)).fetchone() is not None


def database_summary(db_path: Path = DB_PATH) -> dict[str, int]:
    """Return row counts used by the instructor and Streamlit dashboard."""
    with connect_read_only(db_path) as connection:
        return {
            table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("customers", "orders", "order_items", "products")
        }

