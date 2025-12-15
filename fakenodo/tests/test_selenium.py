import time
import os
import uuid
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from app import app, db
from app.modules.dataset.models import DataSet, DSMetaData, DSDownloadRecord, DSViewRecord
from core.environment.host import get_host_for_selenium_testing
from core.selenium.common import close_driver, initialize_driver


FAKENODO_HOST = "http://fakenodo:5000"


def wait_for_page_to_load(driver, timeout=4):
    try:
        WebDriverWait(driver, timeout).until(
            lambda driver: driver.execute_script("return document.readyState") == "complete"
        )
    except:
        pass


def test_fakenodo_workflow_selenium():
    '''
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
        

def fix_docker_url(url, host):
    if "localhost" in url and "localhost" not in host:
        return url.replace("http://localhost", host.rstrip('/'))
    return url

def test_selenium_fakenodo_visual_full_flow():
    '''
    1. Login.
    2. Subir dataset (Storage: Zenodo).
    3. Ir al detalle.
    4. Encontrar el enlace generado.
    5. Corregir la URL para Docker y navegar a Fakenodo.
    '''
    driver = initialize_driver()
    host = get_host_for_selenium_testing()
    
    unique_suffix = uuid.uuid4().hex[:6]
    dataset_title = f"Selenium Fakenodo {unique_suffix}"
    
    csv_path = os.path.abspath(f"temp_fakenodo_{unique_suffix}.csv")
    csv_header = "name,brewery,style,abv,ibu\n"
    csv_rows = [
        "Heineken,Heineken Brouwerijen,Lager,5.0,19",
        "Corona,Grupo Modelo,Lager,4.5,18",
        "Mahou,Mahou San Miguel,Pilsner,5.5,25",
        "Guinness,St James Gate,Stout,4.2,45"
    ]
    with open(csv_path, "w") as f: 
        f.write(csv_header)
        for _ in range(12): 
            for row in csv_rows:
                f.write(f"{row}\n")

    try:
        driver.get(f"{host}/login")
        wait_for_page_to_load(driver)
        driver.find_element(By.NAME, "email").send_keys("user1@example.com")
        driver.find_element(By.NAME, "password").send_keys("1234")
        driver.find_element(By.NAME, "password").send_keys(Keys.RETURN)
        WebDriverWait(driver, 10).until(lambda d: "/login" not in d.current_url)

        driver.get(f"{host}/dataset/upload")
        wait_for_page_to_load(driver)

        driver.find_element(By.NAME, "title").send_keys(dataset_title)
        driver.find_element(By.NAME, "desc").send_keys("Selenium Test Description")
        driver.find_element(By.NAME, "csv_file").send_keys(csv_path)
        
        try:
            select_elem = driver.find_element(By.NAME, "storage_service")
            Select(select_elem).select_by_value("zenodo")
        except NoSuchElementException:
            try:
                rb = driver.find_element(By.CSS_SELECTOR, "input[value='zenodo']")
                driver.execute_script("arguments[0].click();", rb)
            except:
                pass 

        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "agreeCheckbox"))
        driver.find_element(By.ID, "upload_button").click()
        
        WebDriverWait(driver, 15).until(lambda d: "/upload" not in d.current_url)

        if "doi" not in driver.current_url and "dataset" not in driver.current_url:
            driver.get(f"{host}/dataset/list")
            xpath_list = f"//a[contains(text(), '{dataset_title}')]"
            link = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, xpath_list)))
            
            raw_href = link.get_attribute('href')
            driver.get(fix_docker_url(raw_href, host))
        
        wait_for_page_to_load(driver)

        print("Buscando enlace a Fakenodo/Zenodo...")
        
        xpath_locator = "//a[contains(text(), 'Zenodo') or contains(@href, '/records/')]"
        
        try:
            external_link = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, xpath_locator))
            )
            raw_fakenodo_url = external_link.get_attribute('href')
            print(f"Enlace encontrado en el HTML: {raw_fakenodo_url}")
            
        except TimeoutException:
            print("HTML Dump:", driver.page_source[:1000])
            raise Exception("No se encontró el enlace a Zenodo en la página.")
        
        final_url = raw_fakenodo_url
        if "localhost" in raw_fakenodo_url:
            final_url = raw_fakenodo_url.replace("localhost", "fakenodo")
            print(f"URL corregida para red Docker: {final_url}")
            
        driver.get(final_url)
        wait_for_page_to_load(driver)
        
        page_source = driver.page_source
        if "Fakenodo" in page_source or "Zenodo" in driver.title:
            print("TEST PASADO: Llegamos a Fakenodo correctamente.")
            
            if dataset_title in page_source:
                print(f"Título '{dataset_title}' encontrado en Fakenodo.")
        else:
            raise Exception("TEST FALLIDO: La página cargada no parece ser Fakenodo.")

    finally:
        # LIMPIEZA
        if os.path.exists(csv_path): os.remove(csv_path)
        try:
            with app.app_context():
                ds = DataSet.query.join(DSMetaData).filter(DSMetaData.title == dataset_title).first()
                if ds:
                    DSDownloadRecord.query.filter_by(dataset_id=ds.id).delete()
                    DSViewRecord.query.filter_by(dataset_id=ds.id).delete()
                    db.session.delete(ds)
                    if ds.ds_meta_data: db.session.delete(ds.ds_meta_data)
                    db.session.commit()
        except:
            db.session.rollback()
        
        close_driver(driver)