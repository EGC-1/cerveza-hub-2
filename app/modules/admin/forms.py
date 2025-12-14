
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email

class UserAdminForm(FlaskForm):
    email = StringField(
        'Email', 
        validators=[
            DataRequired(message="El email es obligatorio"), 
            Email(message="Email inválido") 
        ]
    )
    
    roles = SelectField(
        'Rol',
        choices=[], 
        validate_choice=False 
    )
    
    submit = SubmitField('Guardar Cambios')