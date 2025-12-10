from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db, login_manager


class User(UserMixin, db.Model):
    """Users table for Chairs, Youth Ministers, and Admins"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(15), unique=True, nullable=True)
    role = db.Column(db.String(20), nullable=False, default='chair')  # chair, youth_minister, admin
    password_hash = db.Column(db.String(256), nullable=False)
    local_church = db.Column(db.String(100), nullable=True)
    parish = db.Column(db.String(100), nullable=True)
    archdeaconry = db.Column(db.String(100), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    delegates = db.relationship('Delegate', backref='registered_by_user', lazy='dynamic')
    payments = db.relationship('Payment', backref='user', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        return self.role == 'admin'
    
    def get_unpaid_delegates_count(self):
        """Get count of delegates not yet paid for"""
        from app.models.delegate import Delegate
        return Delegate.query.filter_by(
            registered_by=self.id,
            is_paid=False
        ).count()
    
    def get_total_amount_due(self):
        """Calculate total amount due for unpaid delegates"""
        from flask import current_app
        return self.get_unpaid_delegates_count() * current_app.config['DELEGATE_FEE']
    
    def __repr__(self):
        return f'<User {self.email}>'


@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))
