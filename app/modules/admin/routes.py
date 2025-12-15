from . import admin_bp
from .forms import UserAdminForm 
from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user 
from functools import wraps 
from app.modules.auth.models import db, User, Role 

def is_admin():
    """Verifica si el usuario actual está activo y tiene el rol 'admin'."""
    return current_user.is_authenticated and current_user.role and current_user.role.name == 'admin'

def role_admin_check():
    """Redirige al usuario si no es administrador."""
    if not is_admin():
        flash('Acceso denegado. Se requiere rol de administrador.', 'danger')
        return redirect(url_for('public.index')) 
    return None 


@admin_bp.route('/')
@login_required
def admin_index():
    response = role_admin_check()
    if response:
        return response
    
    users = User.query.all()
    
    return render_template('user_management.html', users=users)


@admin_bp.route('/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required 
def edit_user(user_id):
    response = role_admin_check()
    if response:
        return response
        
    users = User.query.all() 
    
    user = User.query.filter_by(id=user_id).first_or_404()
    form = UserAdminForm()

    all_roles = Role.query.all()
    form.roles.choices = [(str(role.id), role.name) for role in all_roles] 

    if form.validate_on_submit():
        
        user.email = form.email.data
        
        selected_role_id_str = form.roles.data[0] if form.roles.data else None 
        
        if selected_role_id_str:
            selected_role_id = int(selected_role_id_str)
            new_role = Role.query.get(selected_role_id)
            user.role = new_role 
        else:
            user.role = None
        
        db.session.commit()
        flash(f'Usuario {user.email} actualizado exitosamente.', 'success')
        
        return redirect(url_for('admin.admin_index'))

    elif request.method == 'GET':
        
        form.email.data = user.email
        
        current_role_id_str = str(user.role.id) if user.role else None
        
        form.roles.data = [current_role_id_str] if current_role_id_str else []

    return render_template('user_management.html', 
                             title='Editar Usuario', 
                             form=form, 
                             user_to_edit=user,
                             users=users)