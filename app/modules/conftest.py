import pytest

from app import create_app, db
from app.modules.auth.models import User
# Asegúrate de importar cualquier modelo que se cree/use en los tests,
# como el modelo Profesor si lo vas a probar en otros ficheros.
# from app.modules.profacor.profacor import Profesor 


@pytest.fixture(scope="session")
def test_app():
    """Create and configure a new app instance for each test session."""
    # Asegúrate de que "testing" es el nombre de la configuración de prueba
    test_app = create_app("testing")

    with test_app.app_context():
        # Imprimir los blueprints registrados (útil para debug)
        print("TESTING SUITE (1): Blueprints registrados:", test_app.blueprints)
        yield test_app


@pytest.fixture(scope="module")
def test_client(test_app):

    with test_app.test_client() as testing_client:
        with test_app.app_context():
            print("TESTING SUITE (2): Blueprints registrados:", test_app.blueprints)

            # 1. Limpiar y recrear la BD con los modelos actualizados (incluido User con nuevo atributo)
            db.drop_all()
            db.create_all()
            
            """
            The test suite always includes the following user in order to avoid repetition
            of its creation
            """
            # 2. CREACIÓN DEL USUARIO DE PRUEBA: 
            # ¡AQUÍ SE INCLUYE EL NUEVO ATRIBUTO!
            # Si has añadido 'rol_id', debe aparecer aquí.
            user_test = User(
                email="test@example.com", 
                password="test1234",
                # -----------------------------------------------------------------
                # ⚠️ REEMPLAZA 'nuevo_atributo' y 'valor' con tu campo real
                # Por ejemplo: rol_id=1, is_admin=True, telefono="12345678"
                # nuevo_atributo=valor 
                # -----------------------------------------------------------------
            ) 
            
            db.session.add(user_test)
            db.session.commit()

            print("Rutas registradas:")
            for rule in test_app.url_map.iter_rules():
                print(rule)
            yield testing_client

            # 3. Limpieza al finalizar el módulo
            db.session.remove()
            db.drop_all()


@pytest.fixture(scope="function")
def clean_database():
    """Limpia y recrea la DB antes y después de cada función de prueba."""
    db.session.remove()
    db.drop_all()
    db.create_all()
    yield
    db.session.remove()
    db.drop_all()
    db.create_all()


def login(test_client, email, password):
    """
    Authenticates the user with the credentials provided.
    """
    response = test_client.post(
        "/login", 
        data=dict(email=email, password=password), 
        follow_redirects=True
    )
    return response


def logout(test_client):
    """
    Logs out the user.
    """
    return test_client.get("/logout", follow_redirects=True)