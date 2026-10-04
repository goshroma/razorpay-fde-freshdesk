STATUS_LABELS = {2: "Open", 3: "Pending", 4: "Resolved", 5: "Closed"}
PRIORITY_LABELS = {1: "Low", 2: "Medium", 3: "High", 4: "Urgent"}
MAX_TEXT_LENGTH = 2000


def _truncate(text: str | None) -> str:
    text = (text or "").strip()
    if len(text) <= MAX_TEXT_LENGTH:
        return text
    return text[:MAX_TEXT_LENGTH] + "... [truncated]"


def normalize_ticket(raw: dict) -> dict:
    ticket = {
        "id": raw.get("id"),
        "subject": raw.get("subject"),
        "status": STATUS_LABELS.get(raw.get("status"), f"Other ({raw.get('status')})"),
        "priority": PRIORITY_LABELS.get(
            raw.get("priority"), f"Other ({raw.get('priority')})"
        ),
        "type": raw.get("type"),
        "tags": raw.get("tags", []),
        "requester_id": raw.get("requester_id"),
        "created_at": raw.get("created_at"),
        "updated_at": raw.get("updated_at"),
    }
    if "description_text" in raw:
        ticket["description"] = _truncate(raw.get("description_text"))
    return ticket


def normalize_conversation(raw: dict) -> dict:
    return {
        "id": raw.get("id"),
        "body": _truncate(raw.get("body_text")),
        "from_customer": raw.get("incoming"),
        "private_note": raw.get("private"),
        "user_id": raw.get("user_id"),
        "created_at": raw.get("created_at"),
    }