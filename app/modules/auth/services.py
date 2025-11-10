import os
import secrets 

from flask_login import current_user, login_user

from app import db 
from app.modules.auth.models import User
from app.modules.auth.repositories import UserRepository
from app.modules.profile.models import UserProfile
from app.modules.profile.repositories import UserProfileRepository
from core.configuration.configuration import uploads_folder_name
from core.services.BaseService import BaseService
from flask import url_for, current_app, render_template
# Solo necesitamos la clase Message de flask_mail para construir el email
from flask_mail import Message 

class AuthenticationService(BaseService):
    
    def __init__(self):
        super().__init__(UserRepository())
        self.user_profile_repository = UserProfileRepository()

    def login(self, email, password, remember=True):
        user = self.repository.get_by_email(email)
        if user is not None and user.check_password(password):
            login_user(user, remember=remember)
            return True
        return False

    def is_email_available(self, email: str) -> bool:
        return self.repository.get_by_email(email) is None

    def create_with_profile(self, **kwargs):
        try:
            email = kwargs.pop("email", None)
            password = kwargs.pop("password", None)
            name = kwargs.pop("name", None)
            surname = kwargs.pop("surname", None)

            if not email:
                raise ValueError("Email is required.")
            if not password:
                raise ValueError("Password is required.")
            if not name:
                raise ValueError("Name is required.")
            if not surname:
                raise ValueError("Surname is required.")

            user_data = {"email": email, "password": password}

            profile_data = {
                "name": name,
                "surname": surname,
            }

            user = self.create(commit=False, **user_data)
            profile_data["user_id"] = user.id
            self.user_profile_repository.create(**profile_data)
            self.repository.session.commit()
        except Exception as exc:
            self.repository.session.rollback()
            raise exc
        return user

    def update_profile(self, user_profile_id, form):
        if form.validate():
            updated_instance = self.update(user_profile_id, **form.data)
            return updated_instance, None

        return None, form.errors

    def get_authenticated_user(self) -> User | None:
        if current_user.is_authenticated:
            return current_user
        return None

    def get_authenticated_user_profile(self) -> UserProfile | None:
        if current_user.is_authenticated:
            return current_user.profile
        return None

    def temp_folder_by_user(self, user: User) -> str:
        return os.path.join(uploads_folder_name(), "temp", str(user.id))
    
    def update_user(self, user):
        """
        Persiste cualquier cambio realizado al objeto de usuario en la base de datos.
        Se usa para guardar el token de restablecimiento o la nueva contraseña hasheada.
        """
        try:
            db.session.add(user) 
            self.repository.session.commit()
            return True
        except Exception as e:
            self.repository.session.rollback()
            print(f"Error al actualizar el usuario: {e}")
            return False
        
    def get_user_by_email(self, email):
        """
        Busca y retorna un usuario por su dirección de correo electrónico.
        """
        return User.query.filter_by(email=email).first()

authentication_service = AuthenticationService()


def send_password_reset_email(user):
    """
    Genera el token de restablecimiento y envía el correo electrónico al usuario.
    """
    
    mail = current_app.extensions.get('mail')
    
    if mail is None:
        current_app.logger.error("La extensión Flask-Mail no está registrada en la aplicación.")
        return False
        
    try:
        token = user.generate_reset_token()
        
        db.session.commit()
        current_app.logger.info(f"Token {token} guardado en DB para {user.email}.")
    
        reset_url = url_for(
            'auth.reset_token', 
            token=token,
            _external=True
        )

        msg = Message(
            subject='Restablecimiento de Contraseña',
            sender=current_app.config['MAIL_DEFAULT_SENDER'], 
            recipients=[user.email]
        )
        
        msg.html = render_template(
            'auth/email_recover.html', 
            user=user, 
            reset_url=reset_url,
            FLASK_APP_NAME=current_app.config.get('FLASK_APP_NAME', 'Mi Aplicación')
        )
        
        
        current_app.logger.info(f"EMAIL: Intentando enviar correo a {user.email}...")
        mail.send(msg) 
        current_app.logger.info(f"Correo de restablecimiento enviado con éxito a {user.email}.")
        
        return True

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(
            f"FALLO CRÍTICO al enviar el correo a {user.email}. Error: {e.__class__.__name__}",
            exc_info=True 
        )
        return False