from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from app.models.delegate import Delegate
from app.models.payment import Payment

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))


@main_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_admin():
        return redirect(url_for('admin.dashboard'))
    
    # Get user's delegates
    delegates = Delegate.query.filter_by(registered_by=current_user.id).order_by(Delegate.registered_at.desc()).all()
    
    # Calculate stats
    total_delegates = len(delegates)
    paid_delegates = sum(1 for d in delegates if d.is_paid)
    unpaid_delegates = total_delegates - paid_delegates
    
    # Get recent payments
    payments = Payment.query.filter_by(
        user_id=current_user.id
    ).order_by(Payment.created_at.desc()).limit(5).all()
    
    return render_template('dashboard.html',
        delegates=delegates,
        total_delegates=total_delegates,
        paid_delegates=paid_delegates,
        unpaid_delegates=unpaid_delegates,
        payments=payments
    )
