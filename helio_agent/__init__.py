"""The AI Heliophysicist tool layer.

Deterministic, validated heliophysics analysis tools intended to be driven by
an LLM agent. The agent supplies judgment (which tool, which parameters, what
the result means); these tools supply computation. No tool contains LLM logic,
and every invocation is written to the audit trail.
"""

__version__ = "0.1.0"

from helio_agent.registry import tool, get_tool, list_tools, run_tool  # noqa: F401
