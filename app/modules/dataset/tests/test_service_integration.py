from io import BytesIO
import os
from unittest.mock import patch 

from werkzeug.datastructures import FileStorage
from unittest.mock import MagicMock
from app.modules.dataset.models import Community
from datetime import datetime
from app.modules.dataset.services import CommunityService
from app.modules.auth.models import User
from app import db
from app.modules.conftest import login
from unittest.mock import patch, MagicMock, PropertyMock
from sqlalchemy import inspect
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

class FakeDataSet:
    """Clase ligera para testear (Fake) que engaña a SQLAlchemy."""
    def __init__(self, id, title):
        self.id = id
        self._title = title
        
        # --- CONFIGURACIÓN DEL MOCK DE ESTADO SQLALCHEMY ---
        mock_state = MagicMock()
        
        # 1. Nombre de la clase (para logs)
        mock_state.class_.__name__ = 'DataSet'
        
        # 2. Referencia al objeto
        mock_state.obj.return_value = self
        
        # 3. Flags Booleanos (Evita error 'Instance has been deleted')
        mock_state._deleted = False
        mock_state.expired = False
        mock_state.is_property = False
        
        # 4. Simular Primary Key (Evita error 'Instance is not persisted')
        mock_state.key = (id,) 

        self._sa_instance_state = mock_state

    def name(self):
        return self._title

    def __repr__(self):
        return f"<FakeDataSet ID:{self.id} - {self._title}>"
    
    def __str__(self):
        return self._title

def create_mock_dataset(id, title):
    return FakeDataSet(id=id, title=title)


# ==========================================
# 2. LOS 3 TESTS
# ==========================================

@patch('app.modules.dataset.services.DataSet')
def test_update_datasets_service(MockDataSetClass, test_client):
    """
    TEST 1: Verifica actualización de datasets usando inspección de memoria.
    """
    user = User.query.first()
    if not user:
        user = MagicMock()
        user.id = 1
        user.profile.surname = "Test"
        user.profile.name = "User"

    service = CommunityService()
    community_form = DummyForm("Datasets Test Community", "Testing association")
    fake_file = FileStorage(stream=BytesIO(b"data"), filename="logo.png", content_type="image/png")
    
    with patch('os.makedirs'), patch('os.path.exists', return_value=True), patch.object(fake_file, 'save'):
        community = service.create_from_form(form=community_form, current_user=user, logo_file=fake_file)

    # Fakes
    ds1 = create_mock_dataset(id=10, title="Dataset Ten")
    ds3 = create_mock_dataset(id=30, title="Dataset Thirty")
    
    # Mockear el commit
    service.repository.session.commit = MagicMock() 

    # Ejecutar
    service.update_datasets(community.id, [ds1, ds3])

    # --- VERIFICACIÓN CORREGIDA (Usando inspect) ---
    # Como 'community.datasets' es dinámico (Query), no podemos hacer len().
    # Como usamos Fakes y no hay commit, no podemos hacer .all() (iría a la DB vacía).
    # SOLUCIÓN: Inspeccionamos qué se ha añadido a la relación en la memoria de Python.
    
    history = inspect(community).attrs.datasets.history
    
    # history.added devuelve la lista de objetos agregados en esta sesión
    added_items = history.added
    
    assert len(added_items) == 2
    ids = sorted([d.id for d in added_items])
    assert ids == [10, 30]
    
    # Limpieza
    try:
        if community.logo_path and os.path.exists(community.logo_path):
            os.remove(community.logo_path)
    except Exception:
        pass


@patch('app.modules.dataset.routes.community_service')
@patch('app.modules.dataset.routes.CommunityDatasetForm')
def test_manage_datasets_view_post(MockForm, mock_community_service, test_client):
    """TEST 2: Verifica la ruta POST."""
    
    with patch('flask_login.utils._get_user') as mock_current_user_func:
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.profile.name = "Test"
        mock_user.profile.surname = "User"
        mock_current_user_func.return_value = mock_user

        mock_community = MagicMock(spec=Community)
        mock_community.id = 99
        mock_community.name = "Mock Community"
        mock_community_service.get_or_404.return_value = mock_community
        
        mock_form_instance = MockForm.return_value
        mock_form_instance.validate_on_submit.return_value = True
        mock_form_instance.datasets.data = ['10', '20'] 
        
        MockDataSetQuery = MagicMock()
        fake_ds_list = [
            create_mock_dataset(id=10, title="DS Diez"),
            create_mock_dataset(id=20, title="DS Veinte")
        ]
        MockDataSetQuery.filter.return_value.all.return_value = fake_ds_list
        
        with patch('app.modules.dataset.routes.DataSet') as MockDataSetRoute:
            MockDataSetRoute.query = MockDataSetQuery
            
            rv = test_client.post(f"/community/{mock_community.id}/manage_datasets", follow_redirects=True)
            
            mock_community_service.update_datasets.assert_called_once_with(
                mock_community, 
                fake_ds_list
            )
            assert rv.status_code == 200


@patch('app.modules.dataset.routes.community_service')
def test_list_communities_view_get(mock_community_service, test_client):
    """TEST 3: Verifica el listado."""
    
    mock_community1 = MagicMock() 
    mock_community1.id = 1
    mock_community1.name = "Zeta Community"
    mock_community1.description = "Oldest community"
    mock_community1.logo_path = "/fake/path/z.png" 
    mock_community1.created_at = datetime(2024, 1, 1) 
    mock_community1.to_dict.return_value = {} 

    mock_community2 = MagicMock()
    mock_community2.id = 2
    mock_community2.name = "Alpha Community"
    mock_community2.description = "Newest community"
    mock_community2.logo_path = "/fake/path/a.png"
    mock_community2.created_at = datetime(2024, 2, 1) 
    mock_community2.to_dict.return_value = {}
    
    mock_community_service.get_all_communities.return_value = [mock_community2, mock_community1]
    
    with patch('flask_login.utils._get_user') as mock_current_user_func:
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.profile.name = "Test"
        mock_user.profile.surname = "User"
        mock_current_user_func.return_value = mock_user

        rv = test_client.get("/communities/")
        
        assert rv.status_code == 200
        html = rv.data.decode('utf-8')
        assert html.find("Alpha Community") < html.find("Zeta Community")


@patch('app.modules.dataset.routes.community_service')
def test_get_community_detail(mock_community_service, test_client):
    """
    Verifica la ruta GET /community/<id>.
    """
    with patch('flask_login.utils._get_user') as mock_current_user_func:
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.profile.name = "Test"
        mock_user.profile.surname = "User"
        mock_current_user_func.return_value = mock_user

        # 1. Configurar Datasets
        ds1 = MagicMock()
        ds1.id = 10
        ds1.created_at = datetime.now()
        # Para que {{ dataset.name() }} devuelva texto
        ds1.name.return_value = "Dataset Associated 1"
        ds1.ds_meta_data.title = "Dataset Associated 1" # Por si usa .title

        ds2 = MagicMock()
        ds2.id = 20
        ds2.created_at = datetime.now()
        # Para que {{ dataset.name() }} devuelva texto
        ds2.name.return_value = "Dataset Associated 2"
        ds2.ds_meta_data.title = "Dataset Associated 2"

        # 2. Configurar Comunidad
        mock_community = MagicMock()
        mock_community.id = 123
        mock_community.name = "Detail Test Community"
        mock_community.description = "Checking dataset visibility"
        mock_community.logo_path = "/fake/logo.png"
        
        mock_community.user.profile.name = "Creator Name"
        mock_community.user.profile.surname = "Creator Surname"
        mock_community.created_at = datetime.now()

        # 3. Configurar la relación datasets (LA SOLUCIÓN ROBUSTA)
        mock_datasets_list = [ds1, ds2]
        
        # Creamos un Mock que finge ser la Query de SQLAlchemy
        mock_query = MagicMock()
        
        # A) Si el template hace: {% for ds in community.datasets %}
        mock_query.__iter__.return_value = iter(mock_datasets_list)
        
        # B) Si el template hace: community.datasets.all()
        mock_query.all.return_value = mock_datasets_list
        
        # C) Si el template hace: community.datasets.count()
        mock_query.count.return_value = len(mock_datasets_list)

        # Asignamos este Mock polivalente a la comunidad
        mock_community.datasets = mock_query
        
        # 4. Configurar servicio
        mock_community_service.get_or_404.return_value = mock_community

        # 5. Ejecutar (con follow_redirects para evitar el 308)
        rv = test_client.get(f"/community/{mock_community.id}", follow_redirects=True)

        assert rv.status_code == 200
        html = rv.data.decode('utf-8')

        # 6. Verificaciones
        assert "Detail Test Community" in html
        assert "Dataset Associated 1" in html
        assert "Dataset Associated 2" in html