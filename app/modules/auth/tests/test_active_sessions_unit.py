import datetime
from unittest.mock import MagicMock

import pytest

from app.modules.auth.services import AuthenticationService
from app.modules.profile.services import UserProfileService


def _session_obj(user_id: int, key: str, ip: str = "1.2.3.4", ua: str = "UA", when=None):
    s = MagicMock()
    s.user_id = user_id
    s.session_key = key
    s.ip_address = ip
    s.user_agent = ua
    s.login_time = when or datetime.datetime(2025, 1, 1, 12, 0, 0)
    return s


def test_get_other_active_sessions_excludes_current_and_formats():
    svc = AuthenticationService()
    svc.user_session_repository = MagicMock()

    svc.user_session_repository.get_by_user_id.return_value = [
        _session_obj(1, "A", ip="10.0.0.1", ua="Chrome"),
        _session_obj(1, "B", ip="10.0.0.2", ua="Firefox"),
    ]

    other = svc.get_other_active_sessions(user_id=1, current_session_key="A")

    assert other == [
        {
            "key": "B",
            "device": "Firefox",
            "ip": "10.0.0.2",
            "time": "2025-01-01T12:00:00",
            "is_current": False,
        }
    ]
    svc.user_session_repository.get_by_user_id.assert_called_once_with(1)


def test_close_remote_session_returns_false_when_session_not_found():
    svc = AuthenticationService()
    svc.user_session_repository = MagicMock()
    svc.repository = MagicMock()
    svc.user_session_repository.get_session_by_key.return_value = None

    assert svc.close_remote_session(user_id=1, session_key_to_close="X") is False
    svc.user_session_repository.delete_by_key.assert_not_called()


def test_close_remote_session_returns_false_when_session_belongs_to_other_user():
    svc = AuthenticationService()
    svc.user_session_repository = MagicMock()
    svc.repository = MagicMock()
    svc.user_session_repository.get_session_by_key.return_value = _session_obj(2, "X")

    assert svc.close_remote_session(user_id=1, session_key_to_close="X") is False
    svc.user_session_repository.delete_by_key.assert_not_called()


def test_close_remote_session_deletes_and_commits_when_ok():
    svc = AuthenticationService()
    svc.user_session_repository = MagicMock()
    svc.repository = MagicMock()
    svc.repository.session = MagicMock()

    svc.user_session_repository.get_session_by_key.return_value = _session_obj(1, "X")
    svc.user_session_repository.delete_by_key.return_value = True

    assert svc.close_remote_session(user_id=1, session_key_to_close="X") is True
    svc.user_session_repository.delete_by_key.assert_called_once_with("X")
    svc.repository.session.commit.assert_called_once()


def test_profile_service_get_active_sessions_delegates_to_auth_service():
    profile_svc = UserProfileService()
    profile_svc.auth_service = MagicMock()

    profile_svc.auth_service.get_current_session_info.return_value = {"key": "CUR"}
    profile_svc.auth_service.get_other_active_sessions.return_value = [{"key": "OTHER"}]

    current, others = profile_svc.get_active_sessions(
        user_id=1, current_session_key="CUR", current_ip="9.9.9.9"
    )

    assert current == {"key": "CUR"}
    assert others == [{"key": "OTHER"}]
    profile_svc.auth_service.get_current_session_info.assert_called_once_with("CUR", "9.9.9.9")
    profile_svc.auth_service.get_other_active_sessions.assert_called_once_with(1, "CUR")


@pytest.mark.parametrize(
    "close_result, expected_ok, expected_msg_part",
    [
        (True, True, "Session closed successfully"),
        (False, False, "Failed to terminate"),
    ],
)
def test_profile_service_terminate_session_maps_result(close_result, expected_ok, expected_msg_part):
    profile_svc = UserProfileService()
    profile_svc.auth_service = MagicMock()
    profile_svc.auth_service.close_remote_session.return_value = close_result

    ok, msg = profile_svc.terminate_session(user_id=1, session_key_to_close="X")

    assert ok is expected_ok
    assert expected_msg_part in msg