

import pytest

def test_create_deposit_structure(client):
    """UNITARIO: Verifica que la estructura del JSON de respuesta sea correcta."""
    
    payload = {"metadata": {"title": "Unit Test"}}
    response = client.post('/api/deposit/depositions', json=payload)
    
    assert response.status_code == 201
    data = response.get_json()
    
    assert "id" in data
    assert data["state"] == "unsubmitted"
    assert data["submitted"] is False
    assert "links" in data
    assert "bucket" in data["links"]

def test_get_deposit_not_found(client):
    """UNITARIO: Verifica el error 404 si el ID no existe."""
    response = client.get('/api/deposit/depositions/999999')
    assert response.status_code == 404
    assert response.get_json() == {"message": "Not found"}

def test_upload_file_no_file_part(client):
    """UNITARIO: Verifica error 400 si no se envía el archivo."""
    create_res = client.post('/api/deposit/depositions', json={})
    dep_id = create_res.get_json()['id']
    
    response = client.post(f'/api/deposit/depositions/{dep_id}/files', data={})
    assert response.status_code == 400
    assert response.get_json() == {"message": "No file part"}

def test_upload_file_to_non_existent_id(client):
    """UNITARIO: Subir archivo a un ID fantasma."""
    response = client.post('/api/deposit/depositions/12345/files', data={'file': 'test'})
    assert response.status_code == 404