from datetime import datetime
from app import db


class Delegate(db.Model):
    """Delegates table - people being registered for the event"""
    __tablename__ = 'delegates'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    local_church = db.Column(db.String(100), nullable=False)
    parish = db.Column(db.String(100), nullable=False)
    archdeaconry = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(15), nullable=True)
    gender = db.Column(db.String(10), nullable=False)  # male, female
    
    # Registration details
    registered_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Payment status
    is_paid = db.Column(db.Boolean, default=False)
    payment_id = db.Column(db.Integer, db.ForeignKey('payments.id'), nullable=True)
    
    def __repr__(self):
        return f'<Delegate {self.name}>'
    
    @staticmethod
    def get_stats_by_archdeaconry():
        """Get delegate counts grouped by archdeaconry"""
        return db.session.query(
            Delegate.archdeaconry,
            db.func.count(Delegate.id).label('total'),
            db.func.sum(db.case((Delegate.is_paid == True, 1), else_=0)).label('paid'),
            db.func.sum(db.case((Delegate.is_paid == False, 1), else_=0)).label('unpaid')
        ).group_by(Delegate.archdeaconry).all()
    
    @staticmethod
    def get_stats_by_parish():
        """Get delegate counts grouped by parish"""
        return db.session.query(
            Delegate.parish,
            Delegate.archdeaconry,
            db.func.count(Delegate.id).label('total'),
            db.func.sum(db.case((Delegate.is_paid == True, 1), else_=0)).label('paid'),
            db.func.sum(db.case((Delegate.is_paid == False, 1), else_=0)).label('unpaid')
        ).group_by(Delegate.parish, Delegate.archdeaconry).all()
    
    @staticmethod
    def get_gender_stats():
        """Get delegate counts by gender"""
        return db.session.query(
            Delegate.gender,
            db.func.count(Delegate.id).label('count')
        ).group_by(Delegate.gender).all()
