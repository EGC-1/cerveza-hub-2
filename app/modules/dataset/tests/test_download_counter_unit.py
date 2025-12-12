import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock

from app import db
from app.modules.auth.models import User, Role
from app.modules.dataset.models import DataSet, DSMetaData, DSDownloadRecord, PublicationType

# --- FIXTURE DE CONTEXTO ---
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
    # 1. Aseguramos que existe el Rol (para evitar error de Foreign Key)
    _create_role()
    
    # 2. Creamos el usuario SOLO con los campos que tiene tu modelo User
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

def test_initial_download_count_is_zero(clean_database):
    """
    Verifica que al usar el helper para crear un dataset,
    el contador nace en 0.
    """
    user = _create_user()
    dataset = _create_dataset(user)

    assert dataset.download_count == 0
    assert isinstance(dataset.download_count, int)