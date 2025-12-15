from app.modules.profile.repositories import UserProfileRepository
from core.services.BaseService import BaseService
from app.modules.auth.services import AuthenticationService
from flask import request

auth_service = AuthenticationService()

class UserProfileService(BaseService):
    def __init__(self):
        super().__init__(UserProfileRepository())
        self.auth_service = auth_service

    def update_profile(self, user_profile_id, form):
        if form.validate():
            updated_instance = self.update(user_profile_id, **form.data)
            return updated_instance, None

        return None, form.errors

    def get_active_sessions (self, user_id: int, current_session_key: str, current_ip: str):
        """
        Retrieve active sessions for a user, excluding the current session
        """
        current_device_info = self.auth_service.get_current_session_info(current_session_key, current_ip)
        other_sessions_data = self.auth_service.get_other_active_sessions(user_id, current_session_key)
        return current_device_info, other_sessions_data

    def terminate_session(self, user_id: int, session_key_to_close: str):
        """
        Terminate a remote session for a user 
        """
        try:
            success = self.auth_service.close_remote_session(user_id, session_key_to_close)
            if success:
                return True, "Session closed successfully."
            else:
                return False, "Failed to terminate the session. It might have already been closed or does not exist."
        except Exception as e:
            return False, str(e)