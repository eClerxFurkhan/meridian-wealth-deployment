"""agent_tools.py — LangChain @tool wrappers.

`build_tools(retriever)` is a factory that returns the list of tools the
agent will use. Tools that need external resources (the FAISS retriever)
close over them rather than relying on module-level globals — cleaner
dependency injection and avoids import-time side effects.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from langchain_core.tools import BaseTool, tool
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_tavily import TavilySearch

from src.config import TAVILY_MAX_RESULTS
from src.database_queries import (
    get_client_portfolio,
    list_client_ids,
    list_tickers,
    search_market_data,
)


# --- Internal helpers (not exposed as tools) -----------------------------

def _format_portfolio(portfolio: dict[str, Any]) -> str:
    """Compute aggregates + per-holding detail and return a JSON string."""
    c = portfolio["client"]
    holdings = portfolio["holdings"]

    total_current = sum(h["shares"] * h["current_price"] for h in holdings)
    total_cost = sum(h["shares"] * h["avg_cost_basis"] for h in holdings)
    overall_return = ((total_current - total_cost) / total_cost) * 100 if total_cost else 0.0

    # Sector allocation
    sector_values: dict[str, float] = {}
    for h in holdings:
        val = h["shares"] * h["current_price"]
        sector_values[h["sector"]] = sector_values.get(h["sector"], 0.0) + val
    sector_pct = {s: round((v / total_current) * 100, 1) for s, v in sector_values.items()}

    # Per-holding detail
    holdings_detail = []
    for h in holdings:
        cv = h["shares"] * h["current_price"]
        gain = ((h["current_price"] - h["avg_cost_basis"]) / h["avg_cost_basis"]) * 100
        wt = (cv / total_current) * 100 if total_current else 0.0
        holdings_detail.append({
            "ticker": h["ticker"], "company": h["company_name"],
            "shares": h["shares"], "avg_cost": h["avg_cost_basis"],
            "current_price": h["current_price"], "current_value": cv,
            "unrealized_gain_pct": round(gain, 1),
            "portfolio_weight_pct": round(wt, 1),
            "sector": h["sector"], "ytd_return": h["ytd_return_pct"],
            "analyst_rating": h["analyst_rating"], "purchase_date": h["purchase_date"],
        })

    result = {
        "client_id": c["client_id"], "name": c["name"],
        "relationship_manager": c["relationship_mgr"],
        "risk_profile": c["risk_profile"],
        "investment_horizon": c["investment_horizon"],
        "aum_inr": c["aum_inr"], "last_review": c["last_review"],
        "total_portfolio_value": round(total_current),
        "total_cost_basis": round(total_cost),
        "overall_return_pct": round(overall_return, 1),
        "sector_allocation": sector_pct,
        "holdings": holdings_detail,
    }
    return json.dumps(result, indent=2, ensure_ascii=False)


def _calculate(expression: str) -> str:
    """Heuristic financial calculator — preserved from the source notebook."""
    try:
        numbers = [float(x.replace(",", "")) for x in re.findall(r"[\d,]+\.?\d*", expression)]
        e = expression.lower()

        if ("return" in e or "gain" in e) and len(numbers) >= 2:
            current, cost = numbers[0], numbers[1]
            ret = ((current - cost) / cost) * 100
            return f"Return: (₹{current:,.0f} - ₹{cost:,.0f}) / ₹{cost:,.0f} = {ret:+.2f}%"

        if ("percentage" in e or "allocation" in e or "weight" in e) and len(numbers) >= 2:
            part, whole = numbers[0], numbers[1]
            return f"Percentage: ₹{part:,.0f} / ₹{whole:,.0f} = {(part / whole) * 100:.2f}%"

        if "compare" in e and len(numbers) >= 2:
            a, b = numbers[0], numbers[1]
            return f"Comparison: {a:,.2f} vs {b:,.2f} | Diff: {a - b:+,.2f} ({((a - b) / b) * 100:+.2f}%)"

        if len(numbers) == 2:
            a, b = numbers
            return (f"Values: {a:,.2f} and {b:,.2f} | Sum: {a + b:,.2f} | "
                    f"Diff: {a - b:+,.2f} | Ratio: {a / b:.4f}")

        return f"Provide two numbers with operation type (return, percentage, compare). Got: '{expression}'"
    except Exception as exc:
        return f"Calculation error: {exc}"


# --- Public factory ------------------------------------------------------

def build_tools(retriever: VectorStoreRetriever) -> list[BaseTool]:
    """Return the agent's tool list, wired to the given retriever and DB.

    The @tool decorator is applied inside this function so the policy_retriever
    tool closes over `retriever` cleanly. Tool *names* (`portfolio_lookup`,
    `market_data_search`, …) come from the inner function names and must
    match the names referenced in the system prompt.
    """

    @tool
    def portfolio_lookup(client_id: str) -> str:
        """Look up a client's portfolio from the database: holdings, allocation, total value, and risk profile.
        Use this when you need to know what a specific client owns or their investment profile.
        Input: client ID like 'CLT-001', 'CLT-002', etc."""
        portfolio = get_client_portfolio(client_id.upper())
        if not portfolio:
            return f"Client {client_id} not found. Available: {', '.join(list_client_ids())}"
        return _format_portfolio(portfolio)

    @tool
    def market_data_search(query: str) -> str:
        """Search the market database for stock tickers or sectors. Returns current price, YTD returns,
        PE ratio, analyst ratings, 52-week range, and market cap. Use this when you need market
        performance data for specific stocks or want to compare sector performance.
        Input: a stock ticker (e.g. 'RELIANCE'), sector name (e.g. 'IT', 'Banking'), or company name."""
        results = search_market_data(query)
        if not results:
            return f"No data found for '{query}'. Available: {', '.join(list_tickers())}"
        formatted = [{
            "ticker": r["ticker"], "company": r["company_name"], "sector": r["sector"],
            "price": r["current_price"], "ytd_return": r["ytd_return_pct"],
            "pe_ratio": r["pe_ratio"], "analyst_rating": r["analyst_rating"],
            "52w_range": f"{r['low_52w']} - {r['high_52w']}",
            "market_cap_cr": r["market_cap_cr"],
        } for r in results]
        return json.dumps(formatted, indent=2, ensure_ascii=False)

    @tool
    def calculate_metrics(expression: str) -> str:
        """Perform financial calculations: returns, percentages, allocations, comparisons.
        Input: describe the calculation, e.g. 'return on 596000 vs cost 430000'
        or 'percentage of 350000 out of 2530000' or 'compare 18.5 vs 12.3'."""
        return _calculate(expression)

    @tool
    def policy_retriever(query: str) -> str:
        """Search Meridian Wealth Partners' investment policy PDF documents using RAG (vector similarity search).
        Use this when you need to check investment guidelines, allocation rules, rebalancing triggers,
        risk limits, concentration limits, suitability standards, or reporting requirements.
        Returns relevant excerpts with source document name and page number.
        Input: a natural language query about investment policies."""
        docs = retriever.invoke(query)
        chunks = []
        for i, doc in enumerate(docs, 1):
            src = os.path.basename(doc.metadata.get("source", "unknown"))
            pg = doc.metadata.get("page", "?")
            chunks.append(f"[Policy Doc {i}: {src} | Page {pg}]\n{doc.page_content}")
        return "\n\n---\n\n".join(chunks)

    web_search = TavilySearch(max_results=TAVILY_MAX_RESULTS, topic="news")

    return [portfolio_lookup, market_data_search, calculate_metrics, policy_retriever, web_search]
