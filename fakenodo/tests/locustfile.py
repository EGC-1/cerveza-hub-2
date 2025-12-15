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

def get_csrf_token(html_text):
    if not isinstance(html_text, str): return None
    match = re.search(r'name=["\']csrf_token["\'][^>]*value=["\']([^"\']+)["\']', html_text)
    return match.group(1) if match else None

FN_SHARED_ID = None
FN_LOCK = Semaphore()
FN_CREATED = False
FN_TITLE = f"FAKENODO_LINK_TEST_{str(uuid.uuid4())[:6]}"

class FakenodoTrafficWorkflow(SequentialTaskSet):
    email = None
    password = None

    def on_start(self):
        rid = str(uuid.uuid4())[:8]
        self.email = f"fn_user_{rid}@test.com"
        self.password = "1234"
        self.register()
        self.login()

    def register(self):
        r = self.client.get("/signup/")
        csrf = get_csrf_token(r.text)
        if csrf:
            self.client.post("/signup/", data={
                "email": self.email, "password": self.password, 
                "confirm_password": self.password, "name": "Fakenodo", 
                "surname": "Tester", "csrf_token": csrf, "submit": "Submit"
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
        global FN_SHARED_ID, FN_CREATED

        if not FN_SHARED_ID:
            if not FN_CREATED:
                if FN_LOCK.acquire(blocking=False):
                    try:
                        if not FN_CREATED:
                            logger.info(f"[LIDER FN] Creando dataset en Zenodo/Fakenodo...")
                            self._create_master_dataset_zenodo()
                            FN_CREATED = True
                    finally:
                        FN_LOCK.release()
                else:
                    gevent.sleep(1)
            else:
                gevent.sleep(1)
            
            if not FN_SHARED_ID: return

        
        html_content = self._view_dataset_detail()
        
        if html_content:
            self._click_fakenodo_link(html_content)
        
        self.interrupt()

    def _create_master_dataset_zenodo(self):
        global FN_SHARED_ID
        
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
        
        files_dict = {"csv_file": ("master_zenodo.csv", csv_file, "text/csv")}
        
        data = {
            "title": FN_TITLE, 
            "desc": "Fakenodo Integration Test", 
            "publication_type": "annotationcollection", 
            "tags": "zenodo", 
            "storage_service": "zenodo", 
            "agreeCheckbox": "y", 
            "authors-0-name": "Bot", 
            "authors-0-affiliation": "Locust", 
            "authors-0-orcid": "", 
            "csrf_token": csrf, 
            "submit": "Submit"
        }
        
        need_fallback = False

        with self.client.post(
            "/dataset/upload", 
            data=data, 
            files=files_dict, 
            catch_response=True, 
            allow_redirects=True, 
            name="/dataset/upload (Create Zenodo Master)"
        ) as res:
            if res.status_code in (200, 302) and "upload" not in res.url:
                m = re.search(r"/dataset/(?:unsynchronized/|download/)?(\d+)", res.url)
                if m: 
                    FN_SHARED_ID = m.group(1)
                    logger.info(f"[CREADO FN] Dataset ID: {FN_SHARED_ID} (en Zenodo)")
                    res.success()
                else:
                    need_fallback = True
                    res.success() 
            else:
                logger.error(f"[FN] Fallo subida: {res.status_code}")
                res.failure(f"HTTP {res.status_code}")

        if need_fallback:
            self._find_id_fallback()

    def _find_id_fallback(self):
        global FN_SHARED_ID
        with self.client.get("/dataset/list", name="/dataset/list (Fallback FN)") as res:
            if FN_TITLE in res.text:
                m = re.search(r'href=[\'"]/dataset/download/(\d+)[\'"]', res.text)
                if m: FN_SHARED_ID = m.group(1)

    def _view_dataset_detail(self):
        """Visita la página de detalle en UVLHub y devuelve el HTML."""
        if not FN_SHARED_ID: return None
        
        url = f"/dataset/{FN_SHARED_ID}/" 
        
        with self.client.get(url, catch_response=True, allow_redirects=True, name="/dataset/[id] (CSVHub View)") as res:
            if res.status_code == 200:
                res.success()
                return res.text
            elif res.status_code == 404:
     
                res.failure("Dataset Detail 404")
                return None
            else:
                res.failure(f"View Failed: {res.status_code}")
                return None

    def _click_fakenodo_link(self, html_content):
        """Busca el link a fakenodo en el HTML y hace la petición."""
        
        match = re.search(r'href=["\']([^"\']*/records/[^"\']*)["\']', html_content)
        
        if match:
            fakenodo_url = match.group(1)
 
            if "localhost" in fakenodo_url:
                fakenodo_url = fakenodo_url.replace("localhost", "fakenodo")

            with self.client.get(fakenodo_url, catch_response=True, name="External: Fakenodo Record View") as res:
                if res.status_code == 200:
                    res.success()
                else:
                    logger.warning(f"Fakenodo link falló ({res.status_code}): {fakenodo_url}")
                    res.failure(f"Fakenodo Access Error {res.status_code}")
        else:
            logger.warning("No se encontró el enlace a Zenodo/Fakenodo en la página de detalle.")

class FakenodoUser(HttpUser):
    tasks = [FakenodoTrafficWorkflow]
    wait_time = between(2, 5)
    host = get_host_for_locust_testing()