import datetime
import pytest
from flask import url_for

from app import db 
from app.modules.auth.models import Role, User 
from unittest.mock import patch, MagicMock


from app.modules.auth.repositories import UserRepository
from app.modules.auth.services import AuthenticationService, send_password_reset_email
from app.modules.profile.repositories import UserProfileRepository


@pytest.fixture(scope="module")
def test_client(test_client):
    """
    Extends the test_client fixture to add additional specific data for module testing.
    """
    with test_client.application.app_context():
        # Add HERE new elements to the database that you want to exist in the test context.
        # DO NOT FORGET to use db.session.add(<element>) and db.session.commit() to save the data.
        pass

    yield test_client


def test_login_success(test_client):
    response = test_client.post(
        "/login", data=dict(email="test@example.com", password="test1234"), follow_redirects=True
    )

    assert response.request.path != url_for("auth.login"), "Login was unsuccessful"

    test_client.get("/logout", follow_redirects=True)


def test_login_unsuccessful_bad_email(test_client):
    response = test_client.post(
        "/login", data=dict(email="bademail@example.com", password="test1234"), follow_redirects=True
    )

    assert response.request.path == url_for("auth.login"), "Login was unsuccessful"

    test_client.get("/logout", follow_redirects=True)


def test_login_unsuccessful_bad_password(test_client):
    response = test_client.post(
        "/login", data=dict(email="test@example.com", password="basspassword"), follow_redirects=True
    )

    assert response.request.path == url_for("auth.login"), "Login was unsuccessful"

    test_client.get("/logout", follow_redirects=True)


def test_signup_user_no_name(test_client):
    response = test_client.post(
        "/signup", data=dict(surname="Foo", email="test@example.com", password="test1234"), follow_redirects=True
    )
    assert response.request.path == url_for("auth.show_signup_form"), "Signup was unsuccessful"
    assert b"This field is required" in response.data, response.data


def test_signup_user_unsuccessful(test_client):
    email = "test@example.com"
    response = test_client.post(
        "/signup", data=dict(name="Test", surname="Foo", email=email, password="test1234"), follow_redirects=True
    )
    assert response.request.path == url_for("auth.show_signup_form"), "Signup was unsuccessful"
    assert f"Email {email} in use".encode("utf-8") in response.data


def test_signup_user_successful(test_client):
    response = test_client.post(
        "/signup",
        data=dict(name="Foo", surname="Example", email="foo@example.com", password="foo1234"),
        follow_redirects=True,
    )
    assert response.request.path == url_for("public.index"), "Signup was unsuccessful"


def test_service_create_with_profile_fail_no_email(clean_database):
    data = {"name": "Test", "surname": "Foo", "email": "", "password": "1234"}

    role_test = Role(id=1, name="user", description="Default user role")
    db.session.add(role_test)
    db.session.commit()
    
    with pytest.raises(ValueError, match="Email is required."):
        AuthenticationService().create_with_profile(**data)

    assert UserRepository().count() == 0
    assert UserProfileRepository().count() == 0


def test_service_create_with_profile_fail_no_password(clean_database):
    data = {"name": "Test", "surname": "Foo", "email": "test@example.com", "password": ""}

    role_test = Role(id=1, name="user", description="Default user role")
    db.session.add(role_test)
    db.session.commit()
    
    with pytest.raises(ValueError, match="Password is required."):
        AuthenticationService().create_with_profile(**data)

    assert UserRepository().count() == 0
    assert UserProfileRepository().count() == 0

def test_service_create_with_profie_success(clean_database):
    role_test = Role(id=1, name="user", description="Default user role")
    db.session.add(role_test)
    db.session.commit()

    data = {"name": "Test", "surname": "Foo", "email": "service_test@example.com", "password": "test1234"}

    AuthenticationService().create_with_profile(**data)

    assert UserRepository().count() == 1
    assert UserProfileRepository().count() == 1



# --- NUEVOS TESTS AÑADIDOS PARA COBERTURA (AuthenticationService) ---

# --- Cobertura de update_user ---

@patch('app.modules.auth.services.db.session')
def test_service_update_user_success(mock_db_session):
    """Prueba que update_user guarda y hace commit correctamente."""
    mock_user = MagicMock()
    auth_service = AuthenticationService()
    
    result = auth_service.update_user(mock_user)
    
    assert result is True
    mock_db_session.add.assert_called_once_with(mock_user)
    mock_db_session.commit.assert_called_once()
    mock_db_session.rollback.assert_not_called()


@patch('app.modules.auth.services.db.session')
def test_service_update_user_fail(mock_db_session):
    """Prueba que update_user hace rollback en caso de excepción."""
    mock_user = MagicMock()
    # Simular un fallo en el commit
    mock_db_session.commit.side_effect = Exception("DB Update Error")
    auth_service = AuthenticationService()
    
    result = auth_service.update_user(mock_user)
    
    assert result is False
    mock_db_session.rollback.assert_called_once()


# --- Cobertura de Métodos de Usuario Autenticado (Requiere Mockear Flask-Login) ---

@patch('app.modules.auth.services.current_user')
def test_service_get_authenticated_user_authenticated(mock_current_user):
    """Prueba que retorna el usuario autenticado."""
    mock_current_user.is_authenticated = True
    # Usamos el mock como el valor de retorno para simplificar
    auth_service = AuthenticationService()
    result = auth_service.get_authenticated_user()
    
    assert result is mock_current_user


@patch('app.modules.auth.services.current_user')
def test_service_get_authenticated_user_unauthenticated(mock_current_user):
    """Prueba que retorna None si no hay usuario autenticado."""
    mock_current_user.is_authenticated = False
    
    auth_service = AuthenticationService()
    result = auth_service.get_authenticated_user()
    
    assert result is None


@patch('app.modules.auth.services.current_user')
def test_service_get_authenticated_user_profile_authenticated(mock_current_user):
    """Prueba que retorna el perfil del usuario autenticado."""
    mock_profile = MagicMock()
    mock_current_user.is_authenticated = True
    mock_current_user.profile = mock_profile

    auth_service = AuthenticationService()
    result = auth_service.get_authenticated_user_profile()
    
    assert result is mock_profile


@patch('app.modules.auth.services.current_user')
def test_service_get_authenticated_user_profile_unauthenticated(mock_current_user):
    """Prueba que retorna None si no hay usuario autenticado."""
    mock_current_user.is_authenticated = False
    
    auth_service = AuthenticationService()
    result = auth_service.get_authenticated_user_profile()
    
    assert result is None


# --- Cobertura de Función de Correo Electrónico (Requiere Mockear Flask-Mail) ---

@patch('app.modules.auth.services.current_app')
def test_send_password_reset_email_no_mail_extension(mock_current_app):
    """Prueba el caso de fallo si Flask-Mail no está configurado (Línea 150)."""
    mock_current_app.extensions = {'mail': None}
    mock_current_app.logger = MagicMock()
    mock_user = MagicMock(email="test@fail.com")
    
    result = send_password_reset_email(mock_user)
    
    assert result is False
    mock_current_app.logger.error.assert_called_once()


@patch('app.modules.auth.services.current_app')
@patch('app.modules.auth.services.db.session')
def test_send_password_reset_email_success(mock_db_session, mock_current_app):
    """Prueba el envío exitoso del correo de restablecimiento (Líneas 148-183)."""
    
    # 1. Mocks de dependencias
    mock_mail = MagicMock()
    mock_current_app.extensions = {'mail': mock_mail}
    mock_current_app.config = {'MAIL_DEFAULT_SENDER': 'sender@test.com', 'FLASK_APP_NAME': 'Cerveza App'}
    mock_current_app.logger = MagicMock()
    
    mock_user = MagicMock(email="test@success.com")
    mock_user.generate_reset_token.return_value = "fake_token_456" # Simula la generación del token
    
    # 2. Mockear url_for y render_template
    with patch('app.modules.auth.services.url_for', return_value="/reset_token/fake_token_456") as mock_url_for, \
         patch('app.modules.auth.services.render_template', return_value="<h1>Email HTML Content</h1>") as mock_render:
        
        # 3. Ejecución
        result = send_password_reset_email(mock_user)
        
        # 4. Asertos
        assert result is True
        
        # Se generó y guardó el token
        mock_user.generate_reset_token.assert_called_once()
        mock_db_session.commit.assert_called_once()
        
        # Se construyó el mensaje
        mock_url_for.assert_called_with('auth.reset_token', token="fake_token_456", _external=True)
        mock_render.assert_called_once()
        
        # Se envió el correo
        mock_mail.send.assert_called_once()


@patch('app.modules.auth.services.current_app')
@patch('app.modules.auth.services.db.session')
def test_send_password_reset_email_failure_rollback(mock_db_session, mock_current_app):
    """Prueba que se hace rollback si falla la lógica interna (Líneas 185-194)."""
    
    mock_mail = MagicMock()
    mock_current_app.extensions = {'mail': mock_mail}
    mock_current_app.config = {'MAIL_DEFAULT_SENDER': 'sender@test.com', 'FLASK_APP_NAME': 'Cerveza App'}
    mock_current_app.logger = MagicMock()
    
    mock_user = MagicMock(email="test@fail_rollback.com")
    
    # Forzamos una excepción al intentar enviar (ej. fallo SMTP)
    mock_mail.send.side_effect = ConnectionRefusedError("Simulated Connection Error")
    
    # Ejecución
    result = send_password_reset_email(mock_user)
    
    # Asertos
    assert result is False
    mock_db_session.rollback.assert_called_once()
    mock_current_app.logger.error.assert_called_once()











    

MOCK_TOKEN = 'a' * 64

@patch('app.modules.auth.models.secrets.token_hex', return_value=MOCK_TOKEN)
@patch('app.modules.auth.models.datetime')
def test_generate_reset_token_success(mock_datetime, mock_token_hex):
    """
    Prueba que generate_reset_token establece el token y la expiración 
    (1 hora en el futuro) en el objeto User.
    """
    # 1. Mock Time: Definimos la hora 'actual' para el test
    now = datetime.datetime(2025, 1, 1, 10, 0, 0)
    mock_datetime.utcnow.return_value = now
    
    user = User()
    
    # 2. Ejecución
    token = user.generate_reset_token()
    expected_expiration = datetime.datetime(2025, 1, 1, 11, 0, 0) # 1 hora después
    
    # 3. Asertos
    assert token == MOCK_TOKEN
    assert user.reset_token == MOCK_TOKEN
    assert user.token_expiration == expected_expiration
    mock_token_hex.assert_called_once_with(32)


@patch('app.modules.auth.models.datetime')
@patch('app.modules.auth.models.User.query')
@patch('app.modules.auth.models.db.session')
def test_verify_reset_token_valid(mock_db_session, mock_query, mock_datetime):
    """
    Prueba que verify_reset_token retorna el usuario si el token es válido y no ha expirado.
    """
    VALID_TOKEN = 'valid_token'
    
    # 1. Mock Time (Activo)
    now = datetime.datetime(2025, 1, 1, 10, 30, 0)
    mock_datetime.utcnow.return_value = now
    
    # 2. Mock User: expira 5 min en el futuro (activo)
    mock_user = MagicMock(spec=User)
    mock_user.token_expiration = now + datetime.timedelta(minutes=5)
    
    mock_query.filter_by.return_value.first.return_value = mock_user

    # 3. Ejecución
    user = User.verify_reset_token(VALID_TOKEN)

    # 4. Asertos
    assert user is mock_user
    mock_db_session.commit.assert_not_called()


@patch('app.modules.auth.models.User.query')
def test_verify_reset_token_not_found(mock_query):
    """
    Prueba que verify_reset_token retorna None si el token no se encuentra en la base de datos.
    """
    # 1. Mock Query: retorna None
    mock_query.filter_by.return_value.first.return_value = None

    # 2. Ejecución
    user = User.verify_reset_token('non_existent_token')

    # 3. Asertos
    assert user is None


@patch('app.modules.auth.models.datetime')
@patch('app.modules.auth.models.User.query')
@patch('app.modules.auth.models.db.session')
def test_verify_reset_token_expired(mock_db_session, mock_query, mock_datetime):
    """
    Prueba que retorna None, limpia los campos del usuario y hace commit si el token expiró.
    """
    EXPIRED_TOKEN = 'expired_token'
    
    # 1. Mock Time (Expirado)
    now = datetime.datetime(2025, 1, 1, 10, 30, 0)
    mock_datetime.utcnow.return_value = now
    
    # 2. Mock User: expiró 5 min antes
    mock_user = MagicMock(spec=User)
    mock_user.reset_token = EXPIRED_TOKEN
    mock_user.token_expiration = now - datetime.timedelta(minutes=5) 
    
    mock_query.filter_by.return_value.first.return_value = mock_user

    # 3. Ejecución
    user = User.verify_reset_token(EXPIRED_TOKEN)

    # 4. Asertos
    assert user is None
    # Verifica que los campos fueron limpiados
    assert mock_user.reset_token is None
    assert mock_user.token_expiration is None
    # Verifica que se hizo commit de la limpieza
    mock_db_session.commit.assert_called_once()
    
@patch('app.modules.auth.models.datetime')
@patch('app.modules.auth.models.User.query')
@patch('app.modules.auth.models.db.session')
def test_verify_reset_token_no_expiration(mock_db_session, mock_query, mock_datetime):
    """
    Prueba que retorna None, limpia los campos del usuario y hace commit si 
    token_expiration es None (tratado como expirado).
    """
    INCONSISTENT_TOKEN = 'inconsistent_token'
    
    # 1. Mock Time 
    mock_datetime.utcnow.return_value = datetime.datetime(2025, 1, 1, 10, 30, 0)
    
    # 2. Mock User: expiration es None
    mock_user = MagicMock(spec=User)
    mock_user.reset_token = INCONSISTENT_TOKEN
    mock_user.token_expiration = None 
    
    mock_query.filter_by.return_value.first.return_value = mock_user

    # 3. Ejecución
    user = User.verify_reset_token(INCONSISTENT_TOKEN)

    # 4. Asertos
    assert user is None
    # Verifica que los campos fueron limpiados
    assert mock_user.reset_token is None
    assert mock_user.token_expiration is None
    # Verifica que se hizo commit de la limpieza
    mock_db_session.commit.assert_called_once()