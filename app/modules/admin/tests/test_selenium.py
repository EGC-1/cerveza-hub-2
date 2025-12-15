import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

from core.environment.host import get_host_for_selenium_testing
from core.selenium.common import close_driver, initialize_driver
from app.modules.dataset.tests.test_selenium import wait_for_page_to_load
from app import create_app
from app.modules.auth.models import db, User

app = create_app()

def test_role_change_selenium():
    """
    Verifica que el cambio de rol funciona correctamente:
    - Un admin asigna rol admin a un usuario
    - El usuario accede a /admin
    - Se le quita el rol
    - Se le bloquea el acceso inmediatamente
    """

    driver = initialize_driver()
    user_id = 2  # Usuario a modificar

    try:
        host = get_host_for_selenium_testing()

        # ---------- GUARDAR ROL ORIGINAL ----------
        with app.app_context():
            original_user = User.query.get(user_id)
            original_role_id = original_user.role.id if original_user.role else None

        # ---------- LOGIN COMO ADMIN ----------
        driver.get(f"{host}/login")
        wait_for_page_to_load(driver)
        driver.find_element(By.NAME, "email").send_keys("admin@uvl.com")
        driver.find_element(By.NAME, "password").send_keys("123456")
        driver.find_element(By.NAME, "password").send_keys(Keys.RETURN)
        WebDriverWait(driver, 10).until_not(EC.url_contains("/login"))

        # ---------- ACCEDER A /ADMIN ----------
        driver.get(f"{host}/admin/")
        wait_for_page_to_load(driver)
        assert "/admin" in driver.current_url

        # ---------- EDITAR USUARIO Y ASIGNAR ROL ADMIN ----------
        driver.get(f"{host}/admin/edit/{user_id}")
        wait_for_page_to_load(driver)
        role_select = Select(driver.find_element(By.NAME, "roles"))
        admin_value = next((opt.get_attribute("value") for opt in role_select.options if opt.text.lower() == "admin"), None)
        if not admin_value:
            raise Exception("No existe el rol 'admin'")
        role_select.select_by_value(admin_value)
        driver.find_element(By.NAME, "submit").click()
        WebDriverWait(driver, 5).until(EC.url_contains("/admin"))

        # ---------- LOGOUT ----------
        driver.get(f"{host}/logout")

        # ---------- LOGIN COMO USUARIO PROMOVIDO ----------
        driver.get(f"{host}/login")
        wait_for_page_to_load(driver)
        driver.find_element(By.NAME, "email").send_keys("user1@example.com")
        driver.find_element(By.NAME, "password").send_keys("1234")
        driver.find_element(By.NAME, "password").send_keys(Keys.RETURN)
        WebDriverWait(driver, 10).until_not(EC.url_contains("/login"))

        # ---------- ACCEDER A /admin y confirmar acceso ----------
        driver.get(f"{host}/admin/")
        wait_for_page_to_load(driver)
        assert "/admin" in driver.current_url

        # ---------- QUITAR ROL ADMIN ----------
        driver.get(f"{host}/admin/edit/{user_id}")
        wait_for_page_to_load(driver)
        role_select = Select(driver.find_element(By.NAME, "roles"))
        non_admin_value = next((opt.get_attribute("value") for opt in role_select.options if opt.text.lower() != "admin"), None)
        if not non_admin_value:
            raise Exception("No hay rol no-admin disponible")
        role_select.select_by_value(non_admin_value)
        driver.find_element(By.NAME, "submit").click()
        time.sleep(1)

        # ---------- LOGIN COMO USUARIO SIN ROL ADMIN ----------
        driver.get(f"{host}/logout")
        driver.get(f"{host}/login")
        wait_for_page_to_load(driver)
        driver.find_element(By.NAME, "email").send_keys("user1@example.com")
        driver.find_element(By.NAME, "password").send_keys("1234")
        driver.find_element(By.NAME, "password").send_keys(Keys.RETURN)
        WebDriverWait(driver, 10).until_not(EC.url_contains("/login"))

        # ---------- INTENTAR ACCEDER A /admin ----------
        driver.get(f"{host}/admin/")
        wait_for_page_to_load(driver)
        assert "/admin" not in driver.current_url, "El usuario todavía puede acceder a /admin después de quitar el rol"

        print("✔ Test de cambio de rol completado correctamente")

    finally:
        # ---------- RESTAURAR ROL ORIGINAL ----------
        with app.app_context():
            user = User.query.get(user_id)
            user.role_id = original_role_id
            db.session.commit()
        close_driver(driver)
