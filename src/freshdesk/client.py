import logging
import os
import time

import requests
from dotenv import load_dotenv

from src.freshdesk.exceptions import (
    AuthenticationError,
    FreshdeskError,
    InvalidRequestError,
    NotFoundError,
    RateLimitError,
)

logger = logging.getLogger("freshdesk")

MAX_RETRIES = 3
BASE_BACKOFF_SECONDS = 1
MAX_WAIT_SECONDS = 30


class FreshdeskClient:
    def __init__(self, domain: str, api_key: str, timeout: int = 10):
        if not domain or not api_key:
            raise FreshdeskError(
                "FRESHDESK_DOMAIN and FRESHDESK_API_KEY must be set"
            )
        self.base_url = f"https://{domain}/api/v2"
        self.timeout = timeout
        self.session = requests.Session()
        self.session.auth = (api_key, "X")

    @classmethod
    def from_env(cls) -> "FreshdeskClient":
        load_dotenv()
        return cls(
            os.getenv("FRESHDESK_DOMAIN", ""),
            os.getenv("FRESHDESK_API_KEY", ""),
        )

    def _wait_seconds(self, response, attempt: int) -> int:
        retry_after = response.headers.get("Retry-After", "")
        if retry_after.isdigit():
            return min(int(retry_after), MAX_WAIT_SECONDS)
        return min(BASE_BACKOFF_SECONDS * 2**attempt, MAX_WAIT_SECONDS)

    def _request(self, path: str, params: dict | None = None):
        url = f"{self.base_url}{path}"
        for attempt in range(MAX_RETRIES + 1):
            logger.info("GET %s", path)
            try:
                response = self.session.get(
                    url, params=params, timeout=self.timeout
                )
            except requests.Timeout:
                raise FreshdeskError("Freshdesk request timed out")
            except requests.ConnectionError:
                raise FreshdeskError("Could not connect to Freshdesk")

            status = response.status_code
            if status == 200:
                return response.json()
            if status == 429 or status >= 500:
                if attempt < MAX_RETRIES:
                    wait = self._wait_seconds(response, attempt)
                    logger.warning(
                        "Freshdesk returned %s, retry %s of %s in %ss",
                        status,
                        attempt + 1,
                        MAX_RETRIES,
                        wait,
                    )
                    time.sleep(wait)
                    continue
                if status == 429:
                    raise RateLimitError(
                        "Freshdesk rate limit still exceeded after retries"
                    )
                raise FreshdeskError(
                    f"Freshdesk server error {status} after retries"
                )
            if status == 400:
                raise InvalidRequestError(
                    "Freshdesk rejected the request as invalid"
                )
            if status == 401:
                raise AuthenticationError("Freshdesk authentication failed")
            if status == 403:
                raise AuthenticationError(
                    "Freshdesk denied permission for this resource"
                )
            if status == 404:
                raise NotFoundError("Freshdesk resource not found")
            raise FreshdeskError(
                f"Freshdesk returned an unexpected status {status}"
            )

    def get_ticket(self, ticket_id: int) -> dict:
        return self._request(f"/tickets/{ticket_id}")

    def list_tickets(self, page: int = 1, per_page: int = 20) -> list:
        return self._request(
            "/tickets", params={"page": page, "per_page": per_page}
        )

    def search_tickets(self, query: str, page: int = 1) -> dict:
        return self._request(
            "/search/tickets", params={"query": f'"{query}"', "page": page}
        )

    def list_conversations(self, ticket_id: int, page: int = 1) -> list:
        return self._request(
            f"/tickets/{ticket_id}/conversations", params={"page": page}
        )