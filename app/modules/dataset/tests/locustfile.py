import logging
from gevent.lock import Semaphore
import uuid
import io
import re
import gevent
import time
import requests
from locust import HttpUser, task, between, SequentialTaskSet
from locust.clients import HttpSession
from core.environment.host import get_host_for_locust_testing


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

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
                logger.info(f"Usuario registrado: {self.email}")
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
                    logger.info(f"ÉXITO REAL: Comunidad creada ID {self.community_id}")
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
    

# ==============================================================================
#  Download Counter with Shared Dataset ID (Prefix: DC_)
# ==============================================================================

DC_SHARED_DATASET_ID = None
DC_CREATION_LOCK = Semaphore()
DC_DATASET_CREATED = False
DC_SHARED_TITLE = f"COUNTER_LOCUST_TEST_{str(uuid.uuid4())[:6]}"

def get_csrf_token(html_text):
    if not isinstance(html_text, str): return None
    match = re.search(r'name=["\']csrf_token["\'][^>]*value=["\']([^"\']+)["\']', html_text)
    return match.group(1) if match else None

class SharedDownloadWorkflow(SequentialTaskSet):
    email = None
    password = None

    def on_start(self):
        rid = str(uuid.uuid4())[:8]
        self.email = f"user_{rid}@test.com"
        self.password = "1234"

        r = self.client.get("/signup/")
        csrf = get_csrf_token(r.text)
        if csrf:
            self.client.post("/signup/", data={
                "email": self.email, "password": self.password, 
                "confirm_password": self.password, "name": "Load", 
                "surname": "Tester", "csrf_token": csrf, "submit": "Submit"
            })
            self.client.post("/login", data={
                "email": self.email, "password": self.password, "csrf_token": csrf
            })

    @task
    def coordinator_task(self):
        global DC_SHARED_DATASET_ID, DC_DATASET_CREATED

        if DC_SHARED_DATASET_ID:
            self._view_dataset()
            self._download_target()
            return

        if not DC_DATASET_CREATED:
            if DC_CREATION_LOCK.acquire(blocking=False):
                try:
                    if not DC_DATASET_CREATED:
                        logger.info(f"[LIDER] {self.email} creando dataset maestro para contador de descargas...")
                        self._create_master_dataset()
                        DC_DATASET_CREATED = True
                finally:
                    DC_CREATION_LOCK.release()
            else:
                gevent.sleep(1)
        else:
            gevent.sleep(1)

    def _create_master_dataset(self):
        global DC_SHARED_DATASET_ID
        r = self.client.get("/dataset/upload")
        csrf = get_csrf_token(r.text)
        if not csrf: return

        header = "name,brewery,style,abv,ibu\n"
        rows_data = [
            "Heineken,Heineken Brouwerijen,Lager,5.0,19",
            "Corona,Grupo Modelo,Lager,4.5,18",
            "Mahou,Mahou San Miguel,Pilsner,5.5,25",
            "Guinness,St James Gate,Stout,4.2,45",
            "Stella Artois,Anheuser-Busch,Pilsner,5.0,24"
        ]
        csv_content = header
        for _ in range(12): 
            for row in rows_data:
                csv_content += f"{row}\n"
        csv_file = io.BytesIO(csv_content.encode('utf-8'))
        
        files = {"csv_file": ("master.csv", csv_file, "text/csv")}
        
        data = {
            "title": DC_SHARED_TITLE,
            "desc": "Selenium Test Description equivalent",
            "publication_type": "annotationcollection", 
            "tags": "load",
            "storage_service": "zenodo", 
            "agreeCheckbox": "y",
            "authors-0-name": "Locust Admin", 
            "authors-0-affiliation": "Lab",
            "authors-0-orcid": "",
            "csrf_token": csrf,
            "submit": "Submit"
        }
        
        with self.client.post("/dataset/upload", data=data, files=files, catch_response=True, allow_redirects=True, name="/dataset/upload (Create DC Master)") as res:
            if res.status_code in (200, 302):
                if res.status_code == 200 and "upload" in res.url:
                    errores = re.findall(r'class="text-danger">\s*(.*?)\s*<', res.text)
                    logger.error(f"[CREAR DC] Falló validación: {errores}")
                    res.failure(f"Validation Error")
                    return

                res.success()
                m = re.search(r"/dataset/(?:unsynchronized/|download/)?(\d+)", res.url)
                if m:
                    DC_SHARED_DATASET_ID = m.group(1)
                    logger.info(f"[CREADO DC] ID: {DC_SHARED_DATASET_ID}")
            else:
                logger.error(f"[CREAR DC] Error HTTP {res.status_code}")
                res.failure(f"HTTP {res.status_code}")

        if not DC_SHARED_DATASET_ID:
            self._find_id_in_list_fallback()

    def _find_id_in_list_fallback(self):
        global DC_SHARED_DATASET_ID
        with self.client.get("/dataset/list", catch_response=True, name="/dataset/list (Fallback)") as list_res:
            if DC_SHARED_TITLE in list_res.text:
                m = re.search(r'href=[\'"]/dataset/download/(\d+)[\'"]', list_res.text)
                if m:
                    DC_SHARED_DATASET_ID = m.group(1)
                    logger.info(f"[ENCONTRADO DC] ID: {DC_SHARED_DATASET_ID}")
                    list_res.success()
                else:
                    list_res.failure("Button missing")
            else:
                list_res.success()
                
    def _view_dataset(self):
        url = f"/dataset/unsynchronized/{DC_SHARED_DATASET_ID}/"
        with self.client.get(url, catch_response=True, name="/dataset/view [DC]") as res:
            if res.status_code in (200, 302):
                res.success()
            else:
                res.failure(f"View failed: {res.status_code}")

    def _download_target(self):
        url = f"/dataset/download/{DC_SHARED_DATASET_ID}"
        with self.client.get(url, catch_response=True, name="/dataset/download [DC]") as response:
            if response.status_code in (200, 302):
                response.success()
            else:
                response.failure(f"Error {response.status_code}")

class DownloadCounterUser(HttpUser):
    tasks = [SharedDownloadWorkflow]
    wait_time = between(1, 3)
    host = get_host_for_locust_testing()


# ==============================================================================
#  Statistics Download Counter with Shared Dataset ID Prefix: STATS_
# ==============================================================================

STATS_SHARED_DATASET_ID = None
STATS_CREATION_LOCK = Semaphore()
STATS_DATASET_CREATED = False
STATS_SHARED_TITLE = f"STATS_LOCUST_{str(uuid.uuid4())[:6]}"

class StatsWorkflow(SequentialTaskSet):
    email = None
    password = None

    def on_start(self):
        rid = str(uuid.uuid4())[:8]
        self.email = f"stats_{rid}@test.com"
        self.password = "1234"
        
        self.register()
        self.login()

    def register(self):
        r = self.client.get("/signup/")
        csrf = get_csrf_token(r.text)
        if csrf:
            self.client.post("/signup/", data={
                "email": self.email, "password": self.password, 
                "confirm_password": self.password, "name": "Load", 
                "surname": "Unique", "csrf_token": csrf, "submit": "Submit"
            })

    def login(self):
        r = self.client.get("/auth/login")
        if r.status_code != 200: r = self.client.get("/login")
        csrf = get_csrf_token(r.text)
        if csrf:
            self.client.post("/login", data={
                "email": self.email, "password": self.password, "csrf_token": csrf
            })

    @task
    def flow_logic(self):
        global STATS_SHARED_DATASET_ID, STATS_DATASET_CREATED

        if not STATS_SHARED_DATASET_ID:
            if not STATS_DATASET_CREATED:
                if STATS_CREATION_LOCK.acquire(blocking=False):
                    try:
                        if not STATS_DATASET_CREATED:
                            logger.info(f"[LIDER STATS] {self.email} creando dataset maestro...")
                            self._create_master_dataset()
                            STATS_DATASET_CREATED = True
                    finally:
                        STATS_CREATION_LOCK.release()
                else:
                    gevent.sleep(1)
            else:
                gevent.sleep(1) 
            
            if not STATS_SHARED_DATASET_ID:
                 return 

        self._view_dataset()
        
        self._download_dataset() 
        logger.info(f"[STATS] {self.email} descargó el dataset {STATS_SHARED_DATASET_ID}")
        
        self._download_dataset() 
        
        self.interrupt()
        
    def _create_master_dataset(self):
        global STATS_SHARED_DATASET_ID
        
        r = self.client.get("/dataset/upload")
        if "/login" in r.url: return
        csrf = get_csrf_token(r.text)
        if not csrf: return

        header = "name,brewery,style,abv,ibu\n"
        rows_data = ["Heineken,Heineken,Lager,5.0,19", "Corona,Modelo,Lager,4.5,18"]
        csv_content = header
        for _ in range(20): 
            for row in rows_data:
                csv_content += f"{row}\n"
        csv_file = io.BytesIO(csv_content.encode('utf-8'))
        
        files_dict = {"csv_file": ("master_stats.csv", csv_file, "text/csv")}
        data = {
            "title": STATS_SHARED_TITLE, "desc": "Stats", "publication_type": "annotationcollection", 
            "tags": "stats", "storage_service": "zenodo", "agreeCheckbox": "y", 
            "authors-0-name": "Bot", "authors-0-affiliation": "Lab", "authors-0-orcid": "", 
            "csrf_token": csrf, "submit": "Submit"
        }
        
        need_fallback = False

        with self.client.post(
            "/dataset/upload", 
            data=data, 
            files=files_dict, 
            catch_response=True, 
            allow_redirects=True, 
            name="/dataset/upload (Create Stats Master)"
        ) as res:
            
            if res.status_code in (200, 302) and "upload" not in res.url:
                m = re.search(r"/dataset/(?:unsynchronized/|download/)?(\d+)", res.url)
                if m: 
                    STATS_SHARED_DATASET_ID = m.group(1)
                    logger.info(f"[CREADO STATS] ID: {STATS_SHARED_DATASET_ID}")
                    res.success()
                else: 
                    need_fallback = True
                    res.success() 
            else:
                logger.error(f"[STATS] Fallo subida: {res.status_code}")
                res.failure(f"HTTP {res.status_code}")

        if need_fallback:
            self._find_id_fallback()

    def _find_id_fallback(self):
        global STATS_SHARED_DATASET_ID
        with self.client.get("/dataset/list", name="/dataset/list (Fallback Stats)") as res:
            if STATS_SHARED_TITLE in res.text:
                m = re.search(r'href=[\'"]/dataset/download/(\d+)[\'"]', res.text)
                if m: 
                    STATS_SHARED_DATASET_ID = m.group(1)
                    logger.info(f"[ENCONTRADO STATS] ID: {STATS_SHARED_DATASET_ID}")

    def _view_dataset(self):
        if not STATS_SHARED_DATASET_ID: return
        url = f"/dataset/unsynchronized/{STATS_SHARED_DATASET_ID}/"
        with self.client.get(url, catch_response=True, name="/dataset/view [Stats]") as res:
            if res.status_code in (200, 302):
                res.success()
            else:
                res.failure(f"View failed: {res.status_code}")

    def _download_dataset(self):
        if not STATS_SHARED_DATASET_ID: return
        url = f"/dataset/download/{STATS_SHARED_DATASET_ID}"
        with self.client.get(url, catch_response=True, name="/dataset/download [Stats]") as res:
            if res.status_code in (200, 302):
                res.success()
            else:
                res.failure(f"Download failed: {res.status_code}")
                
class StatsUser(HttpUser):
    tasks = [StatsWorkflow]
    wait_time = between(1, 3)
    host = get_host_for_locust_testing()