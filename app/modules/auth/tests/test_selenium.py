import time
import os
import uuid
import pytest 
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC 
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Importaciones de tu proyecto
from core.environment.host import get_host_for_selenium_testing
from core.selenium.common import close_driver, initialize_driver 

# IMPORTACIONES DE MODELO Y EXTS
# Importamos el objeto real para referenciarlo, pero usaremos la ruta absoluta para el patch.
from app.modules.auth.models import User 

DEFAULT_TIMEOUT = 10 
SUBMIT_BUTTON_SELECTOR = "[type='submit']" 

# --- XPATHS DE MENSAJES CORREGIDOS ---
SUCCESS_MESSAGE_XPATH = "//div[contains(text(), 'Se ha enviado un enlace para restablecer la contraseña a su correo electrónico.')]" 
ERROR_MESSAGE_XPATH = "//div[contains(@class, 'bg-red-100') and contains(text(), 'El correo electrónico no se encuentra registrado. Por favor, verifique.')]"
RESET_SUCCESS_MESSAGE_XPATH = "//div[contains(text(), 'Tu contraseña ha sido actualizada. Ya puedes iniciar sesión.')]"


# --- FIXTURE PARA CONTEXTO DE APLICACIÓN ---
@pytest.fixture(scope="module")
def app_context(test_app):
    """Proporciona un contexto de aplicación. Se mantiene para coherencia."""
    with test_app.app_context():
        yield test_app

# -----------------------------------------------------------------------------
# Tests de /recover (Se asume que siguen fallando si la tabla User no existe, 
# pero el enfoque principal es arreglar el workflow de reset-password).
# -----------------------------------------------------------------------------

def test_forgot_password_success_selenium(app_context):
    # NOTA: Este test necesita que el usuario exista en la DB, o debe ser mockeado
    # de forma similar a test_reset_password_workflow_selenium.
    REGISTERED_EMAIL = "user1@example.com"
    driver = initialize_driver()
    host = get_host_for_selenium_testing()

    print(f"\n--- Ejecutando test_forgot_password_success_selenium para {REGISTERED_EMAIL} ---")
    
    try:
        driver.get(f"{host}/recover")
        WebDriverWait(driver, DEFAULT_TIMEOUT).until(
            EC.presence_of_element_located((By.NAME, "email"))
        )
        
        print("  -> Ingresando email y enviando solicitud...")
        email_input = driver.find_element(By.NAME, "email")
        email_input.send_keys(REGISTERED_EMAIL)
        
        submit_btn = driver.find_element(By.CSS_SELECTOR, SUBMIT_BUTTON_SELECTOR)
        driver.execute_script("arguments[0].click();", submit_btn)

        WebDriverWait(driver, DEFAULT_TIMEOUT).until(EC.url_contains("/login"))
        
        print("  -> Verificando mensaje de éxito (SUCCESS_MESSAGE_XPATH)...")
        
        try:
            WebDriverWait(driver, DEFAULT_TIMEOUT).until(
                EC.presence_of_element_located((By.XPATH, SUCCESS_MESSAGE_XPATH))
            )
            print("  -> ¡ÉXITO! Mensaje de envío de enlace de restablecimiento encontrado.")
        except TimeoutException:
            raise Exception("Fallo en la verificación: No se encontró el mensaje flash de éxito.")
    finally:
        close_driver(driver)


def test_forgot_password_email_not_found_selenium():
    driver = initialize_driver()
    UNREGISTERED_EMAIL = f"nonexistent_{uuid.uuid4().hex[:8]}@test.com"
    host = get_host_for_selenium_testing()

    print(f"\n--- Ejecutando test_forgot_password_email_not_found_selenium para {UNREGISTERED_EMAIL} ---")

    try:
        driver.get(f"{host}/recover")
        WebDriverWait(driver, DEFAULT_TIMEOUT).until(EC.presence_of_element_located((By.NAME, "email")))
        current_url = driver.current_url
        
        email_input = driver.find_element(By.NAME, "email")
        email_input.send_keys(UNREGISTERED_EMAIL)
        
        submit_btn = driver.find_element(By.CSS_SELECTOR, SUBMIT_BUTTON_SELECTOR)
        driver.execute_script("arguments[0].click();", submit_btn)

        WebDriverWait(driver, DEFAULT_TIMEOUT).until(
            lambda driver: driver.current_url == current_url 
        )
        
        print("  -> Verificando mensaje de correo no encontrado (ERROR_MESSAGE_XPATH)...")
        
        try:
            WebDriverWait(driver, DEFAULT_TIMEOUT).until(
                EC.presence_of_element_located((By.XPATH, ERROR_MESSAGE_XPATH))
            )
            print("  -> ¡ÉXITO! Mensaje de correo no encontrado encontrado.")
        except TimeoutException:
            raise Exception("Fallo en la verificación: No se encontró el mensaje flash de error.")
    finally:
        close_driver(driver)


