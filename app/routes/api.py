from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app.church_data import CHURCH_DATA, get_parishes

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/search')
@login_required
def global_search():
    """Global search API - searches delegates, users, payments, events"""
    from app.models.delegate import Delegate
    from app.models.user import User
    from app.models.payment import Payment
    from app.models.event import Event
    
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify({'results': []})
    
    results = []
    search_term = f'%{query}%'
    
    # Search Delegates
    delegates = Delegate.query.filter(
        (Delegate.full_name.ilike(search_term)) |
        (Delegate.phone.ilike(search_term)) |
        (Delegate.email.ilike(search_term)) |
        (Delegate.parish.ilike(search_term))
    ).limit(5).all()
    
    for d in delegates:
        results.append({
            'type': 'delegate',
            'icon': 'bi-person',
            'title': d.full_name,
            'subtitle': f'{d.parish} • {d.phone or "No phone"}',
            'url': f'/delegates/{d.id}',
            'badge': d.registration_status
        })
    
    # Search Users (admin only)
    if current_user.role in ['admin', 'super_admin']:
        users = User.query.filter(
            (User.name.ilike(search_term)) |
            (User.email.ilike(search_term)) |
            (User.phone.ilike(search_term))
        ).limit(5).all()
        
        for u in users:
            results.append({
                'type': 'user',
                'icon': 'bi-person-badge',
                'title': u.name,
                'subtitle': f'{u.role.title()} • {u.email}',
                'url': f'/admin/users/{u.id}',
                'badge': u.role
            })
    
    # Search Payments
    if current_user.role in ['admin', 'super_admin', 'finance', 'treasurer']:
        payments = Payment.query.filter(
            (Payment.transaction_code.ilike(search_term)) |
            (Payment.phone_number.ilike(search_term))
        ).limit(5).all()
        
        for p in payments:
            payer = p.delegate.full_name if p.delegate else (p.user.name if p.user else 'Unknown')
            results.append({
                'type': 'payment',
                'icon': 'bi-cash-coin',
                'title': f'KES {p.amount:,.0f} - {p.transaction_code or "No code"}',
                'subtitle': f'{payer} • {p.payment_date.strftime("%d %b %Y")}',
                'url': '/finance/dashboard',
                'badge': p.status
            })
    
    # Search Events
    events = Event.query.filter(
        (Event.name.ilike(search_term)) |
        (Event.venue.ilike(search_term))
    ).limit(3).all()
    
    for e in events:
        results.append({
            'type': 'event',
            'icon': 'bi-calendar-event',
            'title': e.name,
            'subtitle': f'{e.venue} • {e.start_date.strftime("%d %b %Y")}',
            'url': f'/events/{e.id}',
            'badge': 'Active' if e.is_active else 'Inactive'
        })
    
    return jsonify({'results': results, 'query': query})


@api_bp.route('/parishes/<archdeaconry>')
def get_parishes_for_archdeaconry(archdeaconry):
    """API endpoint to get parishes for a specific archdeaconry"""
    if archdeaconry in CHURCH_DATA:
        parishes = sorted(CHURCH_DATA[archdeaconry])
        return jsonify({'parishes': parishes})
    return jsonify({'parishes': [], 'error': 'Archdeaconry not found'}), 404


@api_bp.route('/church-data')
def get_church_data():
    """API endpoint to get all church data"""
    return jsonify(CHURCH_DATA)
