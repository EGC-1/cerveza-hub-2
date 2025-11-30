import pytest
from flask import url_for

# Nuevas importaciones necesarias para los tests de servicio
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


def test_service_assign_role_to_user_fail_non_existent_user(clean_database):
    """Prueba que falla si el usuario no existe (retorna False)."""
    auth_service = AuthenticationService()
    result = auth_service.assign_role_to_user(9999, 1) 
    assert result is False


@patch('app.modules.auth.services.db.session.rollback')
def test_service_assign_role_to_user_fail_exception(mock_rollback, clean_database):
    """Prueba que se hace rollback si hay una excepción durante la actualización del rol."""
    auth_service = AuthenticationService()
    
    # Mockear el repositorio para que falle al obtener el usuario
    with patch.object(auth_service.repository, 'get_by_id', side_effect=Exception("DB Error")):
        with pytest.raises(Exception, match="DB Error"):
            auth_service.assign_role_to_user(1, 2)
            
    mock_rollback.assert_called_once()


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