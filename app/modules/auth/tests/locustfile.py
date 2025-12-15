from locust import HttpUser, TaskSet, task

from core.environment.host import get_host_for_locust_testing
from core.locust.common import fake, get_csrf_token


class SignupBehavior(TaskSet):
    def on_start(self):
        self.signup()

    @task
    def signup(self):
        response = self.client.get("/signup")
        csrf_token = get_csrf_token(response)

        response = self.client.post(
            "/signup", data={"email": fake.email(), "password": fake.password(), "csrf_token": csrf_token}
        )
        if response.status_code != 200:
            print(f"Signup failed: {response.status_code}")


class LoginBehavior(TaskSet):
    def on_start(self):
        self.ensure_logged_out()
        self.login()

    @task
    def ensure_logged_out(self):
        response = self.client.get("/logout")
        if response.status_code != 200:
            print(f"Logout failed or no active session: {response.status_code}")

    @task
    def login(self):
        response = self.client.get("/login")
        if response.status_code != 200 or "Login" not in response.text:
            print("Already logged in or unexpected response, redirecting to logout")
            self.ensure_logged_out()
            response = self.client.get("/login")

        csrf_token = get_csrf_token(response)

        response = self.client.post(
            "/login", data={"email": "user1@example.com", "password": "1234", "csrf_token": csrf_token}
        )
        if response.status_code != 200:
            print(f"Login failed: {response.status_code}")

class AuthenticatedUserBehavior(TaskSet):
    """
    Representa a un usuario que YA está registrado e intenta iniciar sesión
    y luego realiza alguna acción.
    """
    
    # 1. Login (Debe ser el primer paso)
    def on_start(self):
        """Intenta iniciar sesión inmediatamente."""
        self.login_and_ensure_authenticated()

    def login_and_ensure_authenticated(self):
        """Intenta iniciar sesión o lo repite si es necesario."""
        response = self.client.get("/login")
        
        csrf_token = get_csrf_token(response)

        # Aquí asumes que el usuario existe
        response = self.client.post(
            "/login", data={"email": "user1@example.com", "password": "1234", "csrf_token": csrf_token},
            name="/login [POST] AUTH"
        )
        if response.status_code != 200:
            print(f"Login failed on start: {response.status_code}")
        
    # 2. Tarea Común de Usuario (Dummy)
    @task(3)
    def visit_homepage(self):
        """Simula una tarea común que solo un usuario logueado haría."""
        self.client.get("/", name="/ [Homepage Logged In]")

    # 3. Logout (Salir)
    @task(1)
    def logout(self):
        """Sale del sistema y detiene esta TaskSet."""
        self.client.get("/logout")
        # Detener la TaskSet para que Locust "mate" a este usuario
        self.interrupt()





class RecoverPasswordBehavior(TaskSet):
    """
    Simulates the process of requesting a password recovery link and then
    resetting the password using a token.
    """

    # We use a dummy token for the /reset-password/<token> endpoint
    # since generating a real, valid token is an external dependency (User.verify_reset_token)
    DUMMY_RESET_TOKEN = "TEST_TOKEN_0001"
    TEST_EMAIL = "test_recover@example.com"
    NEW_PASSWORD = fake.password()

    @task(10) # Set a lower weight since recovery is less frequent than login/signup
    def forgot_password_request(self):
        """
        Simulates accessing /recover (GET) and submitting the form (POST).
        Corresponds to the forgot_password_request function in Flask.
        """
        # 1. GET /recover to get the form and CSRF token
        response = self.client.get("/recover", name="/recover [GET]")
        csrf_token = get_csrf_token(response)
        
        # We need a user to exist for the recovery process to succeed
        # In a real setup, ensure self.TEST_EMAIL is a registered user.
        
        # 2. POST /recover to submit the email
        response = self.client.post(
            "/recover",
            data={"email": self.TEST_EMAIL, "csrf_token": csrf_token},
            name="/recover [POST]"
        )
        
        # The expected behavior on success is a redirect (302) to /login
        # with a flash message, so we check for status code 302/200 
        # depending on how the framework handles the redirect in testing.
        if response.status_code not in [200, 302]:
             print(f"Forgot password request failed: {response.status_code}")

    @task(1) # This step is typically only done once per recovery, so a very low weight
    def reset_password_with_token(self):
        """
        Simulates accessing /reset-password/<token> (GET) and submitting the 
        new password (POST). Corresponds to the reset_token function in Flask.
        
        NOTE: This test assumes the application accepts a dummy token in a test
        environment or that the logic can be mocked. Otherwise, it will
        likely hit the "invalid or expired link" logic.
        """
        token_url = f"/reset-password/{self.DUMMY_RESET_TOKEN}"
        
        # 1. GET /reset-password/<token> to get the form and CSRF token
        response = self.client.get(token_url, name="/reset-password/[token] [GET]")
        
        # Check if the token was invalid/expired, which would result in a redirect
        if response.url != token_url:
            print(f"Token GET redirected to {response.url}, likely invalid/expired in testing.")
            return

        csrf_token = get_csrf_token(response)
        
        # 2. POST /reset-password/<token> to submit the new password
        response = self.client.post(
            token_url,
            data={"password": self.NEW_PASSWORD, "confirm_password": self.NEW_PASSWORD, "csrf_token": csrf_token},
            name="/reset-password/[token] [POST]"
        )

        if response.status_code not in [200, 302]:
            print(f"Password reset failed: {response.status_code}")



class AuthUser(HttpUser):
    tasks = [SignupBehavior, LoginBehavior]
    min_wait = 5000
    max_wait = 9000
    host = get_host_for_locust_testing()
