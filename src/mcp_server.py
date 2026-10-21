"""MCP server that lets an AI assistant (e.g. Claude) clean card descriptors as a tool.

Exposes three tools:
  - clean_descriptor:    turn one raw descriptor into merchant, processor, city, province, category
  - clean_descriptors:   do the same for a list of descriptors
  - evaluation_report:   show how accurate the extractor is on the gold dataset

Run it locally:   python src/mcp_server.py
Then connect it to Claude Desktop or Claude Code (see README).
"""
import sys
from pathlib import Path

from mcp.server.mcpserver import MCPServer

sys.path.insert(0, str(Path(__file__).resolve().parent))
import evaluate  # noqa: E402
import extract_rules  # noqa: E402

server = MCPServer("merchant-descriptor-enrichment")


@server.tool()
def clean_descriptor(raw: str) -> dict:
    """Clean a raw Canadian card-statement descriptor (e.g. 'SQ *JOES COFFEE TORONTO ON').

    Returns the recognisable merchant name, payment processor, city, province, and a
    spending category. Empty strings mean the field was not found in the text.
    """
    return extract_rules.extract(raw)


@server.tool()
def clean_descriptors(raws: list[str]) -> list[dict]:
    """Clean a list of raw card-statement descriptors in one call."""
    return [{"raw": r, **extract_rules.extract(r)} for r in raws]


@server.tool()
def evaluation_report() -> dict:
    """Report field-by-field accuracy of the extractor on the hand-labelled gold dataset,
    plus a few example errors, so the assistant can tell users how much to trust results."""
    import pandas as pd

    gold = pd.read_csv(evaluate.ROOT / "data" / "descriptors.csv", keep_default_na=False)
    scores, errors = evaluate.run("Rules", extract_rules.extract, gold)
    return {"descriptors_tested": len(gold), "accuracy": scores, "example_errors": errors[:5]}


if __name__ == "__main__":
    server.run()  # stdio transport, which Claude Desktop and Claude Code use
