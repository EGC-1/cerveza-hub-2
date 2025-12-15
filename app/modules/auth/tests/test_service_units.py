import pytest
from unittest.mock import patch, MagicMock
from flask import url_for

# --- Constantes y Mocks Auxiliares ---
AUTH_ROUTES_PATH = 'app.modules.auth.routes'
AUTH_SERVICE_PATH = f'{AUTH_ROUTES_PATH}.authentication_service'
SEND_EMAIL_PATH = f'{AUTH_ROUTES_PATH}.send_password_reset_email'
REQUEST_FORM_PATH = f'{AUTH_ROUTES_PATH}.RequestResetForm'
RESET_FORM_PATH = f'{AUTH_ROUTES_PATH}.ResetPasswordForm'
USER_CLASS_PATH = f'{AUTH_ROUTES_PATH}.User'
CURRENT_USER_PATH = f'{AUTH_ROUTES_PATH}.current_user'


class MockRequestResetForm:
    """Mock para el formulario de solicitud de restablecimiento."""
    def __init__(self, data=None, is_valid=False):
        self.data = data or {}
        self._is_valid = is_valid
        # Simula el campo email.data. FIX: Add .errors and .label 
        # as Jinja templates often require them for error display, even if empty.
        self.email = MagicMock(
            data=self.data.get('email'),
            errors=[], 
            label=MagicMock(text='Email') 
        )

    def validate_on_submit(self):
        return self._is_valid
    
    def hidden_tag(self):
        """Necesario para que Jinja renderice {{ form.hidden_tag() }} sin error."""
        return ""


class MockResetPasswordForm(MockRequestResetForm):
    """Mock para el formulario de nueva contraseña."""
    def __init__(self, data=None, is_valid=False):
        # Initialize attributes without calling super() to avoid conflicting 'email' field
        self.data = data or {}
        self._is_valid = is_valid
        
        # Simula el campo password.data. FIX: Add .errors and .label
        self.password = MagicMock(
            data=self.data.get('password'),
            errors=[], 
            label=MagicMock(text='Nueva Contraseña')
        )
        
        # Assume standard 'confirm_password' field, also with FIX attributes
        self.confirm_password = MagicMock(
            data=self.data.get('confirm_password'),
            errors=[], 
            label=MagicMock(text='Confirmar Contraseña')
        )
        # Note: hidden_tag is inherited from MockRequestResetForm

    def validate_on_submit(self):
        return self._is_valid


class MockUser:
    """Mock para simular el objeto User."""
    def __init__(self, id=1, email="test@user.com"):
        self.id = id
        self.email = email
        self.is_authenticated = False
        self.set_password = MagicMock()
        
    @staticmethod
    def verify_reset_token(token):
        return None

# --- Tests para forgot_password_request (@auth_bp.route("/recover")) ---

@patch(CURRENT_USER_PATH)
def test_recover_password_get_unauthenticated(mock_current_user, test_client):
    """Verifica que un GET a /recover muestre el formulario si el usuario NO está autenticado."""
    mock_current_user.is_authenticated = False
    response = test_client.get("/recover")
    
    assert response.status_code == 200
    # CORRECCIÓN: Buscamos contenido del HTML, no el nombre del archivo.
    # Buscamos textos que sabemos que están en tu template según el log de error
    assert b"Olvidaste tu Contrase" in response.data 

@patch(CURRENT_USER_PATH)
def test_recover_password_get_authenticated_redirects(mock_current_user, test_client):
    """Verifica que un GET a /recover redirija a / si el usuario SÍ está autenticado."""
    mock_current_user.is_authenticated = True
    response = test_client.get("/recover", follow_redirects=False)
    
    assert response.status_code == 302
    assert response.location == url_for('public.index')

@patch(SEND_EMAIL_PATH)
@patch(AUTH_SERVICE_PATH)
@patch(REQUEST_FORM_PATH)
@patch(CURRENT_USER_PATH)
def test_recover_password_post_success(mock_current_user, MockRequestForm, mock_auth_service, mock_send_email, test_client):
    """Verifica POST con email existente y envío de correo exitoso."""
    mock_current_user.is_authenticated = False
    test_email = 'user@exists.com'
    mock_user = MockUser(email=test_email)
    
    # Configurar Mocks
    MockRequestForm.return_value = MockRequestResetForm(data={'email': test_email}, is_valid=True)
    mock_auth_service.get_user_by_email.return_value = mock_user
    mock_send_email.return_value = True 
    
    response = test_client.post("/recover", data={'email': test_email}, follow_redirects=False)
    
    mock_auth_service.get_user_by_email.assert_called_with(test_email)
    mock_send_email.assert_called_once_with(mock_user)
    assert response.status_code == 302
    assert response.location == url_for('auth.login')


# --- Tests para reset_token (@auth_bp.route("/reset-password/<string:token>")) ---

TEST_TOKEN = 'a_valid_token_123'

@patch(CURRENT_USER_PATH)
def test_reset_token_get_authenticated_redirects(mock_current_user, test_client):
    """Verifica que un usuario autenticado es redirigido."""
    mock_current_user.is_authenticated = True
    response = test_client.get(f"/reset-password/{TEST_TOKEN}", follow_redirects=False)
    
    assert response.status_code == 302
    assert response.location == url_for('public.index')


@patch(USER_CLASS_PATH)
@patch(CURRENT_USER_PATH)
def test_reset_token_get_invalid_token_redirects(mock_current_user, MockUserClass, test_client):
    """Verifica GET con token inválido."""
    mock_current_user.is_authenticated = False
    MockUserClass.verify_reset_token.return_value = None
    
    response = test_client.get(f"/reset-password/{TEST_TOKEN}", follow_redirects=False)
    
    MockUserClass.verify_reset_token.assert_called_once_with(TEST_TOKEN)
    assert response.status_code == 302
    assert response.location == url_for('auth.forgot_password_request')



@patch(AUTH_SERVICE_PATH)
@patch(RESET_FORM_PATH)
@patch(USER_CLASS_PATH)
@patch(CURRENT_USER_PATH)
def test_reset_token_post_success(mock_current_user, MockUserClass, MockResetForm, mock_auth_service, test_client):
    """Verifica POST exitoso."""
    mock_current_user.is_authenticated = False
    new_password = 'newsecurepassword123'
    mock_user_instance = MockUser()
    
    MockUserClass.verify_reset_token.return_value = mock_user_instance
    MockResetForm.return_value = MockResetPasswordForm(data={'password': new_password}, is_valid=True)
    mock_auth_service.update_user.return_value = True 
    
    response = test_client.post(f"/reset-password/{TEST_TOKEN}", 
                                 data={'password': new_password}, 
                                 follow_redirects=False)
    
    mock_user_instance.set_password.assert_called_with(new_password)
    mock_auth_service.update_user.assert_called_with(mock_user_instance)
    assert response.status_code == 302
    assert response.location == url_for('auth.login')


@patch(AUTH_SERVICE_PATH)
@patch(RESET_FORM_PATH)
@patch(USER_CLASS_PATH)
@patch(CURRENT_USER_PATH)
def test_reset_token_post_update_failure(mock_current_user, MockUserClass, MockResetForm, mock_auth_service, test_client):
    """Verifica POST: token válido pero fallo en actualización."""
    mock_current_user.is_authenticated = False
    new_password = 'newsecurepassword123'
    mock_user_instance = MockUser()
    
    MockUserClass.verify_reset_token.return_value = mock_user_instance
    MockResetForm.return_value = MockResetPasswordForm(data={'password': new_password}, is_valid=True)
    mock_auth_service.update_user.return_value = False 
    
    response = test_client.post(f"/reset-password/{TEST_TOKEN}", 
                                 data={'password': new_password}, 
                                 follow_redirects=False)
    
    mock_user_instance.set_password.assert_called_with(new_password)
    mock_auth_service.update_user.assert_called_with(mock_user_instance)
    assert response.status_code == 302
    assert response.location == url_for('auth.reset_token', token=TEST_TOKEN)


