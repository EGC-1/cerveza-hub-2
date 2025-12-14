from curses import flash
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

@profile_bp.route("/profile/manage_account", methods=["GET", "POST"])
@login_required
def manage_account(active_tab='profile'):
    auth_service = AuthenticationService()
    profile_service = UserProfileService()
    user = auth_service.get_authenticated_user()
    profile = auth_service.get_authenticated_user_profile()
    
    if not profile:
        return redirect(url_for("public.index"))

    form = UserProfileForm()
    
    if request.method == "POST":
        result, errors = profile_service.update_profile(profile.id, form)
        return profile_service.handle_service_response(
            result, errors, "profile.manage_account", "Profile updated successfully", "profile/manage_account.html", form
        )
    return render_template(
        "profile/manage_account.html", 
        form=form,
        active_tab = "profile",
        current_device= None,
        sessions = [],
        error = None)

@profile_bp.route("/profile/manage_account/sessions", methods=["GET"])
@login_required
def manage_sessions():
    """
    Render the manage sessions page for the authenticated user.
    """
    profile_service = UserProfileService()
    user = current_user
    current_device = None
    sessions = []
    error = None

    try:
        session_key = request.cookies.get(current_app.config.get('SESSION_COOKIE_NAME', 'session'))
        current_device, sessions = profile_service.get_active_sessions(
            user_id=user.id,
            user_agent= request.user_agent.string,
            ip_address = request.remote_addr,
            current_session_key=session_key
        )
    except Exception as e:
        error = "Sessions could not been retrieved"
        current_app.logger.error(f"Error retrieving sessions: {e}")

    return render_template(
        "profile/manage_account.html", 
        form=UserProfileForm(),
        active_tab="sessions",
        current_device = current_device,
        sessions = sessions,
        error = error
        )

@profile_bp.route("/profile/manage_account/close_session", methods = ["POST"])
@login_required
def close_remote_session():
    """
    Close a remote session for the authenticated user
    """
    profile_service = UserProfileService()
    user = current_user
    
    session_key_to_close = request.form.get("session_key")
    if session_key_to_close:
        if profile_service.terminate_session(user.id, session_key_to_close):
            flash("Session closed successfully", "success")
        else:
            flash("Failed to close the session", "error")
    else:
        flash("No session key provided", "error")
    return redirect(url_for("profile.manage_sessions"))