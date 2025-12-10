from datetime import datetime
from app import db


class Payment(db.Model):
    """Payments table - M-Pesa transactions"""
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_mode = db.Column(db.String(50), default='M-Pesa Paybill')
    
    # M-Pesa specific fields
    transaction_id = db.Column(db.String(50), unique=True, nullable=True)
    mpesa_receipt_number = db.Column(db.String(50), nullable=True)
    checkout_request_id = db.Column(db.String(100), nullable=True)
    merchant_request_id = db.Column(db.String(100), nullable=True)
    phone_number = db.Column(db.String(15), nullable=True)
    
    # Status tracking
    status = db.Column(db.String(20), default='pending')  # pending, completed, failed
    result_code = db.Column(db.String(10), nullable=True)
    result_desc = db.Column(db.String(200), nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Number of delegates this payment covers
    delegates_count = db.Column(db.Integer, nullable=False, default=0)
    
    # Relationship to delegates
    delegates = db.relationship('Delegate', backref='payment', lazy='dynamic')
    
    def __repr__(self):
        return f'<Payment {self.id} - KSh {self.amount}>'
    
    def mark_completed(self, mpesa_receipt, transaction_id=None):
        """Mark payment as completed and update related delegates"""
        self.status = 'completed'
        self.mpesa_receipt_number = mpesa_receipt
        self.transaction_id = transaction_id or mpesa_receipt
        self.completed_at = datetime.utcnow()
        
        # Mark all linked delegates as paid
        for delegate in self.delegates:
            delegate.is_paid = True
    
    def mark_failed(self, result_code, result_desc):
        """Mark payment as failed"""
        self.status = 'failed'
        self.result_code = result_code
        self.result_desc = result_desc
    
    @staticmethod
    def get_total_collected():
        """Get total amount collected"""
        result = db.session.query(
            db.func.sum(Payment.amount)
        ).filter(Payment.status == 'completed').scalar()
        return result or 0
    
    @staticmethod
    def get_payment_stats():
        """Get payment statistics"""
        return db.session.query(
            Payment.status,
            db.func.count(Payment.id).label('count'),
            db.func.sum(Payment.amount).label('total')
        ).group_by(Payment.status).all()
