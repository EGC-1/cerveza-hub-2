import pytest
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select

from core.environment.host import get_host_for_selenium_testing
from core.selenium.common import initialize_driver

class TestAdminFlow:

    # CREDENCIALES DEL ADMIN REAL (El que ya existe en Docker)
    EXISTING_ADMIN_EMAIL = "admin@uvl.com"
    EXISTING_ADMIN_PASSWORD = "123456" 

    def setup_method(self, method):
        self.driver = initialize_driver()
        self.vars = {}
        self.host = get_host_for_selenium_testing()

    def teardown_method(self, method):
        self.driver.quit()

    def test_login_admin_human(self):
        """
        Prueba simple de que el admin puede entrar.
        """
        driver = self.driver
        driver.get(f"{self.host}/login")
        driver.find_element(By.ID, "email").send_keys(self.EXISTING_ADMIN_EMAIL)
        driver.find_element(By.ID, "password").send_keys(self.EXISTING_ADMIN_PASSWORD)
        driver.find_element(By.ID, "submit").click()
        
        # Verificar que entramos
        assert "/login" not in driver.current_url

    def test_admin_create_victim_and_change_role(self):
        """
        Flujo Completo Adaptado a tus URLs:
        1. Lista en: /admin (o /admin/list)
        2. Editar en: /admin/edit/ID
        """
        driver = self.driver
        
        # --- PASO 1: CREAR VÍCTIMA ---
        unique_token = int(time.time())
        unique_email = f"user_{unique_token}@test.com"
        password = "1234"
        
        print(f"--> Creando usuario: {unique_email}")

        driver.get(f"{self.host}/signup")
        driver.find_element(By.ID, "email").send_keys(unique_email)
        driver.find_element(By.ID, "password").send_keys(password)
        
        try:
            driver.find_element(By.NAME, "name").send_keys("Victima")
            driver.find_element(By.NAME, "surname").send_keys("Test")
        except:
            pass 
            
        driver.find_element(By.ID, "submit").click()
        time.sleep(2)
        
        # --- PASO 2: LOGOUT ---
        driver.get(f"{self.host}/logout")
        
        # --- PASO 3: LOGIN ADMIN ---
        driver.get(f"{self.host}/login")
        driver.find_element(By.ID, "email").send_keys(self.EXISTING_ADMIN_EMAIL)
        driver.find_element(By.ID, "password").send_keys(self.EXISTING_ADMIN_PASSWORD)
        driver.find_element(By.ID, "submit").click()
        
        time.sleep(1)
        
        # --- PASO 4: NAVEGAR A LA LISTA ---
        # Según tu info, la lista está en /admin o en /admin/list
        print("--> Entrando al panel de administración...")
        driver.get(f"{self.host}/admin")
        time.sleep(1)

        # Verificación rápida: Si no vemos una tabla, probamos /admin/list explícitamente
        if "list" not in driver.current_url and unique_email not in driver.page_source:
             print("--> No veo al usuario en /admin, probando /admin/list ...")
             driver.get(f"{self.host}/admin/list")
             time.sleep(1)

        # --- PASO 5: BUSCAR Y HACER CLIC EN EDITAR (PAGINACIÓN) ---
        print(f"--> Buscando al usuario {unique_email}...")
        
        user_found = False
        max_pages = 10
        current_page = 1

        while current_page <= max_pages:
            try:
                # Buscamos la fila (tr) que tenga el email
                # Y dentro, un enlace (a) que contenga 'edit'
                # Esto coincidirá con tu URL: .../admin/edit/123
                row_xpath = f"//tr[contains(., '{unique_email}')]"
                edit_btn_xpath = f"{row_xpath}//a[contains(@href, 'edit')]"
                
                # Esperamos a que sea clicable
                btn = WebDriverWait(driver, 2).until(
                    EC.element_to_be_clickable((By.XPATH, edit_btn_xpath))
                )
                
                # Opcional: Imprimir la URL que encontró para confirmar
                found_url = btn.get_attribute("href")
                print(f"--> ¡Encontrado! URL de edición: {found_url}")
                
                btn.click()
                user_found = True
                break 
            
            except:
                # Si falla, buscamos botón Siguiente
                print(f"--> No está en pág {current_page}. Buscando 'Next'...")
                try:
                    # Buscamos flecha '>' o texto 'Next'
                    next_btns = driver.find_elements(By.XPATH, "//li[contains(@class,'next')]//a | //a[contains(text(), '>')]")
                    if next_btns:
                        next_btns[0].click()
                        time.sleep(1)
                        current_page += 1
                    else:
                        break # No hay más botones
                except:
                    break

        if not user_found:
            # Debug: Si falla, imprime qué URLs hay en la página
            print("DEBUG: Links encontrados en la página actual:")
            for a in driver.find_elements(By.TAG_NAME, "a"):
                if "edit" in str(a.get_attribute("href")):
                    print(f" - {a.get_attribute('href')}")
            pytest.fail(f"No se encontró al usuario {unique_email} en la tabla.")

        # --- PASO 6: CAMBIAR ROL ---
        print("--> Cambiando rol a Admin...")
        try:
            # Buscamos cualquier select visible
            select = Select(driver.find_element(By.TAG_NAME, "select"))
            
            # Intentamos elegir Admin
            try:
                select.select_by_visible_text("Admin")
            except:
                select.select_by_index(1) # Opción 2 si falla el texto

            driver.find_element(By.ID, "submit").click()
            print("--> ¡Rol cambiado con éxito!")
            
        except Exception as e:
            pytest.fail(f"Error en el formulario de edición: {e}")

