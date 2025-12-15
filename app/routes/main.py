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


def is_youth_minister():
    """Check if current user is a youth minister"""
    return current_user.role == 'youth_minister'


def get_archdeaconry_user_ids(archdeaconry):
    """Get all user IDs (chairs) in a specific archdeaconry"""
    users = User.query.filter_by(archdeaconry=archdeaconry).all()
    return [u.id for u in users]


@main_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_admin():
        return redirect(url_for('admin.dashboard'))
    
    # Youth ministers see all delegates from their archdeaconry
    if is_youth_minister() and current_user.archdeaconry:
        user_ids = get_archdeaconry_user_ids(current_user.archdeaconry)
        delegates = Delegate.query.filter(
            Delegate.registered_by.in_(user_ids)
        ).order_by(Delegate.registered_at.desc()).all()
        
        # Get payments from archdeaconry users
        payments = Payment.query.filter(
            Payment.user_id.in_(user_ids)
        ).order_by(Payment.created_at.desc()).limit(10).all()
    else:
        # Regular users see only their own delegates
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
