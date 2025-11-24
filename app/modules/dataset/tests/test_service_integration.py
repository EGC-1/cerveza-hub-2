from io import BytesIO
import os
from unittest.mock import patch 

from werkzeug.datastructures import FileStorage
from unittest.mock import MagicMock
from app.modules.dataset.models import Community

from app.modules.dataset.services import CommunityService
from app.modules.auth.models import User
from app import db
from app.modules.conftest import login

class DummyForm:
    def __init__(self, name, description, logo_path="/tmp/test_logo_placeholder.png"): 
        self._data = {"name": name, "description": description, "logo_path": logo_path}

    def get_community_data(self):
        return {
            "name": self._data["name"], 
            "description": self._data["description"], 
            "logo_path": self._data["logo_path"]
        }


def test_create_community_service(test_client):
    user = User.query.first()
    assert user is not None

    dummy = DummyForm(
        "Service Community", 
        "Servicio test",
        logo_path="/tmp/test_community/service_logo.png" 
    )
    fake_file = FileStorage(stream=BytesIO(b"fakepngdata"), filename="logo.png", content_type="image/png")

    service = CommunityService()
    community = service.create_from_form(form=dummy, current_user=user, logo_file=fake_file)

    assert community is not None
    assert community.id is not None
    assert os.path.exists(community.logo_path)
    try:
        if os.path.exists(community.logo_path):
            os.remove(community.logo_path)
        logo_dir = os.path.dirname(community.logo_path)
        if os.path.isdir(logo_dir):
            os.rmdir(logo_dir)
    except Exception:
        pass

def test_create_community_view_post(test_client):

    login(test_client, "test@example.com", "test1234")
    with patch('app.modules.dataset.routes.community_service') as mock_service:
        

        mock_community = MagicMock(spec=Community)
        mock_community.name = "Integration Community"
        mock_community.logo_path = "/tmp/fake_integration_logo.png"

        mock_service.create_from_form.return_value = mock_community
        
        data = {
            "name": "Integration Community",
            "description": "Integration test description",
            "logo": (BytesIO(b"fakepngdata"), "logo.png"),
        }
        rv = test_client.post("/community/create", 
                              data=data, 
                              content_type="multipart/form-data", 
                              follow_redirects=True)

        assert rv.status_code == 200
        mock_service.create_from_form.assert_called_once()

        pass

 