from datetime import datetime
from unittest.mock import MagicMock, patch
from flask import url_for, session 
from app.modules.dataset.models import Community 

AUTH_ROUTES_SERVICE_PATH = 'app.modules.auth.routes.authentication_service' 

def create_mock_dataset(id, title):
    mock_ds = MagicMock()
    mock_ds.id = id

    mock_ds.ds_meta_data = MagicMock()
    mock_ds.ds_meta_data.title = title
    
    mock_ds.created_at = datetime.now()
    return mock_ds

@patch(AUTH_ROUTES_SERVICE_PATH)
@patch('app.modules.dataset.routes.community_service')
@patch('app.modules.dataset.routes.CommunityDatasetForm')
def test_manage_datasets_view_post(MockForm, mock_community_service, mock_auth_service, test_client):
    """TEST 2: Verifica la ruta POST."""

    mock_auth_service.is_session_valid.return_value = True

    form_data_datasets = ['10', '20']
    
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
        mock_form_instance.datasets.data = form_data_datasets

        MockDataSetQuery = MagicMock()
        fake_ds_list = [
            create_mock_dataset(id=10, title="DS Diez"),
            create_mock_dataset(id=20, title="DS Veinte")
        ]
        MockDataSetQuery.filter.return_value.all.return_value = fake_ds_list

        with patch('app.modules.dataset.routes.DataSet') as MockDataSetRoute:
            MockDataSetRoute.query = MockDataSetQuery
            
            with test_client.session_transaction() as sess:
                sess['user_session_key'] = 'mock-session-key-123' 

            rv = test_client.post(
                f"/community/{mock_community.id}/manage_datasets", 
                data={'datasets': form_data_datasets},
                follow_redirects=True
            )
            
            assert rv.status_code in [200, 302] 


@patch(AUTH_ROUTES_SERVICE_PATH)
@patch('app.modules.dataset.routes.community_service')
def test_list_communities_view_get(mock_community_service, mock_auth_service, test_client):
    """TEST 3: Verifica el listado."""

    mock_auth_service.is_session_valid.return_value = True

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

        with test_client.session_transaction() as sess:
            sess['user_session_key'] = 'mock-session-key-123' 

        rv = test_client.get("/communities/", follow_redirects=True)
        
        assert rv.status_code == 200
        assert b"Zeta Community" in rv.data
        assert b"Alpha Community" in rv.data


@patch(AUTH_ROUTES_SERVICE_PATH)
@patch('app.modules.dataset.routes.community_service')
def test_get_community_detail(mock_community_service, mock_auth_service, test_client):
    """
    Verifica la ruta GET /community/<id>.
    """
    
    mock_auth_service.is_session_valid.return_value = True
    
    with patch('flask_login.utils._get_user') as mock_current_user_func:
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.profile.name = "Test"
        mock_user.profile.surname = "User"
        mock_current_user_func.return_value = mock_user

        ds1 = create_mock_dataset(id=10, title="Dataset Associated 1") 
        ds2 = create_mock_dataset(id=20, title="Dataset Associated 2") 
        
        mock_community = MagicMock()
        mock_community.id = 123
        mock_community.name = "Detail Test Community"
        mock_community.description = "Checking dataset visibility"
        mock_community.logo_path = "/fake/logo.png"

        mock_community.user = MagicMock()
        mock_community.user.profile = MagicMock()
        mock_community.user.profile.name = "Creator Name"
        mock_community.user.profile.surname = "Creator Surname"
        mock_community.created_at = datetime.now()
        
        mock_datasets_list = [ds1, ds2]
        mock_query = MagicMock()
        mock_query.__iter__.return_value = iter(mock_datasets_list)
        mock_query.all.return_value = mock_datasets_list
        mock_query.count.return_value = len(mock_datasets_list)
        mock_community.datasets = mock_query
        
        mock_community_service.get_or_404.return_value = mock_community
        
        with test_client.session_transaction() as sess:
            sess['user_session_key'] = 'mock-session-key-123' 
            
        rv = test_client.get(f"/community/{mock_community.id}", follow_redirects=True)

        assert rv.status_code == 200
        assert b"Detail Test Community" in rv.data
        assert b"Dataset Associated 1" in rv.data

@patch(AUTH_ROUTES_SERVICE_PATH)
@patch('app.modules.dataset.routes.community_service')
@patch('app.modules.dataset.routes.CommunityForm') 
def test_edit_community_view_post(MockForm, mock_community_service, mock_auth_service, test_client): 
    """TEST 4: Verifica la edición de una comunidad (POST)."""

    mock_auth_service.is_session_valid.return_value = True

    form_data = {
        'name': "New Name", 
        'description': "New Description",
        'logo_path': "/new/logo.png"
    }

    with patch('flask_login.utils._get_user') as mock_current_user_func:
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.id = 1 
        mock_current_user_func.return_value = mock_user

        mock_community = MagicMock(id=1, user_id=1, name="Old Name")
        mock_community.user_id = mock_user.id 
        mock_community_service.get_or_404.return_value = mock_community

        mock_form_instance = MockForm.return_value
        mock_form_instance.validate_on_submit.return_value = True 
        mock_form_instance.name.data = form_data['name']
        mock_form_instance.description.data = form_data['description']
        mock_form_instance.logo_path.data = form_data['logo_path']
        
        with test_client.session_transaction() as sess:
            sess['user_session_key'] = 'mock-session-key-123' 

        rv = test_client.post(
            f"/community/{mock_community.id}/edit", 
            data=form_data, 
            follow_redirects=True
        )

        assert rv.status_code in [200, 302]
        
        mock_community_service.update_community.assert_called_once()