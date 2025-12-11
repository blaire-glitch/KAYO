from datetime import datetime
import uuid
import qrcode
import io
import base64
from app import db


class Delegate(db.Model):
    """Delegates table - people being registered for the event"""
    __tablename__ = 'delegates'
    
    id = db.Column(db.Integer, primary_key=True)
    ticket_number = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    local_church = db.Column(db.String(100), nullable=False)
    parish = db.Column(db.String(100), nullable=False)
    archdeaconry = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(15), nullable=True)
    id_number = db.Column(db.String(20), nullable=True)  # National ID for duplicate detection
    gender = db.Column(db.String(10), nullable=False)  # male, female
    category = db.Column(db.String(20), default='delegate')  # delegate, leader, speaker, vip
    
    # Registration details
    registered_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Payment status
    is_paid = db.Column(db.Boolean, default=False)
    payment_id = db.Column(db.Integer, db.ForeignKey('payments.id'), nullable=True)
    
    # Check-in tracking
    checked_in = db.Column(db.Boolean, default=False)
    checked_in_at = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f'<Delegate {self.name}>'
    
    @staticmethod
    def generate_ticket_number():
        """Generate a unique ticket number like KAYO-2025-XXXX"""
        year = datetime.utcnow().year
        # Get the count of delegates this year
        count = Delegate.query.filter(
            db.extract('year', Delegate.registered_at) == year
        ).count() + 1
        return f"KAYO-{year}-{count:04d}"
    
    def generate_qr_code(self):
        """Generate QR code for this delegate"""
        qr_data = f"KAYO|{self.ticket_number}|{self.name}|{self.phone_number or 'N/A'}"
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(qr_data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64 for embedding in HTML
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return base64.b64encode(buffer.getvalue()).decode()
    
    @staticmethod
    def check_duplicate(phone_number=None, id_number=None, exclude_id=None):
        """Check for duplicate registrations"""
        duplicates = []
        
        if phone_number:
            query = Delegate.query.filter(Delegate.phone_number == phone_number)
            if exclude_id:
                query = query.filter(Delegate.id != exclude_id)
            if query.first():
                duplicates.append(f"Phone number {phone_number} already registered")
        
        if id_number:
            query = Delegate.query.filter(Delegate.id_number == id_number)
            if exclude_id:
                query = query.filter(Delegate.id != exclude_id)
            if query.first():
                duplicates.append(f"ID number {id_number} already registered")
        
        return duplicates
    
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
    
    @staticmethod
    def get_daily_registration_stats(days=30):
        """Get registration counts for the last N days"""
        from datetime import timedelta
        start_date = datetime.utcnow() - timedelta(days=days)
        return db.session.query(
            db.func.date(Delegate.registered_at).label('date'),
            db.func.count(Delegate.id).label('count')
        ).filter(Delegate.registered_at >= start_date)\
         .group_by(db.func.date(Delegate.registered_at))\
         .order_by(db.func.date(Delegate.registered_at)).all()
    
    @staticmethod
    def get_category_stats():
        """Get delegate counts by category"""
        return db.session.query(
            Delegate.category,
            db.func.count(Delegate.id).label('count')
        ).group_by(Delegate.category).all()
    
    @staticmethod
    def search(query):
        """Smart search across multiple fields"""
        search_term = f"%{query}%"
        return Delegate.query.filter(
            db.or_(
                Delegate.name.ilike(search_term),
                Delegate.phone_number.ilike(search_term),
                Delegate.id_number.ilike(search_term),
                Delegate.ticket_number.ilike(search_term),
                Delegate.local_church.ilike(search_term),
                Delegate.parish.ilike(search_term),
                Delegate.archdeaconry.ilike(search_term)
            )
        ).all()
