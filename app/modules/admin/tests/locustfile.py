import logging
import random
import re
from locust import HttpUser, task, between, SequentialTaskSet
from core.environment.host import get_host_for_locust_testing

logger = logging.getLogger()

def get_csrf_token(html_text):
    if not isinstance(html_text, str): return None
    patterns = [
        r'value=["\']([^"\']+)["\'][^>]*name=["\']csrf_token["\']',
        r'name=["\']csrf_token["\'][^>]*value=["\']([^"\']+)["\']',
        r'type=["\']hidden["\'][^>]*value=["\']([^"\']+)["\']'
    ]
    for p in patterns:
        match = re.search(p, html_text, re.IGNORECASE)
        if match: return match.group(1)
    return None

class AdminRoleChangeWorkflow(SequentialTaskSet):
    admin_email = "admin_test@test.com"
    admin_password = "password123"
    
    target_user_id = 2 
    target_user_email = "victim_selenium@test.com"

    
    def on_start(self):
        self._login()

    def _login(self):
        self.client.cookies.clear()
        login_url = "/login" 
        
        response = self.client.get(login_url, allow_redirects=True)
        if response.status_code != 200:
            logger.error(f"❌ Error cargando login. Status: {response.status_code}")
            return

        csrf_token = get_csrf_token(response.text)
        if not csrf_token:
            logger.error(f"❌ No CSRF token en {login_url}")
            return

        self.client.post(login_url, data={
            "email": self.admin_email,
            "password": self.admin_password,
            "csrf_token": csrf_token
        })
        logger.info(f"✅ Login enviado")

    def _load_edit_page(self):
        url = f"/admin/edit/{self.target_user_id}"
        response = self.client.get(url, name="/admin/edit/[id]")
        
        if "/login" in response.url:
            self._login()
            return None, None
            
        token = get_csrf_token(response.text)
        return url, token

    @task
    def set_standard_or_curator(self):
        url, token = self._load_edit_page()
        if not token: return

        new_role = random.choice(["2", "3"])
        
        data = {
            "email": self.target_user_email,
            "roles": new_role,
            "csrf_token": token,
            "submit": "Guardar Cambios"
        }
        
        with self.client.post(url, data=data, catch_response=True, allow_redirects=True, name="Positive: Standard/Curator") as res:
            if res.status_code == 200 and "actualizado exitosamente" in res.text:
                res.success()
            elif res.status_code == 302: 
                res.success()
            else:
                res.failure(f"Fallo al cambiar rol normal: {res.status_code}")

    @task
    def promote_to_admin(self):
        url, token = self._load_edit_page()
        if not token: return

        data = {
            "email": self.target_user_email,
            "roles": "1", 
            "csrf_token": token
        }
        
        with self.client.post(url, data=data, catch_response=True, allow_redirects=True, name="Positive: Promote to Admin") as res:
            if res.status_code in [200, 302]:
                res.success()
            else:
                res.failure(f"Fallo ascenso admin: {res.status_code}")

    @task
    def try_hack_invalid_role(self):
        url, token = self._load_edit_page()
        if not token: return

        data = {
            "email": self.target_user_email,
            "roles": "9999", 
            "csrf_token": token
        }
        
        with self.client.post(url, data=data, catch_response=True, allow_redirects=True, name="Negative: Invalid Role ID") as res:
            if "Not a valid choice" in res.text or "inválida" in res.text or "Error" in res.text:
                res.success() 
            elif res.status_code == 200 and "actualizado exitosamente" not in res.text:
                 res.success() 
            else:
                res.failure(f"⚠️ SEGURIDAD ROTA: El servidor aceptó el rol falso 9999. Status: {res.status_code}")

class AdminRoleUser(HttpUser):
    tasks = [AdminRoleChangeWorkflow]
    wait_time = between(2, 5)
    host = get_host_for_locust_testing()