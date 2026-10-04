import logging

from src.freshdesk.client import FreshdeskClient
from src.freshdesk.exceptions import FreshdeskError
from src.freshdesk.models import normalize_conversation, normalize_ticket

logger = logging.getLogger("freshdesk.tools")

MAX_PER_PAGE = 50
SEARCH_PAGE_SIZE = 30
MAX_SEARCH_PAGE = 10
MAX_QUERY_LENGTH = 512

_client = None


def get_client() -> FreshdeskClient:
    global _client
    if _client is None:
        _client = FreshdeskClient.from_env()
    return _client


def _invalid(message: str) -> dict:
    return {"error": {"type": "InvalidInput", "message": message}}


def _failure(exc: FreshdeskError) -> dict:
    logger.warning("Tool failed: %s", exc)
    return {"error": {"type": type(exc).__name__, "message": str(exc)}}


def list_tickets(page: int = 1, per_page: int = 20) -> dict:
    """Browse recent support tickets, newest first, one page at a time.

    Use this to get an overview when no specific ticket ID or filter is known.
    Returns ticket summaries without descriptions. Call get_ticket for full
    detail on one ticket. per_page must be between 1 and 50.
    """
    if page < 1:
        return _invalid("page must be 1 or greater")
    if not 1 <= per_page <= MAX_PER_PAGE:
        return _invalid(f"per_page must be between 1 and {MAX_PER_PAGE}")
    logger.info("list_tickets page=%s per_page=%s", page, per_page)
    try:
        raw = get_client().list_tickets(page=page, per_page=per_page)
    except FreshdeskError as exc:
        return _failure(exc)
    return {
        "tickets": [normalize_ticket(t) for t in raw],
        "page": page,
        "count": len(raw),
        "has_more": len(raw) == per_page,
    }


def get_ticket(ticket_id: int) -> dict:
    """Get full details of one ticket, including its description, by exact ID.

    Use this when the ticket ID is already known, for example from
    list_tickets or search_tickets results.
    """
    if ticket_id < 1:
        return _invalid("ticket_id must be a positive integer")
    logger.info("get_ticket ticket_id=%s", ticket_id)
    try:
        raw = get_client().get_ticket(ticket_id)
    except FreshdeskError as exc:
        return _failure(exc)
    return {"ticket": normalize_ticket(raw)}


def search_tickets(query: str, page: int = 1) -> dict:
    """Find tickets matching a Freshdesk field filter query.

    This is a field filter, NOT keyword search. It cannot match words in
    subjects or descriptions. Supported fields include status
    (2=Open, 3=Pending, 4=Resolved, 5=Closed), priority (1=Low, 2=Medium,
    3=High, 4=Urgent), tag, and type. Combine with AND / OR and parentheses.
    Examples: "status:2", "status:2 OR status:3" (all unresolved),
    "priority:4 AND status:2", "tag:'refund'".
    Returns up to 30 ticket summaries per page, pages 1 to 10.
    """
    query = query.strip()
    if not query:
        return _invalid("query must not be empty")
    if len(query) > MAX_QUERY_LENGTH:
        return _invalid(f"query must be at most {MAX_QUERY_LENGTH} characters")
    if not 1 <= page <= MAX_SEARCH_PAGE:
        return _invalid(f"page must be between 1 and {MAX_SEARCH_PAGE}")
    logger.info("search_tickets query=%r page=%s", query, page)
    try:
        raw = get_client().search_tickets(query, page=page)
    except FreshdeskError as exc:
        return _failure(exc)
    results = raw.get("results", [])
    total = raw.get("total", len(results))
    return {
        "tickets": [normalize_ticket(t) for t in results],
        "page": page,
        "count": len(results),
        "total": total,
        "has_more": page * SEARCH_PAGE_SIZE < total and page < MAX_SEARCH_PAGE,
    }


def list_conversations(ticket_id: int, page: int = 1) -> dict:
    """Get the replies and notes on one ticket, by ticket ID.

    Use this when the ticket description alone is not enough and you need
    the back-and-forth between the customer and support agents.
    """
    if ticket_id < 1:
        return _invalid("ticket_id must be a positive integer")
    if page < 1:
        return _invalid("page must be 1 or greater")
    logger.info("list_conversations ticket_id=%s page=%s", ticket_id, page)
    try:
        raw = get_client().list_conversations(ticket_id, page=page)
    except FreshdeskError as exc:
        return _failure(exc)
    return {
        "ticket_id": ticket_id,
        "conversations": [normalize_conversation(c) for c in raw],
        "page": page,
        "count": len(raw),
    }