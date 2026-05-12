"""database_queries.py — SQL helpers over meridian_wealth.db.

Thin wrappers around sqlite3. Connections are opened per call and closed
explicitly — fine for a read-mostly workload of this size and avoids the
threading issues of sharing a sqlite3 connection across FastAPI requests.
All functions return either a list of dict rows or a plain dict.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from src.config import DB_PATH


def _connect() -> sqlite3.Connection:
    """Open a new connection with dict-row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def query_db(sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    """Execute a parameterised SELECT and return a list of dict rows."""
    conn = _connect()
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_client_portfolio(client_id: str) -> dict[str, Any] | None:
    """Return {client, holdings} for the given client_id, or None if missing.

    Holdings are joined with market_data so the agent can see YTD return,
    PE ratio, analyst rating, and 52-week range in one call.
    """
    client = query_db("SELECT * FROM clients WHERE client_id = ?", (client_id,))
    if not client:
        return None

    holdings = query_db(
        """
        SELECT h.ticker, h.company_name, h.shares, h.avg_cost_basis, h.current_price,
               h.sector, h.purchase_date,
               m.ytd_return_pct, m.pe_ratio, m.analyst_rating, m.high_52w, m.low_52w
        FROM holdings h
        LEFT JOIN market_data m ON h.ticker = m.ticker
        WHERE h.client_id = ?
        ORDER BY (h.shares * h.current_price) DESC
        """,
        (client_id,),
    )
    return {"client": client[0], "holdings": holdings}


def search_market_data(query: str) -> list[dict[str, Any]]:
    """Search market_data by ticker (exact), then by sector / company / partial ticker."""
    q = query.upper().strip()
    results = query_db("SELECT * FROM market_data WHERE ticker = ?", (q,))
    if not results:
        results = query_db(
            "SELECT * FROM market_data WHERE UPPER(sector) LIKE ? "
            "OR UPPER(company_name) LIKE ? OR ticker LIKE ?",
            (f"%{q}%", f"%{q}%", f"%{q}%"),
        )
    return results


def list_client_ids() -> list[str]:
    """Return all client IDs — used to render a friendly 'not found' message."""
    return [r["client_id"] for r in query_db("SELECT client_id FROM clients")]


def list_tickers() -> list[str]:
    """Return all tickers — used to render a friendly 'not found' message."""
    return [r["ticker"] for r in query_db("SELECT ticker FROM market_data")]


def check_connection() -> bool:
    """Health probe — True if the DB is reachable and the clients table exists."""
    try:
        query_db("SELECT 1 FROM clients LIMIT 1")
        return True
    except Exception:
        return False
