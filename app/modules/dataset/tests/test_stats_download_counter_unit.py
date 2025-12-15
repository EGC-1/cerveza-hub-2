import pytest
import uuid
from datetime import datetime
from sqlalchemy import text 

from app import db
from app.modules.auth.models import User, Role
from app.modules.profile.models import UserProfile 
from app.modules.dataset.models import DataSet, DSMetaData, DSDownloadRecord, DSViewRecord, PublicationType

def _nuke_db():
    """
    Borra todas las tablas involucradas ignorando las restricciones de 
    Foreign Keys temporalmente. Esto evita el IntegrityError.
    """
    try:
        if 'mysql' in str(db.engine.url):
            db.session.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        else:
            db.session.execute(text("PRAGMA foreign_keys=OFF"))
            
        models = [DSDownloadRecord, DSViewRecord, DataSet, DSMetaData, UserProfile, User, Role]
        
        for model in models:
            db.session.query(model).delete()
            
        if 'mysql' in str(db.engine.url):
            db.session.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
        
        db.session.commit()
    except Exception as e:
        print(f"⚠️ Error limpiando BD en test unitario: {e}")
        db.session.rollback()

@pytest.fixture(scope="function", autouse=True)
def isolation_and_cleanup(test_client):
    """
    Fixture automática (autouse=True).
    Garantiza que CADA test empiece y termine con la BD vacía y la sesión limpia.
    """
    
    with test_client.application.app_context():
        db.session.remove()
        
        _nuke_db()
        
        yield  
        
        db.session.rollback() 
        _nuke_db()
        db.session.remove()

# =================================================================
# HELPERS
# =================================================================

def _create_role():
    role = Role.query.get(1)
    if not role:
        role = Role(id=1, name="user", description="Standard user")
        db.session.add(role)
        db.session.commit()
    return role

def _create_user(email: str = None) -> User:
    _create_role()
    
    email = email or f"user_{uuid.uuid4().hex[:8]}@test.com"
    
    user = User(email=email, password="password123")
    user.profile = UserProfile(surname='Test', name='User', affiliation='Lab', orcid='0000')
    
    db.session.add(user)
    db.session.commit()
    
    db.session.refresh(user)
    return user

def _create_dataset(user: User, title: str = "Unit Test Dataset") -> DataSet:
    user = db.session.merge(user)
    
    doi = f"10.1234/{uuid.uuid4().hex[:6]}"
    
    meta = DSMetaData(
        title=title, 
        description="Description", 
        publication_type=PublicationType.JOURNAL_ARTICLE,
        dataset_doi=doi
    )
    db.session.add(meta)
    db.session.commit()

    dataset = DataSet(user_id=user.id, ds_meta_data_id=meta.id)
    
    dataset.download_count = 0
    
    db.session.add(dataset)
    db.session.commit()
    
    db.session.refresh(dataset)
    return dataset


# =================================================================
# TESTS
# =================================================================

def test_1_initial_stats_state():
    user = _create_user()
    dataset = _create_dataset(user)

    assert dataset.download_count == 0
    
    assert not dataset.row_count 
    assert not dataset.column_names
    
    
def test_2_manual_increment_download():
    user = _create_user()
    dataset = _create_dataset(user)

    dataset.download_count += 1
    db.session.commit()

    db.session.refresh(dataset)
    assert dataset.download_count == 1

    dataset.download_count += 5
    db.session.commit()
    
    db.session.refresh(dataset)
    assert dataset.download_count == 6
  
    
def test_3_record_creation_constraint():
    user = _create_user()
    dataset = _create_dataset(user)

    record = DSDownloadRecord(
        user_id=user.id,
        dataset_id=dataset.id,
        download_date=datetime.utcnow(),
        download_cookie="test_cookie_123"
    )
    db.session.add(record)
    db.session.commit()

    assert record.id is not None
    assert record.dataset_id == dataset.id
    

def test_4_view_record_creation():
    user = _create_user()
    dataset = _create_dataset(user)

    view = DSViewRecord(
        user_id=user.id,
        dataset_id=dataset.id,
        view_date=datetime.utcnow(),
        view_cookie="view_cookie_abc"
    )
    db.session.add(view)
    db.session.commit()

    assert view.id is not None
    assert view.dataset_id == dataset.id


def test_5_csv_metadata_storage():
    user = _create_user()
    dataset = _create_dataset(user)

    dataset.row_count = 1500
    dataset.column_names = "col1,col2,col3"
    db.session.commit()

    retrieved_ds = db.session.get(DataSet, dataset.id)
    
    assert retrieved_ds.row_count == 1500
    assert len(retrieved_ds.column_names.split(',')) == 3
    

def test_6_to_dict_exposes_stats(test_client):
    user = _create_user()
    dataset = _create_dataset(user)
    
    dataset.download_count = 99
    dataset.row_count = 50
    dataset.column_names = "A,B"
    db.session.commit()
    
    db.session.refresh(dataset)

    with test_client.application.test_request_context():
        data = dataset.to_dict()

        assert "download_count" in data
        assert data["download_count"] == 99
        
        if "csv_metrics" in data:
            assert data["csv_metrics"]["row_count"] == 50
            assert data["csv_metrics"]["columns"] == ["A", "B"]