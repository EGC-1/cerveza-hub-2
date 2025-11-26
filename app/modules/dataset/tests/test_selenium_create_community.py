import time
import os
import uuid
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC 

from core.environment.host import get_host_for_selenium_testing
from core.selenium.common import close_driver, initialize_driver


def wait_for_page_to_load(driver, timeout=4):
    """Espera a que el estado del documento sea 'complete'."""
    try:
        WebDriverWait(driver, timeout).until(
            lambda driver: driver.execute_script("return document.readyState") == "complete"
        )
    except:
        pass

def test_community_workflow_selenium():
    driver = initialize_driver()
    unique_suffix = uuid.uuid4().hex[:6]
    community_name = f"Selenium Community {unique_suffix}"
    
    logo_path = os.path.abspath(f"temp_logo_{unique_suffix}.png")
    with open(logo_path, "wb") as f: f.write(b"fake_png_data")

    try:
        host = get_host_for_selenium_testing()
        
        # LOGIN
        driver.get(f"{host}/login")
        wait_for_page_to_load(driver)
        driver.find_element(By.NAME, "email").send_keys("user1@example.com")
        driver.find_element(By.NAME, "password").send_keys("1234")
        driver.find_element(By.NAME, "password").send_keys(Keys.RETURN)
        WebDriverWait(driver, 10).until_not(EC.url_contains("/login"))

        # CREAR COMUNIDAD
        driver.get(f"{host}/community/create")
        wait_for_page_to_load(driver)
        driver.find_element(By.NAME, "name").send_keys(community_name)
        driver.find_element(By.XPATH, "//textarea[@name='description']").send_keys("Test")
        driver.find_element(By.NAME, "logo").send_keys(logo_path)
        
        submit = driver.find_element(By.XPATH, "//button[@type='submit'] | //input[@type='submit']")
        driver.execute_script("arguments[0].click();", submit)
        
        WebDriverWait(driver, 10).until(lambda d: "/community/" in d.current_url and "/create" not in d.current_url)
        community_id = driver.current_url.split('?')[0].rstrip('/').split('/')[-1]

        # --- PASO 3: ASOCIAR DATASETS (INTENTO LENTO Y VISUAL) ---
        print(f"Asociando a ID {community_id}...")
        driver.get(f"{host}/community/{community_id}/manage_datasets")
        wait_for_page_to_load(driver)
        
        # Pausa para asegurar carga total de scripts
        time.sleep(1)

        # Seleccionar opción
        select = Select(driver.find_element(By.NAME, "datasets"))
        select.select_by_index(0)
        dataset_name = select.options[0].text.strip()
        print(f"Seleccionado: {dataset_name}")
        
        # Pausa humana
        time.sleep(0.5)

        # Clic en Guardar
        submit_btn = driver.find_element(By.ID, "submit") # Usamos ID porque lo vi en tu HTML
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_btn)
        time.sleep(0.5)
        
        print("Haciendo clic en Guardar...")
        submit_btn.click()

        # Esperar redirección
        try:
            WebDriverWait(driver, 5).until(lambda d: "manage_datasets" not in d.current_url)
        except:
            print("❌ Falló. El formulario se recargó.")
            # Imprimir si hay algún error oculto en el HTML
            if "csrf_token" in driver.page_source:
                print("El token CSRF sigue ahí, lo que confirma recarga.")
            
            # BUSCAR ERRORES ESPECÍFICOS DE FLASK-WTF
            # A veces los errores no tienen clase 'invalid-feedback' sino que son listas <ul>
            errors = driver.find_elements(By.XPATH, "//ul[contains(@class, 'errors')]/li")
            if errors:
                print("ERRORES ENCONTRADOS:")
                for e in errors: print(f"- {e.text}")
            
            raise Exception("No se pudo asociar el dataset.")

        # VERIFICAR
        print("Verificando...")
        wait_for_page_to_load(driver)
        assert community_name in driver.page_source
        clean_name = dataset_name.split('(')[0].strip()
        assert clean_name in driver.page_source
        
        print("¡ÉXITO!")

    finally:
        if os.path.exists(logo_path): os.remove(logo_path)
        close_driver(driver)