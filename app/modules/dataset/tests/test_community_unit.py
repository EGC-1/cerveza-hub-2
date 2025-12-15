from datetime import datetime
from unittest.mock import MagicMock, patch
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

        fake_ds_list = [
            create_mock_dataset(10, "DS Diez"),
            create_mock_dataset(20, "DS Veinte"),
        ]

        with patch('app.modules.dataset.routes.DataSet') as MockDataSetRoute:
            MockDataSetRoute.query.filter.return_value.all.return_value = fake_ds_list

            with test_client.session_transaction() as sess:
                sess['user_session_key'] = 'mock-session-key-123'

            rv = test_client.post(
                f"/community/{mock_community.id}/manage_datasets",
                data={'datasets': form_data_datasets},
                follow_redirects=True
            )
            assert rv.status_code in (200, 302)


@patch(AUTH_ROUTES_SERVICE_PATH)
@patch('app.modules.dataset.routes.community_service')
def test_list_communities_view_get(mock_community_service, mock_auth_service, test_client):
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
