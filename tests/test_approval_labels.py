from hermes_gmail_bridge.approval_labels import build_approval_label, find_message_id_for_approval_label


class FakeGmail:
    def __init__(self, message_ids):
        self.message_ids = message_ids
        self.queries = []

    def list_recent_message_ids(self, query, max_results=20):
        self.queries.append((query, max_results))
        return list(self.message_ids)


def test_build_approval_label_is_short_deterministic_and_case_insensitive():
    assert build_approval_label("18f9abc123456789") == build_approval_label("18F9ABC123456789")
    assert build_approval_label("18f9abc123456789").startswith("A-")
    assert len(build_approval_label("18f9abc123456789")) == 8


def test_find_message_id_for_approval_label_searches_recent_messages_without_state():
    gmail = FakeGmail(["m-old", "18f9abc123456789", "m-other"])
    label = build_approval_label("18f9abc123456789")

    assert find_message_id_for_approval_label(gmail, label, query="newer_than:14d") == "18f9abc123456789"
    assert gmail.queries == [("newer_than:14d", 50)]


def test_find_message_id_for_approval_label_rejects_unknown_label():
    gmail = FakeGmail(["m-old", "m-other"])

    assert find_message_id_for_approval_label(gmail, "A-NOMATC", query="newer_than:14d") is None
