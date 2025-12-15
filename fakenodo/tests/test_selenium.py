import time
import os
import uuid
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from core.selenium.common import close_driver, initialize_driver

FAKENODO_HOST = "http://fakenodo:5000"


def wait_for_page_to_load(driver, timeout=4):
    try:
        WebDriverWait(driver, timeout).until(
            lambda driver: driver.execute_script("return document.readyState") == "complete"
        )
    except:
        pass


def test_fakenodo_visual_workflow_selenium():
    '''
    Test de Selenium para Fakenodo.
    1. Crea un depósito, sube archivo y publica vía API (Simulación de backend).
    2. Usa Selenium para visitar la página pública del registro.
    3. Verifica que el Título, el DOI y el Archivo se muestran correctamente en el HTML.
    '''
    driver = initialize_driver()

    unique_suffix = uuid.uuid4().hex[:6]
    dataset_title = f"Selenium Fakenodo Test {unique_suffix}"
    filename = f"test_file_{unique_suffix}.txt"

    deposit_id = None

    try:
        print(f"--- 1. PREPARACIÓN DE DATOS (Vía API) ---")

        payload = {
            "metadata": {
                "title": dataset_title,
                "upload_type": "dataset",
                "description": "Created by Selenium Test Script",
                "creators": [{"name": "Selenium Bot", "affiliation": "Automated Testing"}]
            }
        }
        resp = requests.post(f"{FAKENODO_HOST}/api/deposit/depositions", json=payload)
        if resp.status_code != 201:
            raise Exception(f"Fallo al crear depósito en API Fakenodo: {resp.status_code}")

        data = resp.json()
        deposit_id = data['id']
        print(f"Depósito creado ID: {deposit_id}")

        files = {'file': (filename, 'Contenido de prueba para validación visual')}
        resp_file = requests.post(
            f"{FAKENODO_HOST}/api/deposit/depositions/{deposit_id}/files",
            files=files
        )
        if resp_file.status_code != 201:
            raise Exception("Fallo al subir archivo a Fakenodo API")

        resp_pub = requests.post(
            f"{FAKENODO_HOST}/api/deposit/depositions/{deposit_id}/actions/publish"
        )
        if resp_pub.status_code != 202:
            raise Exception("Fallo al publicar en Fakenodo API")

        print("Datos preparados y publicados.")

        target_url = f"{FAKENODO_HOST}/records/{deposit_id}"
        print(f"Navegando a: {target_url}")

        driver.get(target_url)
        wait_for_page_to_load(driver)


        # Verificar Título
        try:
            h1_element = WebDriverWait(driver, 5).until(
                EC.visibility_of_element_located((By.TAG_NAME, "h1"))
            )
            if h1_element.text == dataset_title:
                print(f"¡ÉXITO! Título encontrado: '{dataset_title}'")
            else:
                raise Exception(
                    f"Título incorrecto. Esperado: '{dataset_title}', "
                    f"Obtenido: '{h1_element.text}'"
                )
        except TimeoutException:
            raise Exception("No se encontró el título (H1) en la página.")

        # Verificar Estado
        try:
            badge = driver.find_element(By.CLASS_NAME, "bg-success")
            if "Published" in badge.text:
                print("¡ÉXITO! Badge 'Published' visible.")
            else:
                raise Exception("El estado no aparece como Published.")
        except:
            raise Exception("No se encontró el badge de estado.")

        # Verificar DOI 
        try:
            doi_element = driver.find_element(By.CLASS_NAME, "doi-badge")
            expected_doi = f"10.5281/zenodo.{deposit_id}"

            if expected_doi in doi_element.text:
                print(f"¡ÉXITO! DOI correcto encontrado: {expected_doi}")
            else:
                print(
                    f"ERROR VISUAL: DOI esperado '{expected_doi}' "
                    f"no coincide con '{doi_element.text}'"
                )
                raise Exception("Fallo en verificación de DOI.")
        except:
            raise Exception("No se encontró el elemento del DOI.")

        # Verificar Archivo en la lista
        try:
            file_list = driver.find_element(By.CLASS_NAME, "list-group")
            if filename in file_list.text:
                print(f"¡ÉXITO! El archivo '{filename}' aparece en la lista.")
            else:
                raise Exception(
                    f"El archivo '{filename}' no aparece en la interfaz."
                )
        except:
            raise Exception("No se encontró la lista de archivos.")

    finally:
        close_driver(driver)