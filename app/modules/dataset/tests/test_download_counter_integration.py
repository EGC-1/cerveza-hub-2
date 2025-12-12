import pytest
import os
import shutil
from app import db
from app.modules.auth.models import User, Role
from app.modules.dataset.models import DataSet, DSMetaData, PublicationType

# --- FIXTURES ---

@pytest.fixture
def dataset_scenario(test_client, tmp_path):
    """
    Crea todo el escenario necesario: Rol, Usuario, Archivo físico y Dataset.
    """

    with test_client.application.app_context():
        
        role = Role.query.get(1)
        if not role:
            role = Role(id=1, name="user", description="Standard user")
            db.session.add(role)
            db.session.commit()

        user = User(email="integration@test.com", password="password123")
        db.session.add(user)
        db.session.commit()

        meta = DSMetaData(
            title="Integration Test DS", 
            description="Desc", 
            publication_type=PublicationType.JOURNAL_ARTICLE,
            dataset_doi="10.1234/integration"
        )
        db.session.add(meta)
        db.session.commit()

        dataset_folder = tmp_path / "datasets"
        dataset_folder.mkdir()
        dummy_csv = dataset_folder / "data.csv"
        dummy_csv.write_text("col1,col2\nval1,val2")
        
        dataset = DataSet(
            user_id=user.id, 
            ds_meta_data_id=meta.id,
            csv_file_path=str(dummy_csv), 
            download_count=0
        )
        db.session.add(dataset)
        db.session.commit()

        return user.id, dataset.id


# --- TESTS ---

def test_download_route_happy_path(test_client, dataset_scenario):
    """
    Escenario Ideal: Usuario entra -> Descarga ZIP -> Contador sube.
    """
    user_id, dataset_id = dataset_scenario

    response = test_client.get(f"/dataset/download/{dataset_id}")

    assert response.status_code == 200
    assert response.mimetype == "application/zip"
    
    cookie = test_client.get_cookie('download_cookie')
    assert cookie is not None
    assert cookie.value != ""

    with test_client.application.app_context():
        dataset = db.session.get(DataSet, dataset_id)
        assert dataset.download_count == 1
        
