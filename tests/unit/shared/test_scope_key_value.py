import pytest

from app.shared.domain.values.scope_key import ScopeKey


def test_scope_key_constructs_from_resource_and_action():
    sk = ScopeKey(resource="users", action="read")
    assert sk.key == "users:read"
    assert str(sk) == "users:read"


def test_scope_key_parse_round_trip():
    sk = ScopeKey.parse("users:read")
    assert sk.resource == "users"
    assert sk.action == "read"
    assert sk.key == "users:read"


def test_scope_key_parse_rejects_missing_colon():
    with pytest.raises(ValueError):
        ScopeKey.parse("usersread")


def test_scope_key_parse_rejects_extra_colons():
    with pytest.raises(ValueError):
        ScopeKey.parse("users:read:extra")


def test_scope_key_rejects_empty_parts():
    with pytest.raises(ValueError):
        ScopeKey(resource="", action="read")
    with pytest.raises(ValueError):
        ScopeKey(resource="users", action="")


def test_scope_key_rejects_colon_in_parts():
    with pytest.raises(ValueError):
        ScopeKey(resource="us:ers", action="read")


def test_scope_key_equality():
    assert ScopeKey("users", "read") == ScopeKey("users", "read")
    assert ScopeKey("users", "read") != ScopeKey("users", "write")
