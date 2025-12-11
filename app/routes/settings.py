from functools import wraps
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import AuditLog, Role, User, PERMISSIONS

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')


def super_admin_required(f):
    """Decorator to require super admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_super_admin():
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


# ==================== AUDIT LOGS ====================

@settings_bp.route('/audit-logs')
@login_required
@admin_required
def audit_logs():
    """View audit logs"""
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    # Filters
    action = request.args.get('action', '')
    resource_type = request.args.get('resource_type', '')
    user_id = request.args.get('user_id', type=int)
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    query = AuditLog.query
    
    if action:
        query = query.filter_by(action=action)
    if resource_type:
        query = query.filter_by(resource_type=resource_type)
    if user_id:
        query = query.filter_by(user_id=user_id)
    if date_from:
        query = query.filter(AuditLog.created_at >= datetime.strptime(date_from, '%Y-%m-%d'))
    if date_to:
        query = query.filter(AuditLog.created_at <= datetime.strptime(date_to, '%Y-%m-%d'))
    
    logs = query.order_by(AuditLog.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Get unique values for filters
    actions = db.session.query(AuditLog.action.distinct()).all()
    resource_types = db.session.query(AuditLog.resource_type.distinct()).all()
    users = User.query.filter(User.role.in_(['admin', 'super_admin'])).all()
    
    return render_template('settings/audit_logs.html',
        logs=logs,
        actions=[a[0] for a in actions],
        resource_types=[r[0] for r in resource_types],
        users=users,
        current_filters={
            'action': action,
            'resource_type': resource_type,
            'user_id': user_id,
            'date_from': date_from,
            'date_to': date_to
        }
    )


# ==================== ROLES MANAGEMENT ====================

@settings_bp.route('/roles')
@login_required
@super_admin_required
def list_roles():
    """List all roles"""
    roles = Role.query.order_by(Role.name).all()
    return render_template('settings/roles.html', roles=roles, permissions=PERMISSIONS)


@settings_bp.route('/roles/create', methods=['GET', 'POST'])
@login_required
@super_admin_required
def create_role():
    """Create a new role"""
    if request.method == 'POST':
        name = request.form.get('name', '').lower().replace(' ', '_')
        description = request.form.get('description')
        permissions = request.form.getlist('permissions')
        
        if Role.query.filter_by(name=name).first():
            flash('A role with this name already exists.', 'danger')
            return redirect(url_for('settings.create_role'))
        
        role = Role(
            name=name,
            description=description,
            is_system=False
        )
        role.set_permissions(permissions)
        
        db.session.add(role)
        db.session.commit()
        
        current_user.log_activity('create', 'role', role.id, f'Created role: {role.name}')
        db.session.commit()
        
        flash(f'Role "{role.name}" created successfully!', 'success')
        return redirect(url_for('settings.list_roles'))
    
    return render_template('settings/create_role.html', permissions=PERMISSIONS)


@settings_bp.route('/roles/<int:role_id>/edit', methods=['GET', 'POST'])
@login_required
@super_admin_required
def edit_role(role_id):
    """Edit a role"""
    role = Role.query.get_or_404(role_id)
    
    if role.is_system and role.name == 'super_admin':
        flash('Cannot edit the super admin role.', 'danger')
        return redirect(url_for('settings.list_roles'))
    
    if request.method == 'POST':
        old_perms = role.get_permissions()
        
        role.description = request.form.get('description')
        new_perms = request.form.getlist('permissions')
        role.set_permissions(new_perms)
        
        current_user.log_activity('update', 'role', role.id,
                                 f'Updated role: {role.name}',
                                 {'permissions': old_perms},
                                 {'permissions': new_perms})
        
        db.session.commit()
        flash('Role updated successfully!', 'success')
        return redirect(url_for('settings.list_roles'))
    
    return render_template('settings/edit_role.html', role=role, permissions=PERMISSIONS)


@settings_bp.route('/roles/<int:role_id>/delete', methods=['POST'])
@login_required
@super_admin_required
def delete_role(role_id):
    """Delete a role"""
    role = Role.query.get_or_404(role_id)
    
    if role.is_system:
        flash('Cannot delete system roles.', 'danger')
        return redirect(url_for('settings.list_roles'))
    
    # Check if any users have this role
    users_with_role = User.query.filter_by(role_id=role.id).count()
    if users_with_role > 0:
        flash(f'Cannot delete role: {users_with_role} user(s) are assigned this role.', 'danger')
        return redirect(url_for('settings.list_roles'))
    
    current_user.log_activity('delete', 'role', role.id, f'Deleted role: {role.name}')
    
    db.session.delete(role)
    db.session.commit()
    
    flash('Role deleted successfully!', 'success')
    return redirect(url_for('settings.list_roles'))


# ==================== USER MANAGEMENT ====================

@settings_bp.route('/users')
@login_required
@admin_required
def list_users():
    """List all users"""
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    users = User.query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    roles = Role.query.order_by(Role.name).all()
    
    return render_template('settings/users.html', users=users, roles=roles)


@settings_bp.route('/users/<int:user_id>/role', methods=['POST'])
@login_required
@super_admin_required
def assign_role(user_id):
    """Assign a role to a user"""
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        flash('Cannot change your own role.', 'danger')
        return redirect(url_for('settings.list_users'))
    
    role_id = request.form.get('role_id', type=int)
    role = Role.query.get(role_id) if role_id else None
    
    old_role = user.role
    user.role_id = role_id
    if role:
        user.role = role.name
    
    current_user.log_activity('update', 'user', user.id,
                             f'Changed role for {user.email}',
                             {'role': old_role},
                             {'role': role.name if role else 'none'})
    
    db.session.commit()
    flash(f'Role updated for {user.email}!', 'success')
    return redirect(url_for('settings.list_users'))


@settings_bp.route('/users/<int:user_id>/toggle-active', methods=['POST'])
@login_required
@super_admin_required
def toggle_user_active(user_id):
    """Toggle user active status"""
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        flash('Cannot deactivate yourself.', 'danger')
        return redirect(url_for('settings.list_users'))
    
    user.is_active = not user.is_active
    
    current_user.log_activity('update', 'user', user.id,
                             f'{"Activated" if user.is_active else "Deactivated"} user: {user.email}')
    
    db.session.commit()
    flash(f'User {user.email} {"activated" if user.is_active else "deactivated"}!', 'success')
    return redirect(url_for('settings.list_users'))
