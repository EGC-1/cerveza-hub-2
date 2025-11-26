import io

from app.modules.dataset.models import Community
from app.modules.auth.models import User
from app import db


def test_create_community_model(test_client):
    user = User.query.first()
    assert user is not None
    community = Community(
        name="Test Community",
        description="Descripción de prueba",
        logo_path="/tmp/fake_logo.png",
        creator_user_id=user.id,
    )
    db.session.add(community)
    db.session.commit()
    c = Community.query.filter_by(name="Test Community").first()
    assert c is not None
    assert c.creator_user_id == user.id
    assert "Test Community" in repr(c)
    assert c.name == "Test Community"
    assert c.logo_path == "/tmp/fake_logo.png"
    assert c.description == "Descripción de prueba"
