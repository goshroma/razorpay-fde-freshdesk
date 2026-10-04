import pytest
import responses

from src.freshdesk import client as client_module
from src.freshdesk.client import FreshdeskClient
from src.freshdesk.exceptions import (
    AuthenticationError,
    FreshdeskError,
    InvalidRequestError,
    NotFoundError,
    RateLimitError,
)

BASE = "https://test.freshdesk.com/api/v2"


@pytest.fixture
def client():
    return FreshdeskClient("test.freshdesk.com", "fake-key")


@pytest.fixture(autouse=True)
def sleeps(monkeypatch):
    recorded = []
    monkeypatch.setattr(client_module.time, "sleep", recorded.append)
    return recorded


def test_missing_credentials_rejected():
    with pytest.raises(FreshdeskError):
        FreshdeskClient("", "")


@responses.activate
def test_get_ticket_success_sends_basic_auth(client):
    responses.add(responses.GET, f"{BASE}/tickets/4", json={"id": 4}, status=200)
    assert client.get_ticket(4) == {"id": 4}
    assert responses.calls[0].request.headers["Authorization"].startswith("Basic ")


@responses.activate
def test_list_tickets_sends_pagination(client):
    responses.add(responses.GET, f"{BASE}/tickets", json=[{"id": 1}], status=200)
    assert client.list_tickets(page=2, per_page=5) == [{"id": 1}]
    url = responses.calls[0].request.url
    assert "page=2" in url and "per_page=5" in url


@responses.activate
def test_list_tickets_empty(client):
    responses.add(responses.GET, f"{BASE}/tickets", json=[], status=200)
    assert client.list_tickets() == []


@responses.activate
def test_search_wraps_query_in_quotes(client):
    responses.add(
        responses.GET,
        f"{BASE}/search/tickets",
        json={"results": [{"id": 4}], "total": 1},
        status=200,
    )
    assert client.search_tickets("status:2")["total"] == 1
    assert "query=%22status%3A2%22" in responses.calls[0].request.url


@responses.activate
def test_list_conversations_success(client):
    responses.add(
        responses.GET,
        f"{BASE}/tickets/4/conversations",
        json=[{"id": 9}],
        status=200,
    )
    assert client.list_conversations(4) == [{"id": 9}]


@responses.activate
@pytest.mark.parametrize(
    "status, expected",
    [
        (400, InvalidRequestError),
        (401, AuthenticationError),
        (403, AuthenticationError),
        (404, NotFoundError),
    ],
)
def test_client_errors_are_mapped_without_retry(client, sleeps, status, expected):
    responses.add(responses.GET, f"{BASE}/tickets/4", json={}, status=status)
    with pytest.raises(expected):
        client.get_ticket(4)
    assert len(responses.calls) == 1
    assert sleeps == []


@responses.activate
def test_429_honours_retry_after_then_succeeds(client, sleeps):
    responses.add(
        responses.GET,
        f"{BASE}/tickets/4",
        json={},
        status=429,
        headers={"Retry-After": "2"},
    )
    responses.add(responses.GET, f"{BASE}/tickets/4", json={"id": 4}, status=200)
    assert client.get_ticket(4) == {"id": 4}
    assert sleeps == [2]


@responses.activate
def test_429_without_header_uses_exponential_backoff_and_gives_up(client, sleeps):
    responses.add(responses.GET, f"{BASE}/tickets/4", json={}, status=429)
    with pytest.raises(RateLimitError):
        client.get_ticket(4)
    assert len(responses.calls) == 4
    assert sleeps == [1, 2, 4]


@responses.activate
def test_persistent_5xx_fails_after_bounded_retries(client, sleeps):
    responses.add(responses.GET, f"{BASE}/tickets/4", json={}, status=503)
    with pytest.raises(FreshdeskError):
        client.get_ticket(4)
    assert len(responses.calls) == 4


@responses.activate
def test_error_message_never_contains_api_key(client):
    responses.add(responses.GET, f"{BASE}/tickets/4", json={}, status=401)
    with pytest.raises(AuthenticationError) as info:
        client.get_ticket(4)
    assert "fake-key" not in str(info.value)