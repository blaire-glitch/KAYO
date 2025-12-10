from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models.delegate import Delegate
from app.forms import DelegateForm

delegates_bp = Blueprint('delegates', __name__, url_prefix='/delegates')


@delegates_bp.route('/register', methods=['GET', 'POST'])
@login_required
def register_delegate():
    form = DelegateForm()
    
    # Pre-fill with user's church details
    if request.method == 'GET':
        form.local_church.data = current_user.local_church or ''
        form.parish.data = current_user.parish or ''
        form.archdeaconry.data = current_user.archdeaconry or ''
    
    if form.validate_on_submit():
        delegate = Delegate(
            name=form.name.data,
            local_church=form.local_church.data,
            parish=form.parish.data,
            archdeaconry=form.archdeaconry.data,
            phone_number=form.phone_number.data or None,
            gender=form.gender.data,
            registered_by=current_user.id
        )
        db.session.add(delegate)
        db.session.commit()
        flash(f'Delegate "{delegate.name}" registered successfully!', 'success')
        return redirect(url_for('delegates.list_delegates'))
    
    return render_template('delegates/register.html', form=form)


@delegates_bp.route('/')
@login_required
def list_delegates():
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    delegates = Delegate.query.filter_by(
        registered_by=current_user.id
    ).order_by(Delegate.registered_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('delegates/list.html', delegates=delegates)


@delegates_bp.route('/<int:id>')
@login_required
def view_delegate(id):
    delegate = Delegate.query.get_or_404(id)
    
    # Only allow viewing own delegates (unless admin)
    if delegate.registered_by != current_user.id and not current_user.is_admin():
        flash('You do not have permission to view this delegate.', 'danger')
        return redirect(url_for('delegates.list_delegates'))
    
    return render_template('delegates/view.html', delegate=delegate)


@delegates_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_delegate(id):
    delegate = Delegate.query.get_or_404(id)
    
    # Only allow editing own delegates (unless admin)
    if delegate.registered_by != current_user.id and not current_user.is_admin():
        flash('You do not have permission to edit this delegate.', 'danger')
        return redirect(url_for('delegates.list_delegates'))
    
    # Don't allow editing paid delegates
    if delegate.is_paid:
        flash('Cannot edit delegate after payment has been made.', 'warning')
        return redirect(url_for('delegates.view_delegate', id=id))
    
    form = DelegateForm(obj=delegate)
    
    if form.validate_on_submit():
        delegate.name = form.name.data
        delegate.local_church = form.local_church.data
        delegate.parish = form.parish.data
        delegate.archdeaconry = form.archdeaconry.data
        delegate.phone_number = form.phone_number.data or None
        delegate.gender = form.gender.data
        db.session.commit()
        flash('Delegate updated successfully!', 'success')
        return redirect(url_for('delegates.view_delegate', id=id))
    
    return render_template('delegates/edit.html', form=form, delegate=delegate)


@delegates_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete_delegate(id):
    delegate = Delegate.query.get_or_404(id)
    
    # Only allow deleting own delegates (unless admin)
    if delegate.registered_by != current_user.id and not current_user.is_admin():
        flash('You do not have permission to delete this delegate.', 'danger')
        return redirect(url_for('delegates.list_delegates'))
    
    # Don't allow deleting paid delegates
    if delegate.is_paid:
        flash('Cannot delete delegate after payment has been made.', 'warning')
        return redirect(url_for('delegates.view_delegate', id=id))
    
    name = delegate.name
    db.session.delete(delegate)
    db.session.commit()
    flash(f'Delegate "{name}" has been deleted.', 'success')
    return redirect(url_for('delegates.list_delegates'))
