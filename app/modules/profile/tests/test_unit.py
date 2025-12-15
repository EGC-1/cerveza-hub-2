import pytest

from app import db
from app.modules.auth.models import User
from app.modules.conftest import login, logout
from app.modules.profile.models import UserProfile


@pytest.fixture(scope="module")
def test_client(test_client):
    """
    Extends the test_client fixture to add additional specific data for module testing.
    Creates a standard user and an administrator user.
    """
    with test_client.application.app_context():
        user_test = User(email="user@example.com", password="test1234")
        db.session.add(user_test)
        db.session.commit() 

        profile = UserProfile(user_id=user_test.id, name="Name", surname="Surname")
        db.session.add(profile)
        
        admin_test = User(email="admin@example.com", password="admin1234")
        db.session.add(admin_test)
        db.session.commit()

        admin_profile = UserProfile(user_id=admin_test.id, name="Admin", surname="Superuser")
        db.session.add(admin_profile)
        
        db.session.commit()

    yield test_client

def test_edit_profile_page_get(test_client):
    """
    Tests access to the profile editing page via a GET request.
    """
    from app.modules.auth.models import User
    from app.modules.profile.models import UserProfile
    
    login_response = login(test_client, "user@example.com", "test1234")
    
    response = test_client.get("/profile/edit")
    assert response.status_code == 200

def test_admin_profile_access(test_client):
    """
    Test opcional para verificar que el admin también funciona.
    """
    logout(test_client) 
    login(test_client, "admin@example.com", "admin1234")
    
    response = test_client.get("/profile/edit")
    assert response.status_code == 200