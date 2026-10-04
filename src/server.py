import logging

from mcp.server.fastmcp import FastMCP

from src.tools import tickets

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

mcp = FastMCP("freshdesk-readonly")

mcp.tool()(tickets.list_tickets)
mcp.tool()(tickets.get_ticket)
mcp.tool()(tickets.search_tickets)
mcp.tool()(tickets.list_conversations)

if __name__ == "__main__":
    mcp.run()