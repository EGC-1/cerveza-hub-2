from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo


class SignupForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=100)])
    surname = StringField("Surname", validators=[DataRequired(), Length(max=100)])
    password = PasswordField("Password", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    submit = SubmitField("Submit")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember_me = BooleanField("Remember me")
    submit = SubmitField("Login")

class RequestResetForm(FlaskForm):
    """
    Formulario para solicitar el restablecimiento de contraseña (solo pide el email).
    """
    email = StringField(
        "Email", 
        validators=[DataRequired(), Email()]
    )
    submit = SubmitField("Solicitar Restablecimiento")


class ResetPasswordForm(FlaskForm):
    """
    Formulario para establecer la nueva contraseña (pide contraseña y confirmación).
    """
    password = PasswordField(
        "Nueva Contraseña", 
        validators=[DataRequired(), Length(min=6)]
    )
    confirm_password = PasswordField(
        "Confirmar Contraseña",
        validators=[DataRequired(), EqualTo("password", message="Las contraseñas deben coincidir")]
    )
    submit = SubmitField("Recover Password")