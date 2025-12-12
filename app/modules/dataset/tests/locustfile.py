import logging
import uuid
import io
import re
import time
from locust import HttpUser, task, between, SequentialTaskSet
from core.environment.host import get_host_for_locust_testing
from core.locust.common import get_csrf_token

class DatasetBehavior(SequentialTaskSet):
    @task
    def dataset(self):
        response = self.client.get("/dataset/upload")
        get_csrf_token(response)

class DatasetUser(HttpUser):
    tasks = [DatasetBehavior]
    min_wait = 5000
    max_wait = 9000
    host = get_host_for_locust_testing()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

class CommunityWorkflow(SequentialTaskSet):
    community_id = None
    email = None
    password = None
    username = None

    def on_start(self):
        random_id = str(uuid.uuid4())[:8]
        self.username = f"user_{random_id}"
        self.email = f"user_{random_id}@test.com"
        self.password = "password123"
        

        logged_in = self.register()
        

        if not logged_in:
            self.login()

    def get_csrf_token(self, html_text):
        patterns = [
            r'value=["\']([^"\']+)["\'][^>]*name=["\']csrf_token["\']',
            r'name=["\']csrf_token["\'][^>]*value=["\']([^"\']+)["\']',
            r'id=["\']csrf_token["\'][^>]*value=["\']([^"\']+)["\']'
        ]
        for p in patterns:
            match = re.search(p, html_text, re.IGNORECASE)
            if match: return match.group(1)
        return None

    def register(self):
        """Intenta registrar un usuario en /auth/signup/"""
        register_url = "/signup/"
        response = self.client.get(register_url)
        
        if response.status_code == 404:
            response = self.client.get("/signup/")
            register_url = "/signup/"
        
        if response.status_code != 200:
            logger.error(f" No se pudo cargar la página de registro. Status: {response.status_code}")
            return False

        csrf_token = self.get_csrf_token(response.text)
        if not csrf_token:
            logger.error("No CSRF token en registro.")
            return False
            
        data = {
            "email": self.email,
            "password": self.password,
            "confirm_password": self.password,
            "name": "Locust",
            "surname": "Tester",
            "csrf_token": csrf_token,
            "submit": "Submit" 
        }
        
        with self.client.post(register_url, data=data, catch_response=True) as post_response:
            if post_response.status_code == 200 and "signup" not in post_response.url:
                logger.info(f"✅ Usuario registrado: {self.email}")
                return True
            else:
                post_response.failure("Fallo en registro")
                return False

    def login(self):

        login_url = "/auth/login"
        response = self.client.get(login_url) 
        
        if response.status_code != 200:
             response = self.client.get("/login")
             login_url = "/login"

        csrf_token = self.get_csrf_token(response.text)
        if not csrf_token: return

        self.client.post(
            login_url, 
            data={
                "email": self.email, 
                "password": self.password,
                "csrf_token": csrf_token
            }
        )

    @task
    def create_community(self):
        logger.info("--- Tarea: Crear Comunidad ---")
        

        response = self.client.get("/community/create")
        
        if "/login" in response.url:
            logger.error("!!! Servidor pide Login. El registro/login falló.")
            return 

        csrf_token = self.get_csrf_token(response.text)
        if not csrf_token:
            return

        unique_name = f"Locust_{str(uuid.uuid4())[:6]}"
        img_byte_arr = io.BytesIO(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x03\x01\x01\x00\x18\xdd\x8d\xb0\x00\x00\x00\x00IEND\xaeB`\x82')

        with self.client.post(
            "/community/create",
            data={
                "name": unique_name,
                "description": "Load Test Real POST",
                "csrf_token": csrf_token,
                "submit": "Create Community"
            },
            files={"logo": ("logo.png", img_byte_arr, "image/png")},
            catch_response=True,
            allow_redirects=True 
        ) as post_response:
            if post_response.status_code == 200 and "/community/create" not in post_response.url:
                match = re.search(r"/community/(\d+)", post_response.url)
                if match:
                    self.community_id = match.group(1)
                    post_response.success()
                    logger.info(f"✅ ÉXITO REAL: Comunidad creada ID {self.community_id}")
                else:
                    post_response.success()
                    self.community_id = None 
            else:
                post_response.failure(f"Fallo crear comunidad. URL: {post_response.url}")

    @task
    def associate_datasets(self):
        if not self.community_id:
            return

        logger.info(f"--- Tarea: Asociar Datasets (Comunidad {self.community_id}) ---")
        
        url = f"/community/{self.community_id}/manage_datasets"
        response = self.client.get(url)
        
        if response.status_code != 200: 
            return
            
        csrf_token = self.get_csrf_token(response.text)
        if not csrf_token:
            return
        dataset_ids = ["1", "2"] 
        assoc_resp = self.client.post(
            url,
            data={"datasets": dataset_ids, "csrf_token": csrf_token, "submit": "Save Datasets"}
        )
        
        if assoc_resp.status_code == 200:
            logger.info("Datasets asociados correctamente.")
        
        self.community_id = None

class CommunityUser(HttpUser):
    tasks = [CommunityWorkflow]
    wait_time = between(2, 5) 
    host = get_host_for_locust_testing()