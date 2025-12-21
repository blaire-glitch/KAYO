from flask import Blueprint, render_template, redirect, url_for, send_from_directory, current_app
from flask_login import login_required, current_user
from app.models.delegate import Delegate
from app.models.payment import Payment
from app.models.user import User
import os

main_bp = Blueprint('main', __name__)


@main_bp.route('/favicon.ico')
def favicon():
    return send_from_directory(
        os.path.join(current_app.root_path, 'static', 'images'),
        'logo.png',
        mimetype='image/png'
    )


@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))


@main_bp.route('/app', methods=['GET', 'POST'])
@login_required
def app_home():
    """Masked URL endpoint - redirects to dashboard"""
    return redirect(url_for('main.dashboard'))


@main_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_admin():
        return redirect(url_for('admin.dashboard'))
    
    # Users see only their own delegates
    delegates = Delegate.query.filter_by(registered_by=current_user.id).order_by(Delegate.registered_at.desc()).all()
    
    # Get user's payments
    payments = Payment.query.filter_by(
        user_id=current_user.id
    ).order_by(Payment.created_at.desc()).limit(5).all()
    
    # Calculate stats
    total_delegates = len(delegates)
    paid_delegates = sum(1 for d in delegates if d.is_paid)
    unpaid_delegates = total_delegates - paid_delegates
    
    return render_template('dashboard.html',
        delegates=delegates,
        total_delegates=total_delegates,
        paid_delegates=paid_delegates,
        unpaid_delegates=unpaid_delegates,
        payments=payments
    )
