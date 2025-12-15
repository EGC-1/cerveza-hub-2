import time
import os
import uuid
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC 
from selenium.common.exceptions import TimeoutException

from app import app, db
from app.modules.dataset.models import DataSet, DSMetaData, DSDownloadRecord, DSViewRecord

from core.environment.host import get_host_for_selenium_testing
from core.selenium.common import close_driver, initialize_driver


def wait_for_page_to_load(driver, timeout=4):
    try:
        WebDriverWait(driver, timeout).until(
            lambda driver: driver.execute_script("return document.readyState") == "complete"
        )
    except:
        pass

def test_download_counter_workflow_selenium():
    '''
    Test de Selenium que verifica el contador de descargas de un dataset, lo crea desde la interfaz web,
    descarga el dataset y comprueba que el contador se incrementa correctamente.
    '''
    driver = initialize_driver()
    unique_suffix = uuid.uuid4().hex[:6]
    dataset_title = f"Selenium Dataset {unique_suffix}"
    
    csv_path = os.path.abspath(f"temp_data_{unique_suffix}.csv")
    with open(csv_path, "w") as f: 
        f.write("col1,col2\nval1,val2")

    try:
        host = get_host_for_selenium_testing()
        
        # --- LOGIN ---
        driver.get(f"{host}/login")
        wait_for_page_to_load(driver)
        
        driver.find_element(By.NAME, "email").send_keys("user1@example.com")
        driver.find_element(By.NAME, "password").send_keys("1234")
        driver.find_element(By.NAME, "password").send_keys(Keys.RETURN)
        
        WebDriverWait(driver, 10).until_not(EC.url_contains("/login"))

        # --- CREATE DATASET ---
        driver.get(f"{host}/dataset/upload")
        wait_for_page_to_load(driver)

        driver.find_element(By.NAME, "title").send_keys(dataset_title)
        driver.find_element(By.NAME, "desc").send_keys("Selenium Test Description")
        driver.find_element(By.NAME, "csv_file").send_keys(csv_path)
        
        # Checkbox Agree
        agree_checkbox = driver.find_element(By.ID, "agreeCheckbox")
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", agree_checkbox)
        if not agree_checkbox.is_selected():
            driver.execute_script("arguments[0].click();", agree_checkbox)
        
        time.sleep(0.5)

        submit_btn = driver.find_element(By.ID, "upload_button")
        driver.execute_script("arguments[0].click();", submit_btn)
        
        # Wait until redirect
        try:
            WebDriverWait(driver, 10).until(lambda d: "/upload" not in d.current_url)
        except TimeoutException:
            raise Exception("Timeout esperando a que se cree el dataset.")

        if "dataset" not in driver.current_url:
            driver.get(f"{host}/dataset/list")
            wait_for_page_to_load(driver)
            
            # Search the link by title
            try:
                xpath_title = f"//a[contains(text(), '{dataset_title}')]"
                link = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, xpath_title))
                )
                
                href = link.get_attribute('href')
                if "localhost" in href:
                    # Fix URL for Docker environment
                    fixed_url = href.replace("http://localhost", host.rstrip('/'))
                    
                    if ":5000" not in fixed_url and "web" in fixed_url:
                         fixed_url = fixed_url.replace("http://web", "http://web:5000")

                    driver.get(fixed_url)
                else:
                    link.click()

            except TimeoutException:
                raise Exception(f"No se encontró el dataset '{dataset_title}' en la lista.")
        
        wait_for_page_to_load(driver)
            
        try:
            download_btn = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/dataset/download/')]"))
            )
        except TimeoutException:
            raise Exception("No se encontró el botón de descarga en la página de detalle.")
        
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", download_btn)
        time.sleep(0.5)
        
        driver.execute_script("arguments[0].click();", download_btn)

        time.sleep(2) 

        driver.refresh()
        wait_for_page_to_load(driver)

        page_source = driver.page_source
        
        if "Downloads: 1" in page_source:
            print("¡ÉXITO! Se encontró 'Downloads: 1'.")
        else:
            print("ERROR VISUAL: No se ve 'Downloads: 1'.")
            if "Downloads: 0" in page_source:
                raise Exception("El contador sigue en 0.")
            else:
                try:
                    stats = driver.find_element(By.XPATH, "//*[contains(text(), 'Downloads:')]").text
                    print(f"Texto encontrado: '{stats}'")
                except:
                    pass
                raise Exception("Fallo en la verificación del contador.")

    finally:
        if os.path.exists(csv_path): 
            os.remove(csv_path)
        
        try:
                        
            with app.app_context():
                datasets_to_delete = DataSet.query.join(DSMetaData).filter(
                    DSMetaData.title == dataset_title
                ).all()
                
                for ds in datasets_to_delete:
                    did = ds.id
                    meta_id = ds.ds_meta_data_id
                    
                    deleted_downloads = DSDownloadRecord.query.filter_by(dataset_id=did).delete()
                    
                    deleted_views = DSViewRecord.query.filter_by(dataset_id=did).delete()
                    
                    db.session.delete(ds)
                    
                    if meta_id:
                        meta = db.session.get(DSMetaData, meta_id)
                        if meta:
                            db.session.delete(meta)
                                            
                db.session.commit()

        except Exception as e:
            print(f"Error CRÍTICO durante la limpieza de BD: {e}")
            try:
                db.session.rollback()
            except:
                pass

        close_driver(driver)