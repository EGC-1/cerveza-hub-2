import io
from unittest.mock import patch

from app.modules.conftest import login
from app.modules.dataset.models import DataSet


def _beerish_csv_bytes() -> bytes:
    # Debe pasar validate_csv_file(): incluye >=3 keywords (name, ibu, brewery)
    # y >=1 strong indicator (ibu o brewery)
    return b"name,ibu,brewery\nheineken,35,heineken\n"


def _base_form_data(storage_service_value=None):
    data = {
        "title": "Integration Dataset",
        "desc": "Dataset for integration testing",
        "publication_type": "none",
        "tags": "tag1,tag2",
        "authors-0-name": "Test Author",
        "authors-0-affiliation": "Test Lab",
        "authors-0-orcid": "",
        "authors-0-gnd": "",
        "csv_file": (io.BytesIO(_beerish_csv_bytes()), "test.csv"),
    }
    if storage_service_value is not None:
        data["storage_service"] = storage_service_value
    return data


def test_create_dataset_with_github_storage_updates_metadata_and_redirects(test_client):
    login(test_client, "test@example.com", "test1234")

    fake_github_url = "https://github.com/owner/repo/blob/main/datasets/dataset_1/test.csv"

    with patch("app.modules.dataset.routes.github_service") as gh_service:
        gh_service.upload_dataset_csv.return_value = fake_github_url

        resp = test_client.post(
            "/dataset/upload",
            data=_base_form_data(storage_service_value="github"),
            content_type="multipart/form-data",
            follow_redirects=False,
        )

        # En éxito: DOI fake => redirect a /doi/<doi_only>
        assert resp.status_code in (301, 302)
        assert "/doi/" in resp.headers.get("Location", "")

        assert gh_service.upload_dataset_csv.call_count == 1

    ds = DataSet.query.order_by(DataSet.id.desc()).first()
    assert ds is not None
    assert ds.ds_meta_data.storage_service == "github"
    assert ds.ds_meta_data.storage_record_url == fake_github_url
    assert ds.ds_meta_data.dataset_doi
    assert ds.ds_meta_data.dataset_doi.startswith("10.9999/cervezahub.github.dataset.")


def test_create_dataset_with_github_storage_handles_upload_failure_gracefully(test_client):
    login(test_client, "test@example.com", "test1234")

    with patch("app.modules.dataset.routes.github_service") as gh_service:
        gh_service.upload_dataset_csv.side_effect = Exception("boom")

        resp = test_client.post(
            "/dataset/upload",
            data=_base_form_data(storage_service_value="github"),
            content_type="multipart/form-data",
            follow_redirects=False,
        )

        # En fallo: NO DOI => redirect a unsynchronized
        assert resp.status_code in (301, 302)
        assert "/dataset/unsynchronized/" in resp.headers.get("Location", "")

        assert gh_service.upload_dataset_csv.call_count == 1

    ds = DataSet.query.order_by(DataSet.id.desc()).first()
    assert ds is not None
    assert not ds.ds_meta_data.dataset_doi  # fallo github => no DOI
    assert ds.ds_meta_data.storage_service == "github"  # quedó guardado antes del try


from unittest.mock import patch
from app.modules.conftest import login
from app.modules.dataset.models import DataSet


def test_create_dataset_without_storage_service_rerenders_form_and_does_not_call_remote_services(test_client):
    """
    Comportamiento actual:
    - storage_service es SelectField con choices zenodo/github.
    - Si no se envía storage_service (o viene inválido), WTForms no valida
      y la vista re-renderiza (200) en vez de redirigir.
    - No debe llamar a servicios remotos ni crear el dataset.
    """
    login(test_client, "test@example.com", "test1234")

    before_count = DataSet.query.count()

    with patch("app.modules.dataset.routes.github_service") as gh_service, \
         patch("app.modules.dataset.routes.zenodo_service") as z_service:

        resp = test_client.post(
            "/dataset/upload",
            data=_base_form_data(storage_service_value=None),  # no mandamos el campo
            content_type="multipart/form-data",
            follow_redirects=False,
        )

        assert resp.status_code == 200  # re-render del formulario
        assert gh_service.upload_dataset_csv.call_count == 0
        assert z_service.create_new_deposition.call_count == 0

    after_count = DataSet.query.count()
    assert after_count == before_count
