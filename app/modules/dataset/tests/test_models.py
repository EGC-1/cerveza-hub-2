import io

from app.modules.dataset.models import Community
from app.modules.auth.models import User
from app import db


def test_create_community_model(test_client):
    # Obtener usuario creado por el fixture
    user = User.query.first()
    assert user is not None

    # Crear comunidad a nivel de modelo
    community = Community(
        name="Test Community",
        description="Descripción de prueba",
        logo_path="/tmp/fake_logo.png",
        creator_user_id=user.id,
    )
    db.session.add(community)
    db.session.commit()

    # Recuperar desde la BD y comprobar campos
    c = Community.query.filter_by(name="Test Community").first()
    assert c is not None
    assert c.creator_user_id == user.id
    assert "Test Community" in repr(c)
    d = c.to_dict()
    assert d["name"] == "Test Community"
    assert "logo_path" in d
