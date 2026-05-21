from __future__ import annotations

import hashlib
import re
from typing import Protocol

_LABEL_RE = re.compile(r"^A-[0-9A-Z]{6}$")


class RecentMessageLister(Protocol):
    def list_recent_message_ids(self, query: str, max_results: int = 20) -> list[str]: ...


def build_approval_label(message_id: str) -> str:
    """Return a short deterministic approval label for a Gmail message id."""
    normalized = str(message_id).strip().lower()
    digest = hashlib.blake2s(normalized.encode("utf-8"), digest_size=5).hexdigest().upper()
    return f"A-{digest[:6]}"


def is_approval_label(value: str) -> bool:
    return bool(_LABEL_RE.fullmatch(str(value).strip().upper()))


def find_message_id_for_approval_label(
    gmail: RecentMessageLister,
    label: str,
    query: str,
    max_results: int = 50,
) -> str | None:
    """Resolve an approval label by scanning recent Gmail message ids.

    This intentionally keeps approval labels stateless: no mapping table is
    written. The caller controls the Gmail search query/window.
    """
    normalized_label = str(label).strip().upper()
    if not is_approval_label(normalized_label):
        return None

    for message_id in gmail.list_recent_message_ids(query, max_results=max_results):
        if build_approval_label(message_id) == normalized_label:
            return message_id
    return None
