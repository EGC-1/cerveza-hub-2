import pytest

from app import db
from app.modules.auth.models import User, Role
from app.modules.dataset.models import DataSet, DSMetaData, DSDownloadRecord, PublicationType

# --- CONTEXT FIXTURE ---

@pytest.fixture(autouse=True)
def setup_context(test_client):
    """
    Activa el contexto de la aplicación para que db.session funcione.
    """
    with test_client.application.app_context():
        yield


# --- HELPERS ---

def _create_role():
    """
    Crea el rol 'user' (id=1) si no existe.
    Necesario porque el modelo User tiene role_id default=1.
    """
    role = Role.query.get(1)
    if not role:
        role = Role(id=1, name="user", description="Standard user")
        db.session.add(role)
        db.session.commit()
    return role


def _create_user(email: str = "user@test.com") -> User:
    """Helper para crear un usuario base."""
    
    _create_role()
    
    user = User(email=email, password="password123")
    db.session.add(user)
    db.session.commit()
    return user


def _create_dataset(user: User, title: str = "Unit Test Dataset") -> DataSet:
    """Helper para crear un dataset vinculado a un usuario."""
    meta = DSMetaData(
        title=title, 
        description="Description", 
        publication_type=PublicationType.JOURNAL_ARTICLE,
        dataset_doi=f"10.1234/{title.replace(' ', '').lower()}"
    )
    db.session.add(meta)
    db.session.commit()

    dataset = DataSet(user_id=user.id, ds_meta_data_id=meta.id)
    db.session.add(dataset)
    db.session.commit()
    return dataset


# --- TESTS ---

def test_1_counter_starts_at_zero(clean_database):
    """
    Test 1: Integridad por defecto.
    Verifica que si no decimos nada, el contador no es None, es 0.
    Sirve para detectar: Olvidos en el `default=0` del modelo.
    """
    user = _create_user()
    dataset = _create_dataset(user)

    assert dataset.download_count is not None
    assert dataset.download_count == 0
    
    
def test_2_counter_accepts_increments(clean_database):
    """
    Test 2: Persistencia básica.
    Verifica que la base de datos guarda el número nuevo.
    Sirve para detectar: Problemas de commit o tipos de datos erróneos.
    """
    user = _create_user()
    dataset = _create_dataset(user)

    dataset.download_count += 1
    db.session.commit()

    db.session.refresh(dataset)
    assert dataset.download_count == 1
    

def test_3_record_creation_constraint(clean_database):
    """
    Test 3: Relaciones (Foreign Keys).
    Verifica que podemos crear un registro de descarga vinculado al dataset.
    Sirve para detectar: Fallos en las claves foráneas (user_id/dataset_id).
    """
    user = _create_user()
    dataset = _create_dataset(user)

    record = DSDownloadRecord(
        user_id=user.id,
        dataset_id=dataset.id,
        download_cookie="test_cookie"
    )
    db.session.add(record)
    db.session.commit()

    assert record.id is not None
    assert record.dataset_id == dataset.id
    
    
def test_4_json_exposure(clean_database, test_client):
    """
    Test 4: Serialización.
    Verifica que el método `to_dict` incluye el contador.
    SOLUCIÓN: Usamos test_request_context() para simular que hay una URL activa.
    """
    user = _create_user()
    dataset = _create_dataset(user)
    dataset.download_count = 99
    db.session.commit()

    with test_client.application.test_request_context():

        data = dataset.to_dict()

        assert "download_count" in data
        assert data["download_count"] == 99

    

    

