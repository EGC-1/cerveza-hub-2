import base64
from dataclasses import dataclass

import pytest
from unittest.mock import patch

# GitHubService está definido en app.modules.dataset.services
from app.modules.dataset.services import GitHubService


@dataclass
class _FakeMeta:
    title: str = "Unit test dataset"


@dataclass
class _FakeDataSet:
    id: int
    csv_file_path: str
    ds_meta_data: object


def _make_dataset(dataset_id: int, csv_path: str, title: str = "Unit test dataset") -> _FakeDataSet:
    return _FakeDataSet(id=dataset_id, csv_file_path=csv_path, ds_meta_data=_FakeMeta(title=title))


def test_headers_with_token(monkeypatch):
    # GitHubService lee env en __init__, así que hay que setear antes de instanciar
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    monkeypatch.setenv("GITHUB_REPO", "user/repo")

    svc = GitHubService()
    headers = svc._headers()

    assert headers["Authorization"] == "Bearer fake-token"
    assert headers["Accept"] == "application/vnd.github+json"


def test_headers_without_token(monkeypatch):
    # Asegura que no hay token aunque el entorno del dev/CI lo tenga
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("GITHUB_REPO", "user/repo")

    svc = GitHubService()
    headers = svc._headers()

    assert "Authorization" not in headers
    assert headers["Accept"] == "application/vnd.github+json"


def test_upload_dataset_csv_fails_if_file_not_exists(monkeypatch, tmp_path):
    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    monkeypatch.setenv("GITHUB_REPO", "user/repo")
    svc = GitHubService()

    dataset = _make_dataset(1, str(tmp_path / "missing.csv"))

    with pytest.raises(FileNotFoundError):
        svc.upload_dataset_csv(dataset)


def test_upload_dataset_csv_fails_without_repo_or_token(monkeypatch, tmp_path):
    csv_file = tmp_path / "data.csv"
    csv_file.write_text("name,ibu,brewery\nbeer,5,test")

    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_REPO", raising=False)

    svc = GitHubService()
    dataset = _make_dataset(1, str(csv_file))

    with pytest.raises(RuntimeError):
        svc.upload_dataset_csv(dataset)


@patch("app.modules.dataset.services.requests.put")
@patch("app.modules.dataset.services.requests.get")
def test_upload_dataset_csv_new_file(mock_get, mock_put, monkeypatch, tmp_path):
    csv_file = tmp_path / "data.csv"
    csv_content = "name,ibu,brewery\nbeer,5,test"
    csv_file.write_text(csv_content)

    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    monkeypatch.setenv("GITHUB_REPO", "user/repo")
    monkeypatch.setenv("GITHUB_BRANCH", "main")
    monkeypatch.setenv("GITHUB_BASE_PATH", "datasets")

    svc = GitHubService()
    dataset = _make_dataset(42, str(csv_file), title="A title")

    # GET check -> no existe
    mock_get.return_value.status_code = 404

    # PUT -> created
    mock_put.return_value.status_code = 201
    mock_put.return_value.json.return_value = {
        "content": {"html_url": "https://github.com/user/repo/blob/main/datasets/dataset_42/data.csv"}
    }

    url = svc.upload_dataset_csv(dataset)
    assert url == "https://github.com/user/repo/blob/main/datasets/dataset_42/data.csv"

    # Verifica base64
    sent_payload = mock_put.call_args.kwargs["json"]
    decoded = base64.b64decode(sent_payload["content"]).decode()
    assert decoded == csv_content
    assert "message" in sent_payload
    assert sent_payload["branch"] == "main"
    assert "sha" not in sent_payload


@patch("app.modules.dataset.services.requests.put")
@patch("app.modules.dataset.services.requests.get")
def test_upload_dataset_csv_update_existing_file(mock_get, mock_put, monkeypatch, tmp_path):
    csv_file = tmp_path / "data.csv"
    csv_file.write_text("name,ibu,brewery\nbeer,7,test")

    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    monkeypatch.setenv("GITHUB_REPO", "user/repo")
    monkeypatch.setenv("GITHUB_BRANCH", "main")
    monkeypatch.setenv("GITHUB_BASE_PATH", "datasets")

    svc = GitHubService()
    dataset = _make_dataset(7, str(csv_file), title="Another title")

    # GET check -> existe
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"sha": "existing-sha"}

    # PUT -> updated
    mock_put.return_value.status_code = 200
    mock_put.return_value.json.return_value = {
        "content": {"html_url": "https://github.com/user/repo/blob/main/datasets/dataset_7/data.csv"}
    }

    url = svc.upload_dataset_csv(dataset)
    assert url == "https://github.com/user/repo/blob/main/datasets/dataset_7/data.csv"

    sent_payload = mock_put.call_args.kwargs["json"]
    assert sent_payload["sha"] == "existing-sha"


@patch("app.modules.dataset.services.requests.put")
@patch("app.modules.dataset.services.requests.get")
def test_upload_dataset_builds_expected_github_contents_url(mock_get, mock_put, monkeypatch, tmp_path):
    """
    Verifica que el servicio construye la URL de la API de GitHub (contents endpoint)
    usando repo/branch/base_path y un path dependiente del dataset.id.
    """
    csv_file = tmp_path / "data.csv"
    csv_file.write_text("name,ibu,brewery\nbeer,5,test")

    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    monkeypatch.setenv("GITHUB_REPO", "user/repo")
    monkeypatch.setenv("GITHUB_BRANCH", "main")
    monkeypatch.setenv("GITHUB_BASE_PATH", "datasets")

    svc = GitHubService()
    dataset = _make_dataset(123, str(csv_file), title="Any title")

    mock_get.return_value.status_code = 404

    mock_put.return_value.status_code = 201
    mock_put.return_value.json.return_value = {
        "content": {"html_url": "https://github.com/user/repo/blob/main/datasets/dataset_123/data.csv"}
    }

    svc.upload_dataset_csv(dataset)

    # Lo importante aquí es que el GET vaya a la API de contents con repo y un path que incluya dataset_123 y data.csv
    called_url = mock_get.call_args.args[0]
    assert "https://api.github.com/repos/user/repo/contents/" in called_url
    assert "dataset_123" in called_url
    assert called_url.endswith("data.csv") or "data.csv" in called_url


@patch("app.modules.dataset.services.requests.put")
@patch("app.modules.dataset.services.requests.get")
def test_upload_dataset_includes_branch_in_put_payload(mock_get, mock_put, monkeypatch, tmp_path):
    """
    Asegura que SIEMPRE se manda 'branch' en el JSON del PUT (comportamiento actual),
    que es clave para el WI (usar repo/branch configurables).
    """
    csv_file = tmp_path / "data.csv"
    csv_file.write_text("name,ibu,brewery\nbeer,5,test")

    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    monkeypatch.setenv("GITHUB_REPO", "user/repo")
    monkeypatch.setenv("GITHUB_BRANCH", "develop")
    monkeypatch.setenv("GITHUB_BASE_PATH", "datasets")

    svc = GitHubService()
    dataset = _make_dataset(9, str(csv_file), title="Title")

    mock_get.return_value.status_code = 404
    mock_put.return_value.status_code = 201
    mock_put.return_value.json.return_value = {
        "content": {"html_url": "https://github.com/user/repo/blob/develop/datasets/dataset_9/data.csv"}
    }

    svc.upload_dataset_csv(dataset)

    payload = mock_put.call_args.kwargs["json"]
    assert payload["branch"] == "develop"


@patch("app.modules.dataset.services.requests.put")
@patch("app.modules.dataset.services.requests.get")
def test_upload_dataset_commit_message_mentions_dataset_title_or_id(mock_get, mock_put, monkeypatch, tmp_path):
    """
    Este test ata el contrato “humano” del commit message:
    que tenga algo identificable del dataset (título o id).
    Es útil para auditoría/traceabilidad del almacenamiento permanente.
    """
    csv_file = tmp_path / "data.csv"
    csv_file.write_text("name,ibu,brewery\nbeer,5,test")

    monkeypatch.setenv("GITHUB_TOKEN", "fake-token")
    monkeypatch.setenv("GITHUB_REPO", "user/repo")
    monkeypatch.setenv("GITHUB_BRANCH", "main")
    monkeypatch.setenv("GITHUB_BASE_PATH", "datasets")

    svc = GitHubService()
    dataset = _make_dataset(777, str(csv_file), title="My Dataset Title")

    mock_get.return_value.status_code = 404
    mock_put.return_value.status_code = 201
    mock_put.return_value.json.return_value = {
        "content": {"html_url": "https://github.com/user/repo/blob/main/datasets/dataset_777/data.csv"}
    }

    svc.upload_dataset_csv(dataset)

    payload = mock_put.call_args.kwargs["json"]
    msg = payload.get("message", "")
    assert msg  # no vacío
    assert ("My Dataset Title" in msg) or ("777" in msg)
