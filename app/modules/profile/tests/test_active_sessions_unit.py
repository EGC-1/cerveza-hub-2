from unittest.mock import patch

import pytest

from app.modules.conftest import login, logout
from app.modules.auth.models import User


@pytest.fixture(scope="module")
def logged_client(test_client):
    """
    Logged-in test client with a valid user.
    """
    with test_client.application.app_context():
        user = User.query.filter_by(email="user@example.com").first()
        if not user:
            user = User(email="user@example.com", password="test1234", role_id=1)
            from app import db
            db.session.add(user)
            db.session.commit()

    login(test_client, "user@example.com", "test1234")
    yield test_client
    logout(test_client)


def _pop_flashes(client):
    """
    Safely reads flashes and clears them from session so tests don't leak state.
    Flask stores flashes in session under '_flashes' as (category, message).
    """
    with client.session_transaction() as sess:
        flashes = list(sess.get("_flashes", []))
        sess.pop("_flashes", None)
        return flashes


def _assert_has_any_flash(flashes):
    assert flashes is not None and len(flashes) >= 1, "Expected at least one flash message"


def _assert_category_ok(flashes):
    allowed = {"message", "success", "warning", "danger", "error", "info"}
    cats = {c for c, _ in flashes}
    assert cats & allowed, f"Unexpected flash categories: {cats}"


def _assert_message_contains_any(flashes, keywords):
    msgs = " | ".join(str(m).lower() for _, m in flashes)
    assert any(k.lower() in msgs for k in keywords), f"Expected keywords {keywords} in flashes, got: {msgs}"


def test_manage_sessions_renders_and_calls_service(logged_client):
    from unittest.mock import ANY

    with patch("app.modules.profile.routes.UserProfileService") as svc_cls:
        svc = svc_cls.return_value
        svc.get_active_sessions.return_value = (
            {"key": "CUR", "is_current": True},
            [{"key": "OTHER", "is_current": False}],
        )

        resp = logged_client.get("/profile/manage_account/sessions")
        assert resp.status_code == 200

        with logged_client.application.app_context():
            user = User.query.filter_by(email="user@example.com").first()
            svc.get_active_sessions.assert_called_once_with(
                user_id=user.id,
                current_session_key=ANY,
                current_ip="127.0.0.1",
            )


def test_close_remote_session_rejects_closing_current_session(logged_client):
    # Arrange
    with logged_client.session_transaction() as sess:
        sess["user_session_key"] = "CUR"
        sess.pop("_flashes", None)

    # Act
    resp = logged_client.post(
        "/profile/manage_account/close_session",
        data={"session_key": "CUR"},
        follow_redirects=False,
    )

    # Assert
    assert resp.status_code in (302, 303)

    flashes = _pop_flashes(logged_client)
    _assert_has_any_flash(flashes)
    _assert_category_ok(flashes)
    _assert_message_contains_any(flashes, keywords=["current", "this session", "cannot", "not allowed", "session"])