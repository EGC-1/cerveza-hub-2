import time
import os
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC 

from core.environment.host import get_host_for_selenium_testing
from core.selenium.common import close_driver, initialize_driver


def wait_for_page_to_load(driver, timeout=4):
    """Espera a que el estado del documento sea 'complete'."""
    WebDriverWait(driver, timeout).until(
        lambda driver: driver.execute_script("return document.readyState") == "complete"
    )


def test_create_community_selenium():
    driver = initialize_driver()

    try:
        host = get_host_for_selenium_testing()

        # 1. AUTENTICACIÓN
        driver.get(f"{host}/login")
        wait_for_page_to_load(driver)

        email_field = driver.find_element(By.NAME, "email")
        password_field = driver.find_element(By.NAME, "password")

        # Usamos las credenciales que funcionan en tus otros tests
        email_field.send_keys("user1@example.com") 
        password_field.send_keys("1234")

        password_field.send_keys(Keys.RETURN)
        
        # Sincronización robusta: Esperar que el login termine
        try:
            WebDriverWait(driver, 10).until_not(
                 EC.url_contains("/login")
             )
        except Exception:
            print(f"Error de autenticación. URL: {driver.current_url}")
            raise

        wait_for_page_to_load(driver) 

        # 2. IR A CREAR COMUNIDAD Y ESPERAR EL FORMULARIO
        driver.get(f"{host}/community/create")
        
        # Espera para el campo "name" (Selector confirmado por la vista)
        try:
            name_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.NAME, "name"))
            )
        except Exception as e:
            print(f"No se encontró el formulario. URL actual: {driver.current_url}")
            raise e

        # 3. INTERACCIÓN CON EL FORMULARIO (Selectores confirmados por la vista)
        
        # Descripción: Es un TEXTAREA, el selector XPath es correcto para evitar <meta>
        desc_field = driver.find_element(By.XPATH, "//textarea[@name='description']")
        logo_input = driver.find_element(By.NAME, "logo")

        name_field.send_keys("Selenium Community")
        desc_field.send_keys("Creada por Selenium test")

        file_path = os.path.abspath("app/modules/dataset/tests/test_files/test_logo.png")
        logo_input.send_keys(file_path)


        # 4. ENVIAR FORMULARIO (Esperando el botón)
        try:
            # Selector más robusto para <button type="submit"> o <input type="submit">
            submit_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[@type='submit'] | //input[@type='submit']"))
            )
        except Exception as e:
            # Si esto falla, el botón NO se está renderizando debido a una validación pendiente del logo.
            print(f"Error: El botón de envío no se pudo hacer clic. URL: {driver.current_url}")
            raise e

        submit_btn.click() 

        # 5. COMPROBACIÓN POST-SUBMISIÓN
        WebDriverWait(driver, 10).until(EC.url_contains("/community/"))
        assert "/community/" in driver.current_url

    finally:
        close_driver(driver)