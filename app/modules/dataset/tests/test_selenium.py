import os
import time
import tempfile

from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

from core.environment.host import get_host_for_selenium_testing
from core.selenium.common import initialize_driver, close_driver


def _click_login_submit(driver):
    # Soporta distintas plantillas: button submit, input submit, o botón dentro del form
    for selector in ("button[type='submit']", "input[type='submit']"):
        els = driver.find_elements(By.CSS_SELECTOR, selector)
        if els:
            els[0].click()
            return

    # Último recurso: primer botón dentro del form
    form = driver.find_element(By.TAG_NAME, "form")
    btns = form.find_elements(By.TAG_NAME, "button")
    if btns:
        btns[0].click()
        return

    raise RuntimeError("No se encontró un submit en la página de login (ni button ni input).")


def _login(driver, base_url, email="user1@example.com", password="1234"):
    driver.get(f"{base_url}/login")

    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "email")))
    driver.find_element(By.NAME, "email").clear()
    driver.find_element(By.NAME, "email").send_keys(email)

    driver.find_element(By.NAME, "password").clear()
    driver.find_element(By.NAME, "password").send_keys(password)

    _click_login_submit(driver)

    # Espera a salir de /login (o a que cambie la URL)
    WebDriverWait(driver, 10).until(lambda d: "/login" not in d.current_url)


def _make_temp_csv():
    content = "name,ibu,brewery\nheineken,35,heineken\n"
    fd, path = tempfile.mkstemp(suffix=".csv", text=True)
    with os.fdopen(fd, "w") as f:
        f.write(content)
    return path


def test_upload_dataset_select_github_storage_redirects_to_doi_or_unsynchronized():
    base_url = get_host_for_selenium_testing()
    driver = initialize_driver()
    csv_path = _make_temp_csv()

    try:
        _login(driver, base_url)

        driver.get(f"{base_url}/dataset/upload")

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "storage_service"))
        )

        # Selecciona GitHub
        Select(driver.find_element(By.ID, "storage_service")).select_by_value("github")

        # Rellena campos
        driver.find_element(By.NAME, "title").send_keys("Selenium GitHub Dataset")
        driver.find_element(By.NAME, "desc").send_keys("Dataset uploaded via Selenium selecting GitHub")

        # CSV
        driver.find_element(By.NAME, "csv_file").send_keys(csv_path)

        # Checkbox habilita el submit
        agree = driver.find_element(By.ID, "agreeCheckbox")
        if not agree.is_selected():
            agree.click()

        upload_btn = driver.find_element(By.ID, "upload_button")
        WebDriverWait(driver, 10).until(lambda d: upload_btn.is_enabled())
        upload_btn.click()

        WebDriverWait(driver, 20).until(
            lambda d: ("/doi/" in d.current_url) or ("/dataset/unsynchronized/" in d.current_url)
        )

        assert ("/doi/" in driver.current_url) or ("/dataset/unsynchronized/" in driver.current_url)

    finally:
        driver.quit()
        try:
            os.remove(csv_path)
        except OSError:
            pass


def test_upload_page_has_github_option_and_checkbox_blocks_submit_until_checked():
    base_url = get_host_for_selenium_testing()
    driver = initialize_driver()

    try:
        _login(driver, base_url)

        driver.get(f"{base_url}/dataset/upload")

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "storage_service"))
        )

        select_el = Select(driver.find_element(By.ID, "storage_service"))
        option_values = [o.get_attribute("value") for o in select_el.options]
        assert "github" in option_values

        upload_btn = driver.find_element(By.ID, "upload_button")
        agree = driver.find_element(By.ID, "agreeCheckbox")

        # Al cargar debe estar deshabilitado
        assert upload_btn.get_attribute("disabled") is not None

        # Marcando checkbox debe habilitarse
        if not agree.is_selected():
            agree.click()

        WebDriverWait(driver, 10).until(lambda d: upload_btn.get_attribute("disabled") is None)

    finally:
        driver.quit()



def wait_for_page_to_load(driver, timeout=4):
    WebDriverWait(driver, timeout).until(
        lambda driver: driver.execute_script("return document.readyState") == "complete"
    )


def count_datasets(driver, host):
    driver.get(f"{host}/dataset/list")
    wait_for_page_to_load(driver)

    try:
        amount_datasets = len(driver.find_elements(By.XPATH, "//table//tbody//tr"))
    except Exception:
        amount_datasets = 0
    return amount_datasets


def test_upload_dataset():
    driver = initialize_driver()
    
    temp_csv_name = "selenium_test_data.csv"
    file_path = os.path.abspath(temp_csv_name)
    
    with open(temp_csv_name, "w") as f:
        f.write("col1,col2\nval1,val2")

    try:
        host = get_host_for_selenium_testing()

        driver.get(f"{host}/login")
        wait_for_page_to_load(driver)

        email_field = driver.find_element(By.NAME, "email")
        password_field = driver.find_element(By.NAME, "password")

        email_field.send_keys("user1@example.com")
        password_field.send_keys("1234")

        password_field.send_keys(Keys.RETURN)
        time.sleep(2)
        wait_for_page_to_load(driver)

        initial_datasets = count_datasets(driver, host)

        driver.get(f"{host}/dataset/upload")
        wait_for_page_to_load(driver)

        title_field = driver.find_element(By.NAME, "title")
        title_field.send_keys("Selenium CSV Test")
        
        desc_field = driver.find_element(By.NAME, "desc")
        desc_field.send_keys("Description generated by Selenium")
        
        tags_field = driver.find_element(By.NAME, "tags")
        tags_field.send_keys("tag1,tag2")

        try:
            add_author_button = driver.find_element(By.ID, "add_author")
            add_author_button.send_keys(Keys.RETURN)
            wait_for_page_to_load(driver)
            
            name_field0 = driver.find_element(By.NAME, "authors-0-name")
            name_field0.send_keys("Selenium Author")
            
            affiliation_field0 = driver.find_element(By.NAME, "authors-0-affiliation")
            affiliation_field0.send_keys("Selenium Club")
        except Exception:
            print("Nota: No se pudo añadir autor extra o el botón no existe.")

        file_input = driver.find_element(By.NAME, "csv_file")
        file_input.send_keys(file_path)
        
        wait_for_page_to_load(driver)

        check = driver.find_element(By.ID, "agreeCheckbox")
        try:
            check.click()
        except:
            check.send_keys(Keys.SPACE)
            
        wait_for_page_to_load(driver)

        upload_btn = driver.find_element(By.ID, "upload_button")
        upload_btn.send_keys(Keys.RETURN)
        
        time.sleep(4)
        wait_for_page_to_load(driver)

        current_url = driver.current_url
        print(f"URL tras subir: {current_url}")
        
        assert "upload" not in current_url, "El test sigue en la página de subida (fallo al enviar)"
        assert "/doi/" in current_url or "/dataset/" in current_url, "No se redirigió a la página del dataset creado"

        final_datasets = count_datasets(driver, host)
        assert final_datasets == initial_datasets + 1, "El número de datasets no aumentó."

        print("Test passed!")

    finally:
        close_driver(driver)
        if os.path.exists(temp_csv_name):
            try:
                os.remove(temp_csv_name)
            except:
                pass

test_upload_dataset()