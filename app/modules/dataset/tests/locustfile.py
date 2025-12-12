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

class GithubDatasetUploadWorkflow(SequentialTaskSet):
    email = None
    password = None

    # ---------- helpers ----------
    def _csrf_from_html(self, html_text: str):
        patterns = [
            r'value=["\']([^"\']+)["\'][^>]*name=["\']csrf_token["\']',
            r'name=["\']csrf_token["\'][^>]*value=["\']([^"\']+)["\']',
            r'id=["\']csrf_token["\'][^>]*value=["\']([^"\']+)["\']'
        ]
        for p in patterns:
            m = re.search(p, html_text, re.IGNORECASE)
            if m:
                return m.group(1)
        return None

    def _register(self) -> bool:
        r = self.client.get("/signup/", allow_redirects=True)
        if r.status_code != 200:
            logger.error(f"❌ No se pudo cargar /signup/ (status={r.status_code})")
            return False

        csrf = self._csrf_from_html(r.text)
        if not csrf:
            logger.error("❌ No CSRF en /signup/")
            return False

        data = {
            "email": self.email,
            "password": self.password,
            "confirm_password": self.password,
            "name": "Locust",
            "surname": "Tester",
            "csrf_token": csrf,
            "submit": "Submit",
        }

        with self.client.post("/signup/", data=data, catch_response=True, allow_redirects=True) as pr:
            # éxito típico: redirección o url distinta de signup
            if pr.status_code in (200, 302) and "signup" not in pr.url:
                pr.success()
                return True
            pr.failure(f"Fallo registro (status={pr.status_code}, url={pr.url})")
            return False

    def _login(self):
        for login_url in ("/auth/login", "/login"):
            r = self.client.get(login_url, allow_redirects=True)
            if r.status_code == 200:
                csrf = self._csrf_from_html(r.text)
                if not csrf:
                    return
                self.client.post(
                    login_url,
                    data={"email": self.email, "password": self.password, "csrf_token": csrf},
                    allow_redirects=True,
                )
                return

    def _make_csv(self, rows=200, cols=6) -> io.BytesIO:
        header = ",".join([f"c{i}" for i in range(cols)]) + "\n"
        body = []
        for r in range(rows):
            body.append(",".join([str((r + 7) * (c + 3)) for c in range(cols)]) + "\n")
        return io.BytesIO((header + "".join(body)).encode("utf-8"))

    def on_start(self):
        rid = str(uuid.uuid4())[:8]
        self.email = f"locust_{rid}@test.com"
        self.password = "password123"

        if not self._register():
            self._login()

    # ---------- task ----------
    @task
    def upload_dataset_github_permanent_backup(self):
        # 1) GET form
        r = self.client.get("/dataset/upload", allow_redirects=True)
        if "/login" in r.url:
            logger.error("❌ Redirige a login. Sesión no autenticada.")
            return
        if r.status_code != 200:
            logger.error(f"❌ GET /dataset/upload status={r.status_code}")
            return

        csrf = self._csrf_from_html(r.text)
        if not csrf:
            logger.error("❌ No CSRF en /dataset/upload")
            return

        # 2) POST form: storage_service=github y file en csv_file
        csv_bytes = self._make_csv(rows=350, cols=8)
        csv_bytes.seek(0)

        # NOTA: Los campos de metadatos exactos dependen de DataSetForm.
        # Dejamos los mínimos + algunos comunes; si tu form exige más, añade aquí los name="" exactos.
        form_data = {
            "csrf_token": csrf,
            "storage_service": "github",   # <-- CLAVE según tu controlador
            "submit": "Submit",
        }

        files = {
            "csv_file": ("dataset_locust.csv", csv_bytes, "text/csv")  # <-- CLAVE según tu controlador
        }

        with self.client.post(
            "/dataset/upload",
            data=form_data,
            files=files,
            catch_response=True,
            allow_redirects=True,
        ) as pr:
            # éxito: normalmente redirige a /doi/<...>/ o /dataset/unsynchronized/<id>/
            if pr.status_code in (200, 302) and (
                "/doi/" in pr.url or "/dataset/unsynchronized/" in pr.url or "/dataset/upload" not in pr.url
            ):
                pr.success()
                logger.info(f"✅ Upload GitHub OK -> {pr.url}")
            else:
                pr.failure(f"Upload GitHub FAIL (status={pr.status_code}, url={pr.url})")


class GithubDatasetUser(HttpUser):
    tasks = [GithubDatasetUploadWorkflow]
    wait_time = between(2, 5)
    host = get_host_for_locust_testing()