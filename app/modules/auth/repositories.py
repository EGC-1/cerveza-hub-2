from app.modules.auth.models import User, UserSession
from core.repositories.BaseRepository import BaseRepository
from app import db


class UserRepository(BaseRepository):
    def __init__(self):
        super().__init__(User)

    def create(self, commit: bool = True, **kwargs):
        password = kwargs.pop("password")
        instance = self.model(**kwargs)
        instance.set_password(password)
        self.session.add(instance)
        if commit:
            self.session.commit()
        else:
            self.session.flush()
        return instance

    def get_by_email(self, email: str):
        return self.model.query.filter_by(email=email).first()

class UserSessionRepository(BaseRepository):
    def __init__(self):
        super().__init__(UserSession)

    def save_session(self, user_id: int, session_key: str, ip_address:str, user_agent: str) -> UserSession:
        """
        Save a new user session
        """
        session_obj = self.model(
            user_id = user_id,
            session_key = session_key,
            ip_address = ip_address,
            user_agent = user_agent
        )
        self.session.add(session_obj)
        try:
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            raise e
        return session_obj

    def get_by_user_id(self, user_id: int) -> list[UserSession]:
        """
        Get all sessions for a user, ordered by the most recent
        """
        return self.model.query.filter_by(user_id = user_id).order_by(self.model.login_time.desc()).all()
    
    def get_session_by_key(self, session_key:str):
        """
        Get a session by its key
        """
        sessions = self.get_by_column('session_key', session_key)
        return sessions[0] if sessions else None

    def delete_by_key(self, session_key: str) -> bool:
        """
        Delete a session by its key
        """
        session_to_delete = self.model.query.filter_by(session_key = session_key).first()
        if session_to_delete:
            self.session.delete(session_to_delete)
            self.session.commit()
            return True
        return False