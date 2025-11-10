import pytest

from app import create_app, db
from app.modules.auth.models import User
from app.modules.auth.models import Role 


@pytest.fixture(scope="module")
def test_client(test_app):

    with test_app.test_client() as testing_client:
        with test_app.app_context():
            print("TESTING SUITE (2): Blueprints registrados:", test_app.blueprints)

            db.drop_all()
            db.create_all()
            
            try:
                role_test = Role(id=1, name="user", description="Default user role")
                db.session.add(role_test)
            except NameError:
                 print("⚠️ Advertencia: El modelo 'Role' no fue encontrado. Asegúrate de importarlo.")
            
            """
            El conjunto de pruebas siempre incluye este usuario para evitar su repetición.
            """
            user_test = User(
                email="test@example.com", 
                password="test1234",
                role_id=1, 
            ) 
            
            db.session.add(user_test)
            db.session.commit()

            print("Rutas registradas:")
            for rule in test_app.url_map.iter_rules():
                print(rule)
            yield testing_client

            db.session.remove()
            db.drop_all()


@pytest.fixture(scope="function")
def clean_database():
    """Limpia y recrea la DB antes y después de cada función de prueba (si se usa)."""
    db.session.remove()
    db.drop_all()
    db.create_all()
    yield
    db.session.remove()
    db.drop_all()
    db.create_all()


def login(test_client, email, password):
    """
    Autentica al usuario con las credenciales proporcionadas.
    """
    response = test_client.post(
        "/login", 
        data=dict(email=email, password=password), 
        follow_redirects=True
    )
    return response


def logout(test_client):
    """
    Cierra la sesión del usuario.
    """
    return test_client.get("/logout", follow_redirects=True)