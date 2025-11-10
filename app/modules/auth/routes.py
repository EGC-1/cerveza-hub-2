from app.modules.auth.models import User
from flask import redirect, render_template, request, url_for, flash
from flask_login import current_user, login_user, logout_user

from app.modules.auth import auth_bp
from app.modules.auth.forms import LoginForm, SignupForm, RequestResetForm, ResetPasswordForm
from app.modules.auth.services import AuthenticationService, send_password_reset_email
from app.modules.profile.services import UserProfileService

authentication_service = AuthenticationService()
user_profile_service = UserProfileService()


@auth_bp.route("/signup/", methods=["GET", "POST"])
def show_signup_form():
    if current_user.is_authenticated:
        return redirect(url_for("public.index"))

    form = SignupForm()
    if form.validate_on_submit():
        email = form.email.data
        if not authentication_service.is_email_available(email):
            return render_template("auth/signup_form.html", form=form, error=f"Email {email} in use")

        try:
            user = authentication_service.create_with_profile(**form.data)
        except Exception as exc:
            return render_template("auth/signup_form.html", form=form, error=f"Error creating user: {exc}")

        # Log user
        login_user(user, remember=True)
        return redirect(url_for("public.index"))

    return render_template("auth/signup_form.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("public.index"))

    form = LoginForm()
    if request.method == "POST" and form.validate_on_submit():
        if authentication_service.login(form.email.data, form.password.data):
            return redirect(url_for("public.index"))

        return render_template("auth/login_form.html", form=form, error="Invalid credentials")

    return render_template("auth/login_form.html", form=form)


@auth_bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("public.index"))

@auth_bp.route("/recover", methods=["GET", "POST"])
def forgot_password_request():
    """
    Solicita el email del usuario para iniciar el proceso de restablecimiento de contraseña.
    Si el email existe, envía el enlace de restablecimiento.
    """
    if current_user.is_authenticated:
        return redirect(url_for("public.index"))
    form = RequestResetForm()
    
    if form.validate_on_submit():
        email = form.email.data
        
        user = authentication_service.get_user_by_email(email)
        
        if user:
            aaa = send_password_reset_email(user) 
            
            if aaa :
                flash("Se ha enviado un enlace para restablecer la contraseña a su correo electrónico.", "info")
                return redirect(url_for('auth.login'))
            else:
                return render_template("auth/recover_password.html", form=form)

        else:
            flash("El correo electrónico no se encuentra registrado. Por favor, verifique.", "danger")
            return render_template("auth/recover_password.html", form=form)


    return render_template("auth/recover_password.html", form=form)

@auth_bp.route("/reset-password/<string:token>", methods=["GET", "POST"])
def reset_token(token):
    """
    1. Verifica el token recibido en la URL.
    2. Si es válido, permite al usuario establecer una nueva contraseña.
    """
    if current_user.is_authenticated:
        return redirect(url_for("public.index"))

    user: User = User.verify_reset_token(token)

    if user is None:
        flash("El enlace de recuperación es inválido o ha expirado. Solicita uno nuevo.", "danger")
        return redirect(url_for("auth.forgot_password_request"))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        
        success = authentication_service.update_user(user)

        if success:
            flash("Tu contraseña ha sido actualizada. Ya puedes iniciar sesión.", "success")
            return redirect(url_for("auth.login"))
        else:
            flash("Hubo un error interno al guardar la nueva contraseña. Inténtalo de nuevo.", "danger")
            return redirect(url_for("auth.reset_token", token=token)) 

    return render_template(
        "auth/new_password.html", 
        title="Establecer Nueva Contraseña", 
        form=form
    )