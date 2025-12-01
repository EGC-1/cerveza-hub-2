import pytest

from app import db
from app.modules.auth.models import User
from app.modules.conftest import login, logout
from app.modules.profile.models import UserProfile


@pytest.fixture(scope="module")
def test_client(test_client):
    """
    Extends the test_client fixture to add additional specific data for module testing.
    for module testing (por example, new users)
    """
    with test_client.application.app_context():
        user_test = User(email="user@example.com", password="test1234")
        db.session.add(user_test)
        db.session.commit()

        profile = UserProfile(user_id=user_test.id, name="Name", surname="Surname")
        db.session.add(profile)
        db.session.commit()

    yield test_client


def test_edit_profile_page_get(test_client):
    """
    Tests access to the profile editing page via a GET request.
    """
    from app.modules.auth.models import User
    from app.modules.profile.models import UserProfile
    from app import db

    user = User.query.filter_by(email="user@example.com").first()
    if not user:
        user = User(email="user@example.com", password="test1234")
        db.session.add(user)
        db.session.commit()
        
        # Crear perfil asociado
        profile = UserProfile(user_id=user.id, name="Name", surname="Surname")
        db.session.add(profile)
        db.session.commit()

    login_response = login(test_client, "user@example.com", "test1234")
    

    response = test_client.get("/profile/edit")
    
    assert response.status_code == 200