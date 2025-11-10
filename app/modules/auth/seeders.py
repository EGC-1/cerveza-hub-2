from app.modules.auth.models import User, Role 
from app.modules.profile.models import UserProfile 
from core.seeders.BaseSeeder import BaseSeeder
from app import db 

class AuthSeeder(BaseSeeder):

    priority = 1  

    def run(self):
        
        
        roles_a_insertar = [
            {'name': 'admin', 'description': 'Acceso total y gestión de usuarios.'},
            {'name': 'curator', 'description': 'Puede añadir, editar y eliminar contenido.'},
            {'name': 'standard user', 'description': 'Usuario autenticado.'},
        ]

        print("--- 1. Verificando y creando Roles ---")
        
        for role_data in roles_a_insertar:
            role = Role.query.filter_by(name=role_data['name']).first()
            
            if not role:
                new_role = Role(**role_data)
                db.session.add(new_role)
                print(f"-> Rol creado: {role_data['name']}")
            
        db.session.commit()


        admin_role = Role.query.filter_by(name='admin').first()
        
        if admin_role and not User.query.filter_by(email='admin@uvl.com').first():
            
            admin_user = User(
                email='admin@uvl.com', 
                password='123456', 
                role_id=admin_role.id 
            )
            seeded_admin = self.seed([admin_user])[0] 
            
            admin_profile_data = {
                "user_id": seeded_admin.id, 
                "orcid": "ADMIN",
                "affiliation": "CervezaHub Administration",
                "name": "Super",
                "surname": "Admin",
            }
            admin_profile = UserProfile(**admin_profile_data)
            self.seed([admin_profile])

            print("-> Usuario Administrador creado: admin@uvl.com con perfil.")


        standard_role = Role.query.filter_by(name='standard user').first()
        
        users_to_seed = []
        user_data_list = [
            {"email": "user1@example.com", "password": "1234"},
            {"email": "user2@example.com", "password": "1234"},
        ]
        names = [("John", "Doe"), ("Jane", "Doe")]

        print("--- Verificando y creando Usuarios de Prueba ---")

        for data in user_data_list:
            if not User.query.filter_by(email=data['email']).first():
                new_user = User(
                    email=data['email'], 
                    password=data['password'], 
                    role_id=standard_role.id
                )
                users_to_seed.append(new_user)
                print(f"-> Usuario de prueba añadido: {data['email']}")
            
        if users_to_seed:
            seeded_users = self.seed(users_to_seed)
        else:
            seeded_users = User.query.filter(
                User.email.in_(['user1@example.com', 'user2@example.com'])
            ).all()

        user_profiles_to_create = []
        
        for user, name in zip(seeded_users, names):
            if not user.profile: 
                profile_data = {
                    "user_id": user.id,
                    "orcid": "",
                    "affiliation": "Some University",
                    "name": name[0],
                    "surname": name[1],
                }
                user_profile = UserProfile(**profile_data)
                user_profiles_to_create.append(user_profile)

        if user_profiles_to_create:
            self.seed(user_profiles_to_create)
            print(f"--- {len(user_profiles_to_create)} Perfiles de prueba creados. ---")
        else:
             print("--- 0 Perfiles de prueba creados (ya existen). ---")

    def unseed(self):
        pass