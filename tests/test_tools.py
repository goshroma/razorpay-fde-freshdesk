import pytest

from src.freshdesk.exceptions import NotFoundError
from src.tools import tickets

RAW_TICKET = {
    "id": 4,
    "subject": "UPI payment failed",
    "status": 2,
    "priority": 3,
    "description_text": "Amount deducted",
    "cc_emails": ["hidden@example.com"],
}


class FakeClient:
    def __init__(self):
        self.calls = 0

    def list_tickets(self, page, per_page):
        self.calls += 1
        return [RAW_TICKET] * per_page

    def get_ticket(self, ticket_id):
        self.calls += 1
        if ticket_id == 404:
            raise NotFoundError("Freshdesk resource not found")
        return RAW_TICKET

    def search_tickets(self, query, page):
        self.calls += 1
        return {"results": [], "total": 0}

    def list_conversations(self, ticket_id, page):
        self.calls += 1
        return [{"id": 9, "body_text": "We are checking", "incoming": False}]


@pytest.fixture
def fake(monkeypatch):
    client = FakeClient()
    monkeypatch.setattr(tickets, "get_client", lambda: client)
    return client


def test_get_ticket_is_normalized(fake):
    ticket = tickets.get_ticket(4)["ticket"]
    assert ticket["status"] == "Open"
    assert ticket["priority"] == "High"
    assert ticket["description"] == "Amount deducted"
    assert "cc_emails" not in ticket


def test_get_ticket_not_found_returns_safe_error(fake):
    result = tickets.get_ticket(404)
    assert result == {
        "error": {"type": "NotFoundError", "message": "Freshdesk resource not found"}
    }


def test_list_tickets_reports_has_more(fake):
    result = tickets.list_tickets(page=1, per_page=2)
    assert result["count"] == 2
    assert result["has_more"] is True


def test_search_empty_results(fake):
    result = tickets.search_tickets("status:5")
    assert result["tickets"] == []
    assert result["total"] == 0
    assert result["has_more"] is False


def test_list_conversations_is_normalized(fake):
    result = tickets.list_conversations(4)
    assert result["conversations"][0]["body"] == "We are checking"
    assert result["conversations"][0]["from_customer"] is False


@pytest.mark.parametrize(
    "call",
    [
        lambda: tickets.get_ticket(0),
        lambda: tickets.list_tickets(page=0),
        lambda: tickets.list_tickets(per_page=500),
        lambda: tickets.search_tickets("   "),
        lambda: tickets.search_tickets("status:2", page=11),
        lambda: tickets.list_conversations(-1),
    ],
)
def test_invalid_input_never_reaches_freshdesk(fake, call):
    assert call()["error"]["type"] == "InvalidInput"
    assert fake.calls == 0