import pytest
import os
import uuid
from app import db
from app.modules.auth.models import User, Role
from app.modules.dataset.models import DataSet, DSMetaData, PublicationType

@pytest.fixture(scope="function")
def dataset_scenario(test_client):
    """
    Crea un Dataset PRIVADO (no público, accesible solo bajo ciertas condiciones).
    Tiene su archivo físico real para que la descarga funcione.
    """
    unique_id = str(uuid.uuid4())[:8]
    
    with test_client.application.app_context():
        # Limpieza previa para evitar residuos
        db.session.query(DataSet).filter(DataSet.ds_meta_data_id.in_(
            db.session.query(DSMetaData.id).filter(DSMetaData.title.like(f"Private Dataset {unique_id}%"))
        )).delete(synchronize_session=False)
        db.session.query(DSMetaData).filter(DSMetaData.title.like(f"Private Dataset {unique_id}%")).delete()
        db.session.query(User).filter(User.email.like(f"owner_{unique_id}%")).delete()
        db.session.commit()
        
        role = Role.query.get(1)
        if not role:
            role = Role(id=1, name="user", description="Standard user")
            db.session.add(role)
            db.session.commit()

        owner_email = f"owner_{unique_id}@test.com"
        owner = User(email=owner_email, password="password123")
        db.session.add(owner)
        db.session.commit()

        meta = DSMetaData(
            title=f"Private Dataset {unique_id}", 
            description="Private Description", 
            publication_type=PublicationType.JOURNAL_ARTICLE,
            dataset_doi=f"10.1234/private_{unique_id}"
            # Agrega is_public=False si existe en el modelo
        )
        db.session.add(meta)
        db.session.commit()

        csv_path = f"test_private_data_{unique_id}.csv"
        with open(csv_path, "w") as f:
            f.write("header1,header2\ndata1,data2")
        
        dataset = DataSet(
            user_id=owner.id, 
            ds_meta_data_id=meta.id,
            csv_file_path=csv_path, 
            download_count=0
        )
        db.session.add(dataset)
        db.session.commit()
                
        return dataset.id, csv_path

@pytest.fixture(scope="function")
def public_dataset_scenario(test_client):
    """
    Crea un Dataset que simula ser PÚBLICO (accesible).
    Tiene su archivo físico real para que la descarga funcione.
    """
    unique_id = str(uuid.uuid4())[:8]
    
    with test_client.application.app_context():
        db.session.query(DataSet).filter(DataSet.ds_meta_data_id.in_(
            db.session.query(DSMetaData.id).filter(DSMetaData.title.like(f"Public Dataset {unique_id}%"))
        )).delete(synchronize_session=False)
        db.session.query(DSMetaData).filter(DSMetaData.title.like(f"Public Dataset {unique_id}%")).delete()
        db.session.query(User).filter(User.email.like(f"owner_{unique_id}%")).delete()
        db.session.commit()
                
        role = Role.query.get(1)
        if not role:
            role = Role(id=1, name="user", description="Standard user")
            db.session.add(role)
            db.session.commit()

        owner_email = f"owner_{unique_id}@test.com"
        owner = User(email=owner_email, password="password123")
        db.session.add(owner)
        db.session.commit()

        meta = DSMetaData(
            title=f"Public Dataset {unique_id}", 
            description="Public Description", 
            publication_type=PublicationType.JOURNAL_ARTICLE,
            dataset_doi=f"10.1234/public_{unique_id}"
        )
        db.session.add(meta)
        db.session.commit()

        csv_path = f"test_public_data_{unique_id}.csv"
        with open(csv_path, "w") as f:
            f.write("header1,header2\ndata1,data2")
        
        dataset = DataSet(
            user_id=owner.id, 
            ds_meta_data_id=meta.id,
            csv_file_path=csv_path, 
            download_count=0
        )
        db.session.add(dataset)
        db.session.commit()
                
        return dataset.id, csv_path


# --- TESTS  ---

def test_download_route_happy_path(test_client, dataset_scenario):
    """
    Caso 1: Primera descarga exitosa.
    """
    dataset_id, csv_path = dataset_scenario

    test_client.delete_cookie('download_cookie')

    response = test_client.get(f"/dataset/download/{dataset_id}")

    assert response.status_code == 200
    assert response.mimetype == "application/zip"
    
    cookie = test_client.get_cookie('download_cookie')
    assert cookie is not None

    with test_client.application.app_context():
        dataset = db.session.get(DataSet, dataset_id)
        assert dataset.download_count == 1
    
    db.session.close()
    if os.path.exists(csv_path):
        os.remove(csv_path)


def test_download_route_spam_protection(test_client, dataset_scenario):
    """
    Caso 2: Mismo usuario descarga varias veces -> Cuenta 1.
    """
    dataset_id, csv_path = dataset_scenario
    test_client.delete_cookie('download_cookie')
    
    test_client.get(f"/dataset/download/{dataset_id}")
    test_client.get(f"/dataset/download/{dataset_id}")
    test_client.get(f"/dataset/download/{dataset_id}")

    with test_client.application.app_context():
        dataset = db.session.get(DataSet, dataset_id)
        assert dataset.download_count == 1
    
    db.session.close()
    if os.path.exists(csv_path):
        os.remove(csv_path)


def test_public_dataset_downloads_by_different_users(test_client, public_dataset_scenario):
    """
    Caso 3: DOS usuarios diferentes descargan el dataset público.
    """
    dataset_id, csv_path = public_dataset_scenario
    
    with test_client.application.app_context():
        dataset = db.session.get(DataSet, dataset_id)
        assert dataset is not None, f"Dataset con ID {dataset_id} no existe en BD"
        assert os.path.exists(csv_path), f"Archivo CSV no existe: {csv_path}"

    test_client.delete_cookie('download_cookie')

    # --- USUARIO A ---
    resp_a = test_client.get(f"/dataset/download/{dataset_id}")
    assert resp_a.status_code == 200, f"Error en descarga A: {resp_a.status_code}"

    # --- USUARIO B (Simula usuario distinto borrando cookie) ---
    test_client.delete_cookie('download_cookie')
    
    resp_b = test_client.get(f"/dataset/download/{dataset_id}")
    assert resp_b.status_code == 200, f"Error en descarga B: {resp_b.status_code}"

    with test_client.application.app_context():
        dataset = db.session.get(DataSet, dataset_id)
        assert dataset.download_count == 2, f"Contador esperado: 2, obtenido: {dataset.download_count}"
    
    db.session.close()
    if os.path.exists(csv_path):
        os.remove(csv_path)
        