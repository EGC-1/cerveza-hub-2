from flask import redirect, render_template, request, url_for, session
from flask_login import current_user, login_required

from app import db
from app.modules.auth.services import AuthenticationService
from app.modules.dataset.models import DataSet
from app.modules.profile import profile_bp
from app.modules.profile.forms import UserProfileForm
from app.modules.profile.services import UserProfileService


@profile_bp.route("/profile/edit", methods=["GET", "POST"])
@login_required
def edit_profile():
    auth_service = AuthenticationService()
    profile = auth_service.get_authenticated_user_profile
    if not profile:
        return redirect(url_for("public.index"))

    form = UserProfileForm()
    if request.method == "POST":
        service = UserProfileService()
        result, errors = service.update_profile(profile.id, form)
        return service.handle_service_response(
            result, errors, "profile.edit_profile", "Profile updated successfully", "profile/edit.html", form
        )

    return render_template("profile/edit.html", form=form)


@profile_bp.route("/profile/manage_account", methods=["GET", "POST"])
@login_required
def manage_account():
    auth_service = AuthenticationService()
    profile = auth_service.get_authenticated_user_profile
    if not profile:
        return redirect(url_for("public.index"))

    form = UserProfileForm()
    
    if request.method == "POST":
        service = UserProfileService()
        result, errors = service.update_profile(profile.id, form)
        return service.handle_service_response(
            result, errors, "profile.edit_profile", "Profile updated successfully", "profile/edit.html", form
        )
    return render_template("profile/manage_account.html", form=form)

@profile_bp.route("/profile/summary")
@login_required
def my_profile():
    page = request.args.get("page", 1, type=int)
    per_page = 5

    user_datasets_pagination = (
        db.session.query(DataSet)
        .filter(DataSet.user_id == current_user.id)
        .order_by(DataSet.created_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    total_datasets_count = db.session.query(DataSet).filter(DataSet.user_id == current_user.id).count()

    print(user_datasets_pagination.items)

    return render_template(
        "profile/summary.html",
        user_profile=current_user.profile,
        user=current_user,
        datasets=user_datasets_pagination.items,
        pagination=user_datasets_pagination,
        total_datasets=total_datasets_count,
    )

@profile_bp.route("/profile/manage_account/sessions")
@login_required
def manage_sessions():
    """
    Render the manage sessions page for the authenticated user.
    """
    current_session_key = session.sid
    service = UserProfileService()
    sessions, current_device_info = service.get_active_sessions(
        user_id = current_user.id,
        current_session_key = current_session_key,
        current_ip = request.remote_addr
    )
    return render_template(
        "profile/manage_account.html", 
        active_tab = "sessions",
        sessions = sessions,
        current_device = current_device_info,
        total_sessions = len(sessions) + 1
        )

@profile_bp.route("/profile/manage_account/close_session", methods = ["POST"])
@login_required
def close_remote_session():
    """
    Close a remote session for the authenticated user
    """
    session_key_to_close = request.form.get("session_key")
    if session_key_to_close:
        service = UserProfileService()
        result, errors = service.terminate_session(
            user_id = current_user.id,
            session_key_to_close = session_key_to_close
        )
    return redirect(url_for("profile.manage_sessions"))