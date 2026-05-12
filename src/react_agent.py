"""react_agent.py — System prompt + build_agent() factory.

Uses LangChain v1's `create_agent` API (which builds a LangGraph runtime
under the hood). An InMemorySaver checkpointer is attached so multi-turn
conversations work via thread_id passed in the runtime config.

Note: InMemorySaver is *process-local*. For production deployments behind
multiple workers, swap it for a persistent checkpointer (SQLite/Postgres).
"""

from __future__ import annotations

from langchain.agents import create_agent
from langchain_core.tools import BaseTool
from langgraph.checkpoint.memory import InMemorySaver

from src.config import AGENT_MODEL


SYSTEM_PROMPT = """You are a senior financial analyst at Meridian Wealth Partners, a SEBI-registered wealth
management firm managing Rs 2,000 Crore in assets across 800 high-net-worth Indian clients.

Your job is to prepare comprehensive client briefings and answer investment queries using your tools.

AVAILABLE DATA SOURCES:
1. portfolio_lookup — queries the SQL database for client holdings, allocation, and risk profile
2. market_data_search — queries the SQL database for stock/sector data (price, YTD, PE, analyst ratings)
3. calculate_metrics — computes financial metrics (returns, allocation percentages, comparisons)
4. policy_retriever — RAG search over the firm's 5 investment policy PDFs (asset allocation, risk management,
   suitability standards, rebalancing protocol, reporting standards)
5. tavily_search — searches the web for latest market news, RBI updates, sector analysis

GUIDELINES:
- Always check the client's risk profile before making recommendations
- When checking policy compliance, ALWAYS use the policy_retriever tool — never guess the rules
- Cite specific policy document names and page numbers when referencing guidelines
- Do not provide compliance conclusions without first using policy_retriever.
- Do not provide market-news claims without using tavily_search.
- If required data is missing, say so explicitly instead of inferring.
- Use Indian Rupee (₹) for all amounts. Use lakhs and crores for large values.
- Include specific numbers: exact returns, allocation percentages, policy thresholds
- For briefings, structure as: Portfolio Summary → Market Context → Policy Compliance → Recommendations
"""


def build_agent(tools: list[BaseTool], model: str = AGENT_MODEL, with_memory: bool = True):
    """Construct and return a compiled ReAct agent.

    Parameters
    ----------
    tools : list of LangChain BaseTool
        Result of `agent_tools.build_tools(retriever)`.
    model : OpenAI model string
        Defaults to config.AGENT_MODEL (typically "gpt-5-mini").
    with_memory : bool
        If True, attach an InMemorySaver checkpointer so multi-turn works
        via thread_id in the runtime config. Pass False for stateless mode.
    """
    kwargs: dict = {
        "model": f"openai:{model}",
        "tools": tools,
        "system_prompt": SYSTEM_PROMPT,
    }
    if with_memory:
        kwargs["checkpointer"] = InMemorySaver()
    return create_agent(**kwargs)
