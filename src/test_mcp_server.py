"""Smoke test: start the MCP server as a real subprocess and call its tools over stdio."""
import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER = Path(__file__).resolve().parent / "mcp_server.py"


async def main():
    params = StdioServerParameters(command=sys.executable, args=[str(SERVER)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("Tools:", [t.name for t in tools.tools])
            result = await session.call_tool("clean_descriptor", {"raw": "TIM HORTONS #3421 KANATA ON"})
            print("clean_descriptor ->", result.content[0].text)
            report = await session.call_tool("evaluation_report", {})
            print("evaluation_report ->", report.content[0].text[:200], "...")


if __name__ == "__main__":
    asyncio.run(main())
