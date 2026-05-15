import pytest

from app.shared.domain.values.email import Email


def test_email_accepts_valid_address():
    e = Email("alice@example.com")
    assert e.value == "alice@example.com"
    assert str(e) == "alice@example.com"


def test_email_rejects_missing_at_sign():
    with pytest.raises(ValueError):
        Email("aliceexample.com")


def test_email_rejects_missing_local_part():
    with pytest.raises(ValueError):
        Email("@example.com")


def test_email_rejects_missing_domain_dot():
    with pytest.raises(ValueError):
        Email("alice@example")


def test_email_equality_by_value():
    assert Email("a@b.com") == Email("a@b.com")
    assert Email("a@b.com") != Email("a@c.com")
