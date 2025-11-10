from datetime import datetime, timezone, timedelta

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash
from app import db
import secrets

class Role(db.Model):
    __tablename__ = 'roles'  

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.String(255))
    

    def __repr__(self):
        return f'<Role {self.name}>'

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)

    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False, default=1)
    
    email = db.Column(db.String(256), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    reset_token = db.Column(db.String(128), index=True, unique=True, nullable=True)
    token_expiration = db.Column(db.DateTime, nullable=True)



    role = db.relationship("Role", backref="users", lazy=True)
    
    data_sets = db.relationship("DataSet", backref="user", lazy=True)
    profile = db.relationship("UserProfile", backref="user", uselist=False)

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if "password" in kwargs:
            self.set_password(kwargs["password"])

    def __repr__(self):
        return f"<User {self.email}>"

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def temp_folder(self) -> str:
        from app.modules.auth.services import AuthenticationService

        return AuthenticationService().temp_folder_by_user(self)

    

    def generate_reset_token(self):
        """
        Genera un token hexadecimal seguro, lo guarda en el usuario con una expiración
        de 1 hora y retorna el valor del token.
        """
        token = secrets.token_hex(32) 
    
        expiration_time = datetime.utcnow() + timedelta(hours=1)
    
        self.reset_token = token
        self.token_expiration = expiration_time
    
    
        return token

    @staticmethod
    def verify_reset_token(token):
        """
    Verifica si el token existe en algún usuario y si no ha expirado.
    
    Args:
        token (str): El token de restablecimiento proporcionado por el usuario.

    Returns:
        User or None: El objeto User si el token es válido y activo, None en caso contrario.
    """
        user = User.query.filter_by(reset_token=token).first()
    
        if user is None:
            return None
    
        if user.token_expiration is None or user.token_expiration < datetime.utcnow():
            user.reset_token = None
            user.token_expiration = None
            db.session.commit()
            return None
        
        return user