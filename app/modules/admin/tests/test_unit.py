import pytest
from flask import url_for
from app import create_app, db
from app.modules.auth.models import User, Role

@pytest.fixture
def app():
    app = create_app('testing') 
    app.config['SERVER_NAME'] = 'localhost' 
    app.config['WTF_CSRF_ENABLED'] = False 
    app.config['TESTING'] = True
    
    with app.app_context():
        # --- FIX IMPORTANTE: LIMPIEZA PREVIA ---
        db.session.remove()
        db.drop_all()   # Borramos todo lo que haya quedado de tests anteriores
        db.create_all() # Creamos las tablas limpias
        # ---------------------------------------
        
        # Ahora es seguro crear los roles
        roles = [
            Role(name='admin'),
            Role(name='standard user'),
            Role(name='curator'), 
            Role(name='guest') 
        ]
        db.session.add_all(roles)
        db.session.commit()
        
        yield app
        
        # Limpieza al terminar
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def setup_users(app):
    with app.app_context():
        admin_role = Role.query.filter_by(name='admin').one() 
        user_role = Role.query.filter_by(name='standard user').one()
        
        admin_user = User(email='admin@test.com', role=admin_role)
        admin_user.set_password('adminpass')
        
        normal_user = User(email='user@test.com', role=user_role)
        normal_user.set_password('userpass')
        
        db.session.add_all([admin_user, normal_user])
        db.session.commit()
        
        return admin_user.id, normal_user.id 

# --- HELPER: Login Real ---
def login_user_real(client, email, password):
    # Usamos /login que es la ruta correcta
    return client.post('/login', data={
        'email': email,
        'password': password
    }, follow_redirects=True)

# --- TESTS ---

def test_admin_index_not_logged_in(client, app):
    """Verifica redirección al login si no hay sesión."""
    response = client.get(url_for('admin.admin_index'), follow_redirects=False)
    assert response.status_code == 302
    assert '/login' in response.headers['Location']

def test_admin_index_standard_user_access(client, app, setup_users):
    """Verifica redirección al home si el usuario no es admin."""
    login_user_real(client, 'user@test.com', 'userpass')
    
    response = client.get(url_for('admin.admin_index'), follow_redirects=False)
    
    # Debe redirigir (302) porque no tiene permiso
    assert response.status_code == 302
    # Redirige al index público (http://localhost/ o /)
    assert response.headers['Location'] in ['http://localhost/', '/']

def test_admin_index_admin_user_access(client, app, setup_users):
    """Verifica que el admin ve la lista de usuarios."""
    login_user_real(client, 'admin@test.com', 'adminpass')
    
    response = client.get(url_for('admin.admin_index'))
    
    assert response.status_code == 200
    assert b"admin@test.com" in response.data 

def test_edit_user_get_loads_form_data(client, app, setup_users):
    """Verifica la carga del formulario de edición."""
    admin_id, normal_id = setup_users
    
    login_user_real(client, 'admin@test.com', 'adminpass')
    
    edit_url = url_for('admin.edit_user', user_id=normal_id)
    response = client.get(edit_url) 
    
    assert response.status_code == 200
    assert b"user@test.com" in response.data

def test_edit_user_post_single_role_change(client, app, setup_users):
    """[POSITIVO] Cambio de rol exitoso."""
    admin_id, normal_id = setup_users
    
    login_user_real(client, 'admin@test.com', 'adminpass')
    
    with app.app_context(): 
        curator_role_id = Role.query.filter_by(name='curator').one().id
        
        form_data = {
            'email': 'curator_updated@test.com', 
            'roles': str(curator_role_id) 
        }
        
        edit_url = url_for('admin.edit_user', user_id=normal_id)
            
    response = client.post(edit_url, data=form_data, follow_redirects=False)
    
    # Redirección exitosa tras guardar
    assert response.status_code == 302
    assert '/admin' in response.headers['Location']
    
    with app.app_context(): 
        updated_user = User.query.get(normal_id)
        assert updated_user.email == 'curator_updated@test.com'
        assert updated_user.role.name == 'curator'

def test_edit_user_post_invalid_email_no_update(client, app, setup_users):
    """[NEGATIVO] Email inválido."""
    admin_id, normal_id = setup_users
    
    login_user_real(client, 'admin@test.com', 'adminpass')
    
    with app.app_context():
        original_user = User.query.get(normal_id)
        original_email = original_user.email
        original_role_id = original_user.role.id
        
        form_data = {
            'email': 'esto_no_es_un_email', 
            'roles': str(original_role_id), 
        }
        edit_url = url_for('admin.edit_user', user_id=normal_id)
             
    response = client.post(edit_url, data=form_data, follow_redirects=True)
    
    assert response.status_code == 200 
    
    with app.app_context():
        updated_user = User.query.get(normal_id)
        assert updated_user.email == original_email

def test_edit_user_positive_promote_to_admin(client, app, setup_users):
    """[POSITIVO] Ascender a Admin."""
    admin_id, normal_id = setup_users
    
    login_user_real(client, 'admin@test.com', 'adminpass')
    
    with app.app_context():
        admin_role_id = Role.query.filter_by(name='admin').one().id
        
        form_data = {
            'email': 'new_admin@test.com',
            'roles': str(admin_role_id)
        }
        edit_url = url_for('admin.edit_user', user_id=normal_id)
            
    client.post(edit_url, data=form_data)
    
    with app.app_context():
        updated_user = User.query.get(normal_id)
        assert updated_user.role.name == 'admin'

def test_edit_user_positive_demote_to_guest(client, app, setup_users):
    """[POSITIVO] Degradar a Guest."""
    admin_id, normal_id = setup_users
    
    login_user_real(client, 'admin@test.com', 'adminpass')
    
    with app.app_context():
        guest_role_id = Role.query.filter_by(name='guest').one().id
        
        form_data = {
            'email': 'user@test.com',
            'roles': str(guest_role_id)
        }
        edit_url = url_for('admin.edit_user', user_id=normal_id)

    client.post(edit_url, data=form_data)
    
    with app.app_context():
        updated_user = User.query.get(normal_id)
        assert updated_user.role.name == 'guest'

def test_edit_user_negative_invalid_role_id(client, app, setup_users):
    """[NEGATIVO] Rol inválido."""
    admin_id, normal_id = setup_users
    
    login_user_real(client, 'admin@test.com', 'adminpass')
    
    with app.app_context():
        original_user = User.query.get(normal_id)
        original_role_name = original_user.role.name
        
        form_data = {
            'email': 'hacker@test.com',
            'roles': '9999' 
        }
        edit_url = url_for('admin.edit_user', user_id=normal_id)

    response = client.post(edit_url, data=form_data, follow_redirects=True)
    
    assert response.status_code == 200
    
    with app.app_context():
        user_after = User.query.get(normal_id)
        assert user_after.role.name == original_role_name

def test_edit_user_negative_unauthorized_access(client, app, setup_users):
    """[NEGATIVO] Usuario normal intenta editar."""
    admin_id, normal_id = setup_users
    
    # Login como NORMAL
    login_user_real(client, 'user@test.com', 'userpass')
        
    with app.app_context():
        admin_role_id = Role.query.filter_by(name='admin').one().id
        form_data = {
            'email': 'hack_attempt@test.com',
            'roles': str(admin_role_id)
        }
        edit_url = url_for('admin.edit_user', user_id=admin_id)

    response = client.post(edit_url, data=form_data, follow_redirects=False)
    
    # Debe ser redirigido fuera
    assert response.status_code == 302
    assert '/admin' not in response.headers['Location']
    
    with app.app_context():
        admin_user = User.query.get(admin_id)
        assert admin_user.email != 'hack_attempt@test.com'