from locust import HttpUser, TaskSet, task, between
from core.environment.host import get_host_for_locust_testing
from core.locust.common import fake, get_csrf_token
import random
import string

class SignupBehavior(TaskSet):
    
    def on_start(self):
        """Prepara el entorno para las pruebas de registro."""
        pass

    # --- CASO BUENO (Happy Path) ---
    @task(3) # Mayor peso, ocurre con más frecuencia
    def signup_success(self):
        """Registro con datos válidos y únicos."""
        response = self.client.get("/signup")
        csrf_token = get_csrf_token(response)
        
        email = fake.email()
        password = fake.password()
        
        with self.client.post(
            "/signup", 
            data={"email": email, "password": password, "surname": "Test", "name": "User", "csrf_token": csrf_token},
            catch_response=True
        ) as response:
            if response.status_code == 200 or response.status_code == 302:
                response.success()
            else:
                response.failure(f"Signup Good Case Failed: {response.status_code}")

    # --- CASO MALO (Negative Testing) ---
    @task(1)
    def signup_existing_email(self):
        """Intento de registro con email duplicado (debe fallar controladamente)."""
        response = self.client.get("/signup")
        csrf_token = get_csrf_token(response)
        
        # Usamos un email que sabemos que existe (o creamos uno al inicio)
        email = "user1@example.com" 
        
        with self.client.post(
            "/signup", 
            data={"email": email, "password": "pass", "surname": "Test", "name": "User", "csrf_token": csrf_token},
            catch_response=True
        ) as response:
            # Esperamos que la página cargue (200) pero contenga el mensaje de error
            if response.status_code == 200 and "in use" in response.text:
                response.success()
            elif response.status_code == 200:
                response.failure("Signup Bad Case Failed: Server accepted duplicate email")
            else:
                response.failure(f"Signup Bad Case Error: {response.status_code}")

    # --- CASO LÍMITE (Boundary Testing) ---
    @task(1)
    def signup_boundary_inputs(self):
        """Prueba de límites: Strings masivos."""
        
        # 1. ¡AGREGA ESTO! Limpia sesión anterior
        self.client.get("/logout") 

        # 2. Ahora carga el formulario
        response = self.client.get("/signup")
        csrf_token = get_csrf_token(response)
        
        # Límite superior: Contraseña de 5000 caracteres
        huge_password = ''.join(random.choices(string.ascii_letters, k=5000))
        
        with self.client.post(
            "/signup", 
            data={"email": "", "password": huge_password, "surname": "", "name": "", "csrf_token": csrf_token},
            catch_response=True
        ) as response:
            # Debe fallar validación pero NO dar error 500
            if response.status_code != 500:
                response.success()
            else:
                response.failure("Signup Boundary Failed: Server crashed (500) with huge payload")


class LoginBehavior(TaskSet):
    
    def on_start(self):
        self.client.get("/logout")

    #
    # --- CASO BUENO: Administrador ---
    @task(2)
    def login_admin_success(self):
        """Login correcto de admin y redirección al panel."""
        response = self.client.get("/login")
        csrf_token = get_csrf_token(response)

        with self.client.post(
            "/login", 
            data={"email": "admin@example.com", "password": "admin1234", "csrf_token": csrf_token},
            catch_response=True
        ) as response:
            # Verificamos si redirige o muestra contenido de admin
            if response.status_code == 200 and ("Dashboard" in response.text or "Admin" in response.text):
                response.success()
            elif "/admin" in response.url: 
                response.success()
            else:
                response.failure(f"Admin Login Failed: Redirected to {response.url}")
        
        self.client.get("/logout")

    # --- CASO MALO ---
    @task(1)
    def login_bad_credentials(self):
        """Login con contraseña incorrecta."""
        response = self.client.get("/login")
        csrf_token = get_csrf_token(response)

        with self.client.post(
            "/login", 
            data={"email": "user1@example.com", "password": "WRONG_PASSWORD", "csrf_token": csrf_token},
            catch_response=True
        ) as response:
            if "Invalid credentials" in response.text or "Error" in response.text:
                response.success()
            else:
                response.failure("Login Bad Case Failed: Logged in with wrong password")

    # --- CASO LÍMITE: Inyección SQL ---
    @task(1)
    def login_sql_injection_attempt(self):
        """Prueba de robustez: Inyección SQL."""
        response = self.client.get("/login")
        csrf_token = get_csrf_token(response)
        
        sql_payload = "' OR '1'='1"

        with self.client.post(
            "/login", 
            data={"email": sql_payload, "password": sql_payload, "csrf_token": csrf_token},
            catch_response=True
        ) as response:
            if response.status_code == 500:
                response.failure("Login Boundary Failed: SQL Injection caused 500")
            elif "Login" in response.text: 
                response.success()
            else:
                response.failure("Login Boundary Critical Failure: SQL Injection bypassed auth")

    # --- CASO LÍMITE: Seguridad Admin ---
    @task(1)
    def unauthorized_admin_access_attempt(self):
        """Usuario normal intenta forzar entrada al admin panel."""
        # 1. Login como usuario normal
        response = self.client.get("/login")
        csrf = get_csrf_token(response)
        self.client.post("/login", data={"email": "user1@example.com", "password": "1234", "csrf_token": csrf})

        # 2. Intento de acceso
        with self.client.get("/admin", catch_response=True) as response:
            if response.status_code in [403, 302] or ("Admin" not in response.text):
                response.success()
            else:
                response.failure("SECURITY BREACH: Standard user accessed Admin Panel!")
        
        self.client.get("/logout")


class AuthUser(HttpUser):
    """
    Esta es la clase que tu comando docker está llamando.
    Incluye tanto comportamientos de Registro como de Login (Admin y User).
    """
    tasks = [SignupBehavior, LoginBehavior]
    wait_time = between(5, 9) 
    host = get_host_for_locust_testing()


