"""Allowlisted, read-only domain tools over the teaching SQLite database."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


DB_PATH = Path(__file__).resolve().parents[1] / "data" / "orders.db"


def connect_read_only(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Open SQLite in read-only mode and return rows as dictionaries."""
    connection = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def list_customers(db_path: Path = DB_PATH) -> list[dict[str, Any]]:
    """Return safe demo identities; real authentication belongs outside chat."""
    with connect_read_only(db_path) as connection:
        rows = connection.execute(
            "SELECT customer_id, name FROM customers ORDER BY customer_id"
        ).fetchall()
    return [dict(row) for row in rows]


def get_customer(customer_id: int, db_path: Path = DB_PATH) -> dict[str, Any] | None:
    """Resolve a customer profile for session context."""
    with connect_read_only(db_path) as connection:
        row = connection.execute(
            "SELECT customer_id, name, email FROM customers WHERE customer_id = ?",
            (customer_id,),
        ).fetchone()
    return dict(row) if row else None


def list_customer_orders(
    customer_id: int, db_path: Path = DB_PATH
) -> list[dict[str, Any]]:
    """Return orders belonging to one customer, newest first."""
    sql = """
        SELECT order_id, order_date, status, delivery_date, total_amount
        FROM orders
        WHERE customer_id = ?
        ORDER BY order_date DESC, order_id DESC
    """
    with connect_read_only(db_path) as connection:
        rows = connection.execute(sql, (customer_id,)).fetchall()
    return [dict(row) for row in rows]


def customer_owns_order(
    customer_id: int, order_id: str, db_path: Path = DB_PATH
) -> bool:
    """Object-level authorization: the session customer must own the order."""
    with connect_read_only(db_path) as connection:
        row = connection.execute(
            "SELECT 1 FROM orders WHERE customer_id = ? AND order_id = ?",
            (customer_id, order_id),
        ).fetchone()
    return row is not None


def get_order(order_id: str, db_path: Path = DB_PATH) -> dict[str, Any] | None:
    """Return one governed order aggregate containing its product evidence."""
    order_sql = """
        SELECT o.order_id, o.order_date, o.status, o.delivery_date,
               o.total_amount, o.shipping_address, o.payment_method,
               o.customer_id, c.name AS customer_name
        FROM orders AS o
        JOIN customers AS c ON c.customer_id = o.customer_id
        WHERE o.order_id = ?
    """
    item_sql = """
        SELECT oi.product_id, p.name, p.category, p.description,
               p.return_policy, p.warranty_period,
               oi.quantity, oi.price_at_purchase
        FROM order_items AS oi
        JOIN products AS p ON p.product_id = oi.product_id
        WHERE oi.order_id = ?
        ORDER BY p.name
    """
    with connect_read_only(db_path) as connection:
        order = connection.execute(order_sql, (order_id,)).fetchone()
        if order is None:
            return None
        items = connection.execute(item_sql, (order_id,)).fetchall()
    result = dict(order)
    result["items"] = [dict(item) for item in items]
    return result


def database_summary(db_path: Path = DB_PATH) -> dict[str, int]:
    """Return counts used by the app and notebook data audit."""
    with connect_read_only(db_path) as connection:
        return {
            table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("customers", "orders", "order_items", "products")
        }
