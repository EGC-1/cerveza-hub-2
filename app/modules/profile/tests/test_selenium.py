import time
import uuid

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from core.environment.host import get_host_for_selenium_testing
from core.selenium.common import initialize_driver, close_driver


def _click_login_submit(driver):
    for selector in ("button[type='submit']", "input[type='submit']"):
        els = driver.find_elements(By.CSS_SELECTOR, selector)
        if els:
            els[0].click()
            return

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
    WebDriverWait(driver, 10).until(lambda d: "/login" not in d.current_url)


def _go_manage_sessions(driver, base_url):
    driver.get(f"{base_url}/profile/manage_account/sessions")
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))


def _has_no_other_sessions_alert(driver):
    return bool(driver.find_elements(By.XPATH, "//*[contains(., 'No other active sessions found')]"))


def _wait_body(driver, timeout=10):
    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )


def _get_flask_app_for_context():
    """
    Intenta obtener una app Flask para poder abrir app_context().
    Compatible con proyectos que tienen create_app() o una instancia 'app'.
    """
    # 1) factory pattern
    try:
        from app import create_app  # type: ignore
        return create_app()
    except Exception:
        pass

    # 2) global app instance
    try:
        from app import app as flask_app  # type: ignore
        return flask_app
    except Exception as e:
        pytest.skip(f"No se pudo obtener app Flask (create_app/app): {e}")


def _seed_remote_session_for_user(email: str) -> str:
    """
    Inserta una sesión remota en DB para que aparezca en "Other Active Sessions".
    Devuelve el session_key insertado.
    """
    flask_app = _get_flask_app_for_context()

    # imports "dentro" para asegurar que se evalúan ya con el contexto disponible
    try:
        from app import db  # type: ignore
    except Exception as e:
        pytest.skip(f"No se pudo importar app.db: {e}")

    try:
        from app.modules.auth.models import User  # type: ignore
    except Exception:
        try:
            from app.modules.auth.models.user import User  # type: ignore
        except Exception as e:
            pytest.skip(f"No se pudo importar User: {e}")

    # Modelo de sesión
    SessionModel = None
    candidates = [
        ("app.modules.auth.models", "UserSession"),
        ("app.modules.auth.models.user_session", "UserSession"),
        ("app.modules.auth.models.session", "UserSession"),
    ]
    for mod, name in candidates:
        try:
            m = __import__(mod, fromlist=[name])
            SessionModel = getattr(m, name)
            break
        except Exception:
            continue

    if SessionModel is None:
        pytest.skip("No se encontró el modelo UserSession (ajusta el import al path real).")

    with flask_app.app_context():
        user = User.query.filter_by(email=email).first()
        if not user:
            pytest.skip(f"No existe el usuario {email} en DB (necesario para el test).")

        session_key = f"selenium-remote-{uuid.uuid4().hex[:12]}"

        obj = SessionModel()

        if hasattr(obj, "user_id"):
            obj.user_id = user.id
        if hasattr(obj, "session_key"):
            obj.session_key = session_key
        if hasattr(obj, "ip_address"):
            obj.ip_address = "203.0.113.10"
        if hasattr(obj, "user_agent"):
            obj.user_agent = "Selenium Remote Device"

        # Algunos modelos guardan timestamps
        if hasattr(obj, "login_time"):
            try:
                import datetime
                obj.login_time = datetime.datetime.utcnow()
            except Exception:
                pass

        db.session.add(obj)
        db.session.commit()

    return session_key


def _remote_row_close_button_xpath(session_key: str) -> str:
    return (
        f"//form[.//input[@name='session_key' and @value='{session_key}']]"
        "//button[contains(@class,'btn-outline-danger') and @type='submit']"
    )


def test_manage_sessions_page_renders():
    base_url = get_host_for_selenium_testing()
    driver = initialize_driver()

    try:
        _login(driver, base_url)
        _go_manage_sessions(driver, base_url)

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//h1[contains(., 'Manage Sessions')]"))
        )

        body_text = driver.find_element(By.TAG_NAME, "body").text
        assert "This is your current session" in body_text

        assert ("Other Active Sessions" in body_text) or _has_no_other_sessions_alert(driver)

    finally:
        close_driver(driver)


def test_close_seeded_remote_session_via_ui_single_browser():
    base_url = get_host_for_selenium_testing()
    driver = initialize_driver()

    try:
        _login(driver, base_url, email="user1@example.com", password="1234")

        seeded_key = _seed_remote_session_for_user("user1@example.com")

        _go_manage_sessions(driver, base_url)
        _wait_body(driver, 10)

        close_btn_xpath = _remote_row_close_button_xpath(seeded_key)
        close_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, close_btn_xpath))
        )
        close_btn.click()

        # Confirm JS
        alert = WebDriverWait(driver, 5).until(EC.alert_is_present())
        alert.accept()

        # Flash
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".alert")))
        alerts = driver.find_elements(By.CSS_SELECTOR, ".alert")
        alerts_text = " | ".join(a.text.lower() for a in alerts)
        assert any(k in alerts_text for k in ["closed", "success", "logout", "session"]), (
            f"No aparece mensaje de éxito tras cerrar sesión. Alerts: {alerts_text}"
        )

        # Debe desaparecer
        time.sleep(0.3)
        driver.refresh()
        _wait_body(driver, 10)

        still_there = driver.find_elements(By.XPATH, close_btn_xpath)
        assert not still_there, "La sesión remota seeded todavía aparece en la UI tras cerrarla."

    finally:
        close_driver(driver)
