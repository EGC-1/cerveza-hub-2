# app/modules/admin/forms.py (USANDO SELECTMULTIPLEFIELD)

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
# 🚨 Cambiamos a SelectMultipleField
from wtforms.fields import SelectMultipleField 
# Eliminamos: from flask_wtf.db import QuerySelectField
# Eliminamos: def get_roles() y def get_role_label()

class UserAdminForm(FlaskForm):
    email = StringField('Email')
    
    # Usamos SelectMultipleField con choices=[] iniciales.
    # Las opciones se llenarán en el fichero routes.py (la vista).
    roles = SelectMultipleField(
        'Roles',
        choices=[], 
        # Importante: deshabilitamos la validación inicial de opciones 
        # hasta que se hayan llenado en la vista.
        validate_choice=False 
    )
    submit = SubmitField('Guardar Cambios')