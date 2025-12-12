import logging
import re
import random
from locust import HttpUser, task, between, SequentialTaskSet
from core.environment.host import get_host_for_locust_testing

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

class ExploreBehavior(SequentialTaskSet):
    
    def get_csrf_token(self, html_text):
        pattern = r'name=["\']csrf_token["\'][^>]*value=["\']([^"\']+)["\']'
        match = re.search(pattern, html_text, re.IGNORECASE)
        return match.group(1) if match else None

    def get_community_ids(self, html_text):

        pattern = r'<option\s+value="(\d+)"'
        ids = re.findall(pattern, html_text)
        return ids

    @task
    def filter_by_community(self):
        response = self.client.get("/explore")
        
        if response.status_code != 200:
            logger.warning(f"Fallo al cargar /explore: {response.status_code}")
            return 

        csrf_token = self.get_csrf_token(response.text)
        if not csrf_token:
            return

        community_ids = self.get_community_ids(response.text)
        
        if not community_ids:
            logger.warning("No hay comunidades en el desplegable para filtrar.")
            return

        selected_community_id = random.choice(community_ids)

        payload = {
            "query": "",
            "sorting": "newest",
            "publication_type": "any",
            "community_id": selected_community_id
        }

        headers = {
            "X-CSRFToken": csrf_token,
            "Referer": self.client.base_url + "/explore"
        }
        with self.client.post("/explore", json=payload, headers=headers, catch_response=True) as post_response:
            
            if post_response.status_code == 200:
                try:
                    results = post_response.json()

                    if isinstance(results, list):
                        num_results = len(results)
                        if num_results > 0:
                            logger.info(f"Comunidad ID {selected_community_id}: Encontrados {num_results} datasets.")
                        else:
                            logger.info(f"Comunidad ID {selected_community_id}: 0 resultados.")
                        
                        post_response.success()
                    else:
                        post_response.failure("El servidor respondió 200 pero no envió una lista JSON.")
                        
                except Exception as e:
                    logger.error(f"Error leyendo JSON: {e}")
                    post_response.failure("Respuesta no válida (No es JSON)")
            else:
                post_response.failure(f"Error HTTP {post_response.status_code}")

class ExploreUser(HttpUser):
    tasks = [ExploreBehavior]
    wait_time = between(2, 5)
    host = get_host_for_locust_testing()